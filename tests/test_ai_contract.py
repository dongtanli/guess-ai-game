"""测试接口格式、超时、降级、置信度阈值。"""

import pytest
from pydantic import ValidationError

from src.core.contracts import (
    AI_TIMEOUT_SECONDS,
    ALLOWED_IMAGE_FORMATS,
    CONFIDENCE_THRESHOLD,
    FEEDBACK_OPTIONS,
    MAX_IMAGE_SIZE_BYTES,
    QWEN_MODEL_NAME,
    GameState,
    GuessRequest,
    ModelRegistry,
    PredictionResult,
    PredictorProtocol,
)

# ==================== PredictionResult 测试 ====================

def test_prediction_result_valid() -> None:
    """正常创建 PredictionResult。"""
    result = PredictionResult(
        model_name="qwen3-vl-flash",
        guess="苹果",
        confidence=0.85,
        reasoning="看起来像一个带叶子的圆形水果",
        fallback_triggered=False,
    )
    assert result.model_name == "qwen3-vl-flash"
    assert result.guess == "苹果"
    assert result.confidence == 0.85
    assert result.reasoning == "看起来像一个带叶子的圆形水果"
    assert result.fallback_triggered is False


def test_prediction_result_defaults() -> None:
    """PredictionResult 默认值：reasoning=None, fallback_triggered=False。"""
    result = PredictionResult(
        model_name="qwen3-vl-flash",
        guess="苹果",
        confidence=0.8,
    )
    assert result.reasoning is None
    assert result.fallback_triggered is False


def test_prediction_result_confidence_lower_bound() -> None:
    """confidence 可接受 0.0。"""
    result = PredictionResult(model_name="test", guess="test", confidence=0.0)
    assert result.confidence == 0.0


def test_prediction_result_confidence_upper_bound() -> None:
    """confidence 可接受 1.0。"""
    result = PredictionResult(model_name="test", guess="test", confidence=1.0)
    assert result.confidence == 1.0


def test_prediction_result_confidence_below_zero_raises() -> None:
    """confidence 小于 0 时抛出 ValidationError。"""
    with pytest.raises(ValidationError):
        PredictionResult(model_name="test", guess="test", confidence=-0.1)


def test_prediction_result_confidence_above_one_raises() -> None:
    """confidence 大于 1 时抛出 ValidationError。"""
    with pytest.raises(ValidationError):
        PredictionResult(model_name="test", guess="test", confidence=1.1)


def test_prediction_result_fallback_triggered() -> None:
    """fallback_triggered 为 True 降级场景。"""
    result = PredictionResult(
        model_name="qwen3-vl-flash",
        guess="timeout",
        confidence=0.0,
        fallback_triggered=True,
    )
    assert result.fallback_triggered is True
    assert result.confidence == 0.0


# ==================== GuessRequest 测试 ====================

def test_guess_request_valid() -> None:
    """正常创建 GuessRequest。"""
    b64_prefix = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCA"
    req = GuessRequest(image_b64=b64_prefix)
    assert req.image_b64.startswith("data:image/png;base64,")


def test_guess_request_min_length_boundary() -> None:
    """image_b64 长度刚好为 10 可以通过。"""
    req = GuessRequest(image_b64="a" * 10)
    assert len(req.image_b64) == 10


def test_guess_request_too_short_raises() -> None:
    """image_b64 长度小于 10 时抛出 ValidationError。"""
    with pytest.raises(ValidationError):
        GuessRequest(image_b64="short")


# ==================== GameState 枚举测试 ====================

def test_game_state_enum_values() -> None:
    """GameState 枚举值正确。"""
    assert GameState.DRAFT.value == "draft"
    assert GameState.GUESSING.value == "guessing"
    assert GameState.RESULT.value == "result"
    assert GameState.DONE.value == "done"


def test_game_state_is_string_enum() -> None:
    """GameState 继承自 str Enum。"""
    assert isinstance(GameState.DRAFT, str)
    assert GameState.DRAFT == "draft"


# ==================== ModelRegistry 测试 ====================

class _MockPredictor:
    """模拟 PredictorProtocol 的实现，用于测试注册表。"""

    def __init__(self, model_name: str) -> None:
        self._name = model_name

    @property
    def name(self) -> str:
        return self._name

    async def predict(self, image_bytes: bytes) -> PredictionResult:
        return PredictionResult(model_name=self._name, guess="mock", confidence=0.9)


def test_model_registry_register_and_get() -> None:
    """注册并获取 Provider。"""
    predictor = _MockPredictor("test-model")
    ModelRegistry.register(predictor)
    retrieved = ModelRegistry.get("test-model")
    assert retrieved is predictor
    assert retrieved.name == "test-model"


def test_model_registry_list_models() -> None:
    """list_models 返回已注册的名称列表。"""
    predictor = _MockPredictor("model-a")
    ModelRegistry.register(predictor)
    models = ModelRegistry.list_models()
    assert "model-a" in models


def test_model_registry_get_unregistered_raises() -> None:
    """获取未注册的模型抛出 ValueError。"""
    with pytest.raises(ValueError, match="not registered"):
        ModelRegistry.get("non-existent-model")


# ==================== PredictorProtocol 测试 ====================

def test_predictor_protocol_is_callable() -> None:
    """验证 PredictorProtocol 定义了 predict 和 name。"""
    assert hasattr(PredictorProtocol, "predict")
    assert hasattr(PredictorProtocol, "name")


# ==================== 常量测试 ====================

def test_max_image_size_bytes() -> None:
    """MAX_IMAGE_SIZE_BYTES 等于 2MB。"""
    assert MAX_IMAGE_SIZE_BYTES == 2 * 1024 * 1024


def test_allowed_image_formats_png_only() -> None:
    """ALLOWED_IMAGE_FORMATS 仅包含 PNG。"""
    assert ALLOWED_IMAGE_FORMATS == ["image/png"]


def test_ai_timeout_seconds() -> None:
    """AI_TIMEOUT_SECONDS 为 5.0。"""
    assert AI_TIMEOUT_SECONDS == 5.0


def test_confidence_threshold() -> None:
    """CONFIDENCE_THRESHOLD 为 0.65。"""
    assert CONFIDENCE_THRESHOLD == 0.65


def test_feedback_options() -> None:
    """FEEDBACK_OPTIONS 为二元判断。"""
    assert FEEDBACK_OPTIONS == ["correct", "incorrect"]


def test_qwen_model_name() -> None:
    """QWEN_MODEL_NAME 正确。"""
    assert QWEN_MODEL_NAME == "qwen3-vl-flash"


# ==================== safe_predict 测试 ====================

@pytest.mark.asyncio
async def test_safe_predict_normal() -> None:
    """safe_predict 正常路径：Predictor 返回有效结果。"""
    from src.services.ai_predictor import safe_predict
    from tests.conftest import MockPredictor

    predictor = MockPredictor()
    predictor._result = PredictionResult(
        model_name="test-model",
        guess="苹果",
        confidence=0.9,
    )
    result = await safe_predict(predictor, b"fake-image")
    assert result.guess == "苹果"
    assert result.confidence == 0.9
    assert result.fallback_triggered is False


@pytest.mark.asyncio
async def test_safe_predict_low_confidence_fallback() -> None:
    """safe_predict 低置信度：confidence < CONFIDENCE_THRESHOLD 时标记降级。"""
    from src.services.ai_predictor import safe_predict
    from tests.conftest import MockPredictor

    predictor = MockPredictor()
    predictor._result = PredictionResult(
        model_name="test-model",
        guess="不确定",
        confidence=0.3,
    )
    result = await safe_predict(predictor, b"fake-image")
    assert result.guess == "不确定"
    assert result.confidence == 0.3
    assert result.fallback_triggered is True


@pytest.mark.asyncio
async def test_safe_predict_timeout() -> None:
    """safe_predict 超时：返回降级 guess='timeout'。"""
    from src.core.contracts import AI_TIMEOUT_SECONDS
    from src.services.ai_predictor import safe_predict
    from tests.conftest import MockPredictor

    predictor = MockPredictor()
    predictor._delay = AI_TIMEOUT_SECONDS + 1.0

    result = await safe_predict(predictor, b"fake-image")
    assert result.guess == "timeout"
    assert result.confidence == 0.0
    assert result.fallback_triggered is True
    assert result.model_name == predictor.name


@pytest.mark.asyncio
async def test_safe_predict_exception() -> None:
    """safe_predict 异常：返回降级 guess='error'。"""
    from src.services.ai_predictor import safe_predict
    from tests.conftest import MockPredictor

    predictor = MockPredictor()
    predictor._should_fail = RuntimeError("Provider crashed")

    result = await safe_predict(predictor, b"fake-image")
    assert result.guess == "error"
    assert result.confidence == 0.0
    assert result.fallback_triggered is True
    assert result.model_name == predictor.name


# ==================== QwenProvider 测试 ====================

class TestQwenProvider:
    """QwenProvider 单元测试（Mock httpx）。"""

    @staticmethod
    def _make_mock_response(choices_content: str) -> dict:
        """构造标准 OpenAI 兼容响应。"""
        return {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": choices_content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 20},
        }

    @pytest.mark.asyncio
    async def test_name_property(self) -> None:
        """name 属性返回 QWEN_MODEL_NAME。"""
        from src.services.providers.qwen import QwenProvider

        provider = QwenProvider(
            api_key="sk-test", api_url="https://test.api/", model="qwen3-vl-flash"
        )
        assert provider.name == "qwen3-vl-flash"

    def test_build_request_format(self) -> None:
        """_build_request 构造的请求体格式正确。"""
        import base64

        from src.core.contracts import QWEN_MODEL_NAME
        from src.services.providers.qwen import QwenProvider

        provider = QwenProvider(
            api_key="sk-test", api_url="https://test.api/", model=QWEN_MODEL_NAME
        )
        image_data = b"\x89PNG\r\n\x1a\n"
        request_body = provider._build_request(image_data)

        assert request_body["model"] == QWEN_MODEL_NAME
        assert request_body["max_tokens"] == 50
        assert request_body["temperature"] == 0.1

        messages = request_body["messages"]
        assert isinstance(messages, list)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

        content = messages[0]["content"]
        assert isinstance(content, list)
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert "简笔画" in content[0]["text"]
        assert content[1]["type"] == "image_url"
        assert "image_url" in content[1]
        assert "url" in content[1]["image_url"]
        assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")

        expected_b64 = base64.b64encode(image_data).decode("utf-8")
        assert content[1]["image_url"]["url"] == f"data:image/png;base64,{expected_b64}"

    def test_parse_response_normal(self) -> None:
        """_parse_response 正常解析 API 响应。"""
        from src.services.providers.qwen import QwenProvider

        raw = self._make_mock_response("苹果")
        result = QwenProvider._parse_response(raw)

        assert result.guess == "苹果"
        assert result.confidence == 0.8
        assert result.model_name == "qwen3-vl-flash"
        assert result.fallback_triggered is False

    def test_parse_response_empty_choices(self) -> None:
        """_parse_response choices 为空时返回降级。"""
        from src.services.providers.qwen import QwenProvider

        raw: dict = {"choices": []}
        result = QwenProvider._parse_response(raw)

        assert result.guess == "error"
        assert result.confidence == 0.0
        assert result.fallback_triggered is True
        assert "Empty choices" in (result.reasoning or "")

    def test_parse_response_missing_content(self) -> None:
        """_parse_response message.content 为空时返回降级。"""
        from src.services.providers.qwen import QwenProvider

        raw = self._make_mock_response("")
        result = QwenProvider._parse_response(raw)

        assert result.guess == "error"
        assert result.confidence == 0.0
        assert result.fallback_triggered is True

    def test_parse_response_malformed(self) -> None:
        """_parse_response 畸形容错：缺失 choices 键。"""
        from src.services.providers.qwen import QwenProvider

        raw: dict = {"unexpected": "format"}
        result = QwenProvider._parse_response(raw)

        assert result.guess == "error"
        assert result.confidence == 0.0
        assert result.fallback_triggered is True

    @pytest.mark.asyncio
    async def test_predict_success(self) -> None:
        """predict 端到端（Mock httpx）：正常响应。"""
        from unittest.mock import AsyncMock, MagicMock, patch

        from src.services.providers.qwen import QwenProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._make_mock_response("飞机")
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            provider = QwenProvider(
                api_key="sk-test", api_url="https://test.api/", model="qwen3-vl-flash"
            )
            result = await provider.predict(b"fake-image")

        assert result.guess == "飞机"
        assert result.confidence == 0.8
        assert result.model_name == "qwen3-vl-flash"
        assert result.fallback_triggered is False

    @pytest.mark.asyncio
    async def test_predict_http_error(self) -> None:
        """predict 端到端（Mock httpx）：HTTP 4xx/5xx 抛异常。"""
        from unittest.mock import AsyncMock, MagicMock, patch

        import httpx

        from src.services.providers.qwen import QwenProvider

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            provider = QwenProvider(
                api_key="sk-test", api_url="https://test.api/", model="qwen3-vl-flash"
            )
            with pytest.raises(httpx.HTTPStatusError):
                await provider.predict(b"fake-image")


# ==================== db.py 测试 ====================

@pytest.mark.asyncio
async def test_init_db_idempotent(tmp_path: str) -> None:
    """init_db 重复执行不报错（幂等）。"""
    import os

    import aiosqlite

    from src.services.db import init_db

    db_path = os.path.join(tmp_path, "test_idempotent.db")
    await init_db(db_path)
    await init_db(db_path)

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='rounds'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "rounds"


@pytest.mark.asyncio
async def test_init_db_creates_index(tmp_path: str) -> None:
    """init_db 创建索引。"""
    import os

    import aiosqlite

    from src.services.db import init_db

    db_path = os.path.join(tmp_path, "test_index.db")
    await init_db(db_path)

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_rounds_created_at'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "idx_rounds_created_at"


@pytest.mark.asyncio
async def test_insert_and_list_rounds(test_db: str) -> None:
    """insert_round + list_rounds 读写一致性。"""
    from src.services.db import insert_round, list_rounds

    await insert_round(test_db, "苹果", "苹果", True, "qwen3-vl-flash")
    await insert_round(test_db, "太阳", "月亮", False, "qwen3-vl-flash")

    records = await list_rounds(test_db, limit=10)
    assert len(records) == 2

    assert records[0]["guess"] == "月亮"
    assert records[0]["topic"] == "太阳"
    assert records[0]["is_correct"] == 0
    assert records[0]["model_name"] == "qwen3-vl-flash"

    assert records[1]["guess"] == "苹果"
    assert records[1]["topic"] == "苹果"
    assert records[1]["is_correct"] == 1


@pytest.mark.asyncio
async def test_list_rounds_limit(test_db: str) -> None:
    """list_rounds 尊重 limit 参数。"""
    from src.services.db import insert_round, list_rounds

    for i in range(5):
        await insert_round(test_db, f"topic-{i}", f"guess-{i}", True, "qwen3-vl-flash")

    records = await list_rounds(test_db, limit=3)
    assert len(records) == 3


@pytest.mark.asyncio
async def test_list_rounds_empty(test_db: str) -> None:
    """list_rounds 在空表时返回空列表。"""
    from src.services.db import list_rounds

    records = await list_rounds(test_db, limit=10)
    assert records == []


@pytest.mark.asyncio
async def test_insert_round_bool_conversion(test_db: str) -> None:
    """insert_round 正确将 bool 转为 INTEGER。"""
    from src.services.db import insert_round, list_rounds

    await insert_round(test_db, "test", "guess", True, "qwen3-vl-flash")
    await insert_round(test_db, "test2", "guess2", False, "qwen3-vl-flash")

    records = await list_rounds(test_db)
    assert records[0]["is_correct"] == 0
    assert records[1]["is_correct"] == 1
