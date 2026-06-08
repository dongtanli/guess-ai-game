# 03-ai-services — AI 预测与数据服务

## 概述

实现 AI Provider（DeepSeek）、安全预测包装器（safe_predict）、SQLite 持久化层。所有模块通过 Mock 接口可独立测试，不依赖真实 API 或数据库服务。

## 涉及文件

| 文件 | 说明 |
|------|------|
| `src/services/providers/deepseek.py` | DeepSeekProvider，实现 PredictorProtocol |
| `src/services/ai_predictor.py` | safe_predict() 包装器（已有骨架，需完善） |
| `src/services/db.py` | SQLite 初始化 + rounds 表 CRUD |

---

## 任务清单

### T3.1 deepseek.py — DeepSeek Provider

- [ ] `class DeepSeekProvider`：实现 `PredictorProtocol`
- [ ] `name` property → 返回 `DEEPSEEK_MODEL_NAME`
- [ ] `__init__(api_key: str, api_url: str)`：接收运行时配置
- [ ] `async predict(image_bytes: bytes) -> PredictionResult`：
  - [ ] 构造 OpenAI 兼容请求体（`model`, `messages[].content[]` 含 text + image_url）
  - [ ] POST 到 `deepseek_api_url`，Header `Authorization: Bearer {api_key}`
  - [ ] 解析 `choices[0].message.content` → `PredictionResult.guess`
  - [ ] 固定 `confidence=0.8`（DeepSeek 无置信度字段）
  - [ ] HTTP 4xx/5xx 应 raise 异常（由 safe_predict 捕获）

### T3.2 ai_predictor.py — 安全预测包装器

- [ ] `async def safe_predict(predictor: PredictorProtocol, image_bytes: bytes) -> PredictionResult`
- [ ] `asyncio.wait_for(predictor.predict(...), timeout=AI_TIMEOUT_SECONDS)`
- [ ] 成功且 confidence < CONFIDENCE_THRESHOLD → 设置 `fallback_triggered=True`
- [ ] `asyncio.TimeoutError` → 返回降级 `PredictionResult(guess="timeout", confidence=0.0, fallback_triggered=True)`
- [ ] 其他 `Exception` → 返回降级 `PredictionResult(guess="error", confidence=0.0, fallback_triggered=True)`

### T3.3 db.py — 数据持久化

- [ ] `async def init_db(db_path: str) -> None`：CREATE TABLE + CREATE INDEX
- [ ] `async def insert_round(db_path, topic, guess, is_correct, model_name) -> None`
- [ ] `async def list_rounds(db_path, limit=20) -> list[dict]`
- [ ] 使用 `aiosqlite` 异步连接
- [ ] 表结构：id, topic, guess, is_correct, model_name, created_at

---

## 验收标准

| 检查项 | 命令 | 阈值 |
|--------|------|------|
| Ruff | `uv run ruff check src/services/` | 0 errors |
| Mypy | `uv run mypy src/services/ --strict` | 0 issues |
| Pytest | `uv run pytest tests/test_ai_contract.py --cov=src/services --cov-fail-under=90` | 全绿 |
| 覆盖率 | line≥90%, branch≥85% | — |
| Mock 覆盖率 | 所有测试不直连真实 API/DB | 100% |

### 测试用例最小覆盖

- [ ] safe_predict 正常路径：Predictor 返回有效结果
- [ ] safe_predict 低置信度：`fallback_triggered=True`
- [ ] safe_predict 超时：返回降级 `guess="timeout"`
- [ ] safe_predict 异常：返回降级 `guess="error"`
- [ ] deepseek.py 请求体格式正确（Mock httpx）
- [ ] deepseek.py 响应解析：正常/空/畸形
- [ ] db.py init_db 重复执行幂等
- [ ] db.py insert_round + list_rounds 读写一致性

---

## 依赖

- `src/core/contracts.py`（常量 + PredictorProtocol + PredictionResult）
- `src/core/config.py`（API Key / URL）
- 不依赖 state_machine / api 层
