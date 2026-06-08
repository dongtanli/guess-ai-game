"""通义千问 VL Provider — 实现 PredictorProtocol，对接 DashScope API。"""

import base64

import httpx

from src.core.contracts import QWEN_MODEL_NAME, PredictionResult

# 提示词：要求 AI 仅返回物品名称
_SYSTEM_PROMPT: str = "请用中文猜测这幅简笔画画的是什么，只返回物品名称，不要多余解释。"


class QwenProvider:
    """通义千问 VL Provider，兼容 OpenAI Chat Completions 格式。"""

    def __init__(self, api_key: str, api_url: str, model: str) -> None:
        self._api_key = api_key
        self._api_url = api_url
        self._model = model

    @property
    def name(self) -> str:
        return QWEN_MODEL_NAME

    async def predict(self, image_bytes: bytes) -> PredictionResult:
        """调用通义千问 VL API 识别图像内容。"""
        request_body = self._build_request(image_bytes)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._api_url + "/chat/completions",
                json=request_body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            return self._parse_response(response.json())

    def _build_request(self, image_bytes: bytes) -> dict[str, object]:
        """构造 OpenAI 兼容请求体。"""
        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        return {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _SYSTEM_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_data}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 50,
            "temperature": 0.1,
        }

    @staticmethod
    def _parse_response(raw: dict[str, object]) -> PredictionResult:
        """解析 API 响应为 PredictionResult。"""
        choices: list[dict[str, object]] = raw.get("choices", [])  # type: ignore[assignment]
        if not choices:
            return PredictionResult(
                model_name=QWEN_MODEL_NAME,
                guess="error",
                confidence=0.0,
                reasoning="Empty choices in API response.",
                fallback_triggered=True,
            )
        message: dict[str, object] = choices[0].get("message", {})  # type: ignore[assignment]
        guess: str = str(message.get("content", "")).strip()
        if not guess:
            return PredictionResult(
                model_name=QWEN_MODEL_NAME,
                guess="error",
                confidence=0.0,
                reasoning="Empty content in API message.",
                fallback_triggered=True,
            )
        return PredictionResult(
            model_name=QWEN_MODEL_NAME,
            guess=guess,
            confidence=0.8,
        )
