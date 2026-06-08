"""PredictorProtocol 协议定义 & Mock 实现，以及安全预测包装器。"""

import asyncio

from src.core.contracts import (
    AI_TIMEOUT_SECONDS,
    CONFIDENCE_THRESHOLD,
    PredictionResult,
    PredictorProtocol,
)


async def safe_predict(predictor: PredictorProtocol, image_bytes: bytes) -> PredictionResult:
    """契约级安全包装：强制超时 + 自动降级 + 置信度阈值校验。

    所有调用方无需自行实现超时/异常处理，统一走此函数。
    """
    try:
        result = await asyncio.wait_for(
            predictor.predict(image_bytes),
            timeout=AI_TIMEOUT_SECONDS,
        )
        # 低于置信度阈值标记降级
        if result.confidence < CONFIDENCE_THRESHOLD:
            result.fallback_triggered = True
        return result
    except TimeoutError:
        return PredictionResult(
            model_name=predictor.name,
            guess="timeout",
            confidence=0.0,
            reasoning="AI inference exceeded timeout threshold.",
            fallback_triggered=True,
        )
    except Exception as e:
        return PredictionResult(
            model_name=predictor.name,
            guess="error",
            confidence=0.0,
            reasoning=f"Provider error: {str(e)}",
            fallback_triggered=True,
        )
