"""只读契约：数据结构、枚举、阈值、接口协议。"""

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

# ================= 1. 核心常量与边界 =================
MAX_IMAGE_SIZE_BYTES: int = 2 * 1024 * 1024  # 2MB 上限
ALLOWED_IMAGE_FORMATS: list[str] = ["image/png"]  # V1 仅 PNG
AI_TIMEOUT_SECONDS: float = 5.0
CONFIDENCE_THRESHOLD: float = 0.65
FEEDBACK_OPTIONS: list[str] = ["correct", "incorrect"]  # V1 二元判断
QWEN_MODEL_NAME: str = "qwen3-vl-flash"  # 注册表 key


# ================= 2. 状态枚举 =================
class GameState(StrEnum):
    """回合状态枚举，前后端/状态机同源引用。"""
    DRAFT = "draft"
    GUESSING = "guessing"
    RESULT = "result"
    DONE = "done"


# ================= 3. 数据结构契约 =================
class PredictionResult(BaseModel):
    """AI 返回的标准化结果，所有 Provider 必须严格匹配此结构。"""
    model_name: str
    guess: str
    confidence: float
    reasoning: str | None = None
    fallback_triggered: bool = False

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class GuessRequest(BaseModel):
    """前端提交的标准请求体。"""
    image_b64: str = Field(..., min_length=10)  # data:image/png;base64,... 前缀


# ================= 4. 协议接口契约 =================
class PredictorProtocol(Protocol):
    """所有 AI Provider 必须实现此接口。业务层仅依赖此签名。"""
    async def predict(self, image_bytes: bytes) -> PredictionResult: ...
    @property
    def name(self) -> str: ...


class ModelRegistry:
    """模型注册表，Router 仅通过此类获取实例，禁止直连 Provider。"""
    _registry: dict[str, PredictorProtocol] = {}

    @classmethod
    def register(cls, predictor: PredictorProtocol) -> None:
        cls._registry[predictor.name] = predictor

    @classmethod
    def get(cls, name: str) -> PredictorProtocol:
        if name not in cls._registry:
            raise ValueError(
                f"Model '{name}' not registered. Available: {list(cls._registry.keys())}"
            )
        return cls._registry[name]

    @classmethod
    def list_models(cls) -> list[str]:
        return list(cls._registry.keys())
