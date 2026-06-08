"""Mock AI、临时 DB、异步 fixture。"""

import asyncio

import pytest

from src.core.contracts import PredictionResult

# ==================== Mock Predictor fixture ====================

class MockPredictor:
    """可控制返回值的 Mock Predictor，用于 safe_predict 测试。"""

    def __init__(self, model_name: str = "mock-model") -> None:
        self._name = model_name
        self._delay: float = 0.0
        self._result = PredictionResult(
            model_name=model_name,
            guess="mock-guess",
            confidence=0.9,
        )
        self._should_fail: Exception | None = None

    @property
    def name(self) -> str:
        return self._name

    async def predict(self, image_bytes: bytes) -> PredictionResult:
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        if self._should_fail is not None:
            raise self._should_fail
        return self._result


@pytest.fixture
def mock_predictor() -> MockPredictor:
    """返回可配置的 MockPredictor 实例。"""
    return MockPredictor()


# ==================== DB 临时数据库 fixture ====================

@pytest.fixture
async def test_db(tmp_path: str) -> str:
    """提供临时文件数据库。"""
    import os

    from src.services.db import init_db

    db_path = os.path.join(tmp_path, "test_guess.db")
    await init_db(db_path)
    return db_path
