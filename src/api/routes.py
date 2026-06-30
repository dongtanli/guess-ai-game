"""FastAPI 路由（Orchestrator）。"""

import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import get_db_path, get_predictor, get_session
from src.core.contracts import (
    MAX_IMAGE_SIZE_BYTES,
    QWEN_MODEL_NAME,
    GuessRequest,
)
from src.core.state_machine import GameSession, calculate_score, is_correct_guess
from src.core.word_bank import get_random_topic
from src.services.ai_predictor import safe_predict
from src.services.db import insert_round, list_rounds
from src.services.providers.qwen import QwenProvider

router: APIRouter = APIRouter()

# 常量
_PNG_PREFIX: str = "data:image/png;base64,"


class TopicResponse(BaseModel):
    topic: str


class GuessResponse(BaseModel):
    guess: str
    confidence: float
    model: str


class FeedbackRequest(BaseModel):
    user_says_correct: bool


class FeedbackResponse(BaseModel):
    scored: bool
    score: int


class ScoreResponse(BaseModel):
    score: int


class ResetResponse(BaseModel):
    ok: bool


class HistoryItemResponse(BaseModel):
    id: int
    topic: str
    guess: str
    is_correct: bool
    model_name: str
    created_at: str


class HistoryResponse(BaseModel):
    records: list[HistoryItemResponse]


def _validate_and_decode_image(image_b64: str) -> bytes:
    """校验图片前缀、解码 base64、检查大小，返回原始字节。"""
    # 1. 检查 PNG 前缀
    if not image_b64.startswith(_PNG_PREFIX):
        raise HTTPException(
            status_code=400,
            detail="only PNG format is allowed",
        )

    # 2. 分离并解码 base64
    b64_data: str = image_b64[len(_PNG_PREFIX):]
    try:
        image_bytes: bytes = base64.b64decode(b64_data, validate=True)
    except binascii.Error:
        raise HTTPException(
            status_code=400,
            detail="invalid base64 encoding",
        ) from None

    # 3. 检查大小
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="image exceeds 2MB limit",
        )

    return image_bytes


# ==================== 端点 ====================


@router.get("/topic", response_model=TopicResponse)
def get_topic(
    session: GameSession = Depends(get_session),
) -> TopicResponse:
    """随机出题，开始新一轮。"""
    topic: str = get_random_topic()
    try:
        session.start_round(topic)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return TopicResponse(topic=topic)


@router.post("/guess", response_model=GuessResponse)
async def post_guess(
    body: GuessRequest,
    session: GameSession = Depends(get_session),
    predictor: QwenProvider = Depends(get_predictor),
) -> GuessResponse:
    """提交画图，AI 进行猜测。"""
    # 1. 校验并解码图片
    image_bytes: bytes = _validate_and_decode_image(body.image_b64)

    # 2. 状态：DRAFT → GUESSING
    try:
        session.submit_guess()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # 3. AI 预测（含超时/降级）
    result = await safe_predict(predictor, image_bytes)

    # 4. 状态：GUESSING → RESULT
    try:
        session.receive_result(result.guess)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return GuessResponse(
        guess=result.guess,
        confidence=result.confidence,
        model=result.model_name,
    )


@router.post("/feedback", response_model=FeedbackResponse)
async def post_feedback(
    body: FeedbackRequest,
    session: GameSession = Depends(get_session),
    db_path: str = Depends(get_db_path),
) -> FeedbackResponse:
    """用户判断 AI 猜测正误。"""
    # 1. 持久化回合记录（先写 DB，再改状态：DB 失败时不污染状态机）
    ai_correct = is_correct_guess(session.current_topic, session.ai_guess or "")
    scored = calculate_score(body.user_says_correct, ai_correct) == 1
    try:
        await insert_round(
            db_path=db_path,
            topic=session.current_topic,
            guess=session.ai_guess or "",
            is_correct=scored,
            model_name=QWEN_MODEL_NAME,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None

    # 2. 状态：RESULT → DONE，计分
    try:
        _scored, new_score = session.process_feedback(body.user_says_correct)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return FeedbackResponse(scored=scored, score=new_score)


@router.get("/score", response_model=ScoreResponse)
def get_score(
    session: GameSession = Depends(get_session),
) -> ScoreResponse:
    """返回当前累计得分。"""
    return ScoreResponse(score=session.score)


@router.get("/reset", response_model=ResetResponse)
def post_reset(
    session: GameSession = Depends(get_session),
) -> ResetResponse:
    """错误恢复：强制重置状态机到 DRAFT。"""
    session.reset()
    return ResetResponse(ok=True)


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    db_path: str = Depends(get_db_path),
) -> HistoryResponse:
    """返回最近 20 条回合记录。"""
    rows = await list_rounds(db_path, limit=20)
    items = [
        HistoryItemResponse(
            id=row["id"],  # type: ignore[arg-type]
            topic=row["topic"],  # type: ignore[arg-type]
            guess=row["guess"],  # type: ignore[arg-type]
            is_correct=bool(row["is_correct"]),
            model_name=row["model_name"],  # type: ignore[arg-type]
            created_at=row["created_at"],  # type: ignore[arg-type]
        )
        for row in rows
    ]
    return HistoryResponse(records=items)
