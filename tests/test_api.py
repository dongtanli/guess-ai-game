"""路由层集成测试（TestClient + Mock Predictor）。"""

import base64
import os

import pytest
from fastapi.testclient import TestClient

from src.api.deps import get_db_path, get_predictor, get_session
from src.core.contracts import PredictionResult
from src.core.state_machine import GameSession
from src.main import app
from src.services.db import init_db

# ==================== Mock Provider ====================

class MockProviderForAPI:
    """可编程 Mock Provider，用于 API 集成测试。"""

    def __init__(self, model_name: str = "deepseek-v4-pro") -> None:
        self._name: str = model_name
        self._result: PredictionResult = PredictionResult(
            model_name=model_name,
            guess="苹果",
            confidence=0.9,
        )

    @property
    def name(self) -> str:
        return self._name

    async def predict(self, image_bytes: bytes) -> PredictionResult:
        return self._result


# ==================== Fixtures ====================

@pytest.fixture
def mock_provider() -> MockProviderForAPI:
    """可编程 Mock Provider 实例。"""
    return MockProviderForAPI()


@pytest.fixture
def test_client(mock_provider: MockProviderForAPI, tmp_path: str) -> TestClient:
    """构造 TestClient，覆盖 get_session/get_predictor/get_db_path。

    关键：使用闭包捕获同一个 GameSession 实例，确保跨请求状态持久化。
    """
    db_path: str = os.path.join(tmp_path, "test_api.db")
    session: GameSession = GameSession()

    import asyncio

    asyncio.run(init_db(db_path))

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_predictor] = lambda: mock_provider
    app.dependency_overrides[get_db_path] = lambda: db_path

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# ==================== Helper ====================

def _make_valid_image() -> str:
    """生成最小的有效 PNG（1×1 像素）。"""
    # 1×1 白色 PNG
    png_bytes: bytes = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
        0x44, 0xAE, 0x42, 0x60, 0x82,
    ])
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")


# ==================== Tests: GET /api/topic ====================

def test_get_topic_returns_valid_topic(test_client: TestClient) -> None:
    """GET /api/topic 返回 200 和合法 topic。"""
    resp = test_client.get("/api/topic")
    assert resp.status_code == 200
    data = resp.json()
    assert "topic" in data
    assert isinstance(data["topic"], str)
    assert len(data["topic"]) > 0


# ==================== Tests: POST /api/guess ====================

def test_post_guess_success(test_client: TestClient) -> None:
    """POST /api/guess 正常流程返回 guess/confidence/model。"""
    test_client.get("/api/topic")

    resp = test_client.post("/api/guess", json={"image_b64": _make_valid_image()})
    assert resp.status_code == 200
    data = resp.json()
    assert data["guess"] == "苹果"
    assert data["confidence"] == 0.9
    assert data["model"] == "deepseek-v4-pro"


def test_post_guess_png_prefix_invalid(test_client: TestClient) -> None:
    """非 PNG 前缀 → 400。"""
    test_client.get("/api/topic")
    resp = test_client.post(
        "/api/guess",
        json={"image_b64": "data:image/jpeg;base64,YWJjZA=="},
    )
    assert resp.status_code == 400
    assert "only PNG format" in resp.json()["detail"]


def test_post_guess_invalid_base64(test_client: TestClient) -> None:
    """无效 base64 → 400。"""
    test_client.get("/api/topic")
    resp = test_client.post(
        "/api/guess",
        json={"image_b64": "data:image/png;base64,!!!not-valid!!!"},
    )
    assert resp.status_code == 400
    assert "invalid base64" in resp.json()["detail"]


def test_post_guess_image_too_large(test_client: TestClient) -> None:
    """图片超过 2MB → 400。"""
    test_client.get("/api/topic")
    # 生成 2MB+1 字节的 base64
    dummy: bytes = b"\x00" * (2 * 1024 * 1024 + 1)
    b64: str = base64.b64encode(dummy).decode("ascii")
    resp = test_client.post(
        "/api/guess",
        json={"image_b64": f"data:image/png;base64,{b64}"},
    )
    assert resp.status_code == 400
    assert "exceeds 2MB" in resp.json()["detail"]


def test_post_guess_ai_degraded_returns_200(
    test_client: TestClient,
    mock_provider: MockProviderForAPI,
) -> None:
    """AI 降级结果仍返回 200（非 5xx）。"""
    mock_provider._result = PredictionResult(
        model_name="deepseek-v4-pro",
        guess="timeout",
        confidence=0.0,
        fallback_triggered=True,
    )
    test_client.get("/api/topic")
    resp = test_client.post("/api/guess", json={"image_b64": _make_valid_image()})
    assert resp.status_code == 200
    data = resp.json()
    assert data["guess"] == "timeout"
    assert data["confidence"] == 0.0


# ==================== Tests: POST /api/feedback ====================

def test_post_feedback_scored(
    test_client: TestClient,
    mock_provider: MockProviderForAPI,
) -> None:
    """用户判定正确且 AI 猜对 → scored=true, score=1。"""
    # 先获取 topic，再让 mock 返回与 topic 匹配的 guess
    resp1 = test_client.get("/api/topic")
    topic: str = resp1.json()["topic"]
    # 让 mock 返回包含 topic 的 guess，确保 ai_correct 为 True
    mock_provider._result = PredictionResult(
        model_name="deepseek-v4-pro",
        guess=topic,
        confidence=0.9,
    )

    test_client.post("/api/guess", json={"image_b64": _make_valid_image()})
    resp = test_client.post("/api/feedback", json={"user_says_correct": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["scored"] is True
    assert data["score"] == 1


def test_post_feedback_not_scored(
    test_client: TestClient,
    mock_provider: MockProviderForAPI,
) -> None:
    """用户判定错误 → scored=false, score=0（无论 AI 是否正确）。"""
    resp1 = test_client.get("/api/topic")
    topic: str = resp1.json()["topic"]
    # 让 mock 返回与 topic 匹配的 guess（ai_correct=True），
    # 但 user_says_correct=False → scored 仍为 False
    mock_provider._result = PredictionResult(
        model_name="deepseek-v4-pro",
        guess=topic,
        confidence=0.9,
    )

    test_client.post("/api/guess", json={"image_b64": _make_valid_image()})
    resp = test_client.post("/api/feedback", json={"user_says_correct": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["scored"] is False
    assert data["score"] == 0


def test_post_feedback_state_barrier_400(test_client: TestClient) -> None:
    """未完成 guess 直接 feedback → 400（状态屏障）。"""
    test_client.get("/api/topic")
    resp = test_client.post("/api/feedback", json={"user_says_correct": True})
    assert resp.status_code == 400


# ==================== Tests: GET /api/score ====================

def test_get_score_initial(test_client: TestClient) -> None:
    """初始 score 为 0。"""
    resp = test_client.get("/api/score")
    assert resp.status_code == 200
    assert resp.json()["score"] == 0


def test_get_score_after_feedback(
    test_client: TestClient,
    mock_provider: MockProviderForAPI,
) -> None:
    """反馈后 score 更新。"""
    resp1 = test_client.get("/api/topic")
    topic: str = resp1.json()["topic"]
    mock_provider._result = PredictionResult(
        model_name="deepseek-v4-pro",
        guess=topic,
        confidence=0.9,
    )
    test_client.post("/api/guess", json={"image_b64": _make_valid_image()})
    test_client.post("/api/feedback", json={"user_says_correct": True})
    resp = test_client.get("/api/score")
    assert resp.status_code == 200
    assert resp.json()["score"] == 1


# ==================== Tests: 完整流程 ====================

def test_full_flow(
    test_client: TestClient,
    mock_provider: MockProviderForAPI,
) -> None:
    """完整流程：topic → guess → feedback → score → 下一轮。"""
    # Step 1: 获取 topic
    resp1 = test_client.get("/api/topic")
    assert resp1.status_code == 200
    assert "topic" in resp1.json()
    topic: str = resp1.json()["topic"]
    mock_provider._result = PredictionResult(
        model_name="deepseek-v4-pro",
        guess=topic,
        confidence=0.9,
    )

    # Step 2: 提交猜画
    resp2 = test_client.post("/api/guess", json={"image_b64": _make_valid_image()})
    assert resp2.status_code == 200
    guess_data = resp2.json()
    assert "guess" in guess_data
    assert "confidence" in guess_data

    # Step 3: 反馈
    resp3 = test_client.post("/api/feedback", json={"user_says_correct": True})
    assert resp3.status_code == 200
    feedback_data = resp3.json()
    assert "scored" in feedback_data
    assert feedback_data["score"] == 1

    # Step 4: 查分
    resp4 = test_client.get("/api/score")
    assert resp4.status_code == 200
    assert resp4.json()["score"] == feedback_data["score"]

    # Step 5: 下一轮 — 重置 mock（guess 不匹配新 topic）
    # 不强制得分，只验证流程可继续
    resp5 = test_client.get("/api/topic")
    assert resp5.status_code == 200
    assert "topic" in resp5.json()
