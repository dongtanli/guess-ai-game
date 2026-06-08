# 04-api-layer — API 路由与依赖注入

## 概述

实现 FastAPI 路由层、依赖注入、应用入口。编排 Core + Services 层，对外暴露 4 个 REST 端点。

## 涉及文件

| 文件 | 说明 |
|------|------|
| `src/api/deps.py` | 依赖注入（GameSession / Predictor / DB 路径单例） |
| `src/api/routes.py` | 4 个 API 端点（topic / guess / feedback / score） |
| `src/main.py` | FastAPI app 创建 + CORS + 启动初始化 |

---

## 任务清单

### T4.1 deps.py — 依赖注入

- [ ] `get_session() -> GameSession`：模块级懒加载单例
- [ ] `get_predictor() -> DeepSeekProvider`：从 config 读取 api_key/api_url 构造
- [ ] `get_db_path() -> str`：从 config 读取 database_url 并解析路径
- [ ] 单例线程安全（使用模块级全局变量）

### T4.2 routes.py — API 端点

**GET /api/topic**
- [ ] 调用 `get_random_topic()`
- [ ] `session.start_round(topic)`
- [ ] 返回 `{"topic": topic}`

**POST /api/guess**
- [ ] 请求体：`GuessRequest`（Pydantic 自动校验）
- [ ] 手动校验：base64 解码 → 大小 ≤ 2MB
- [ ] 手动校验：前缀 `data:image/png;base64,`
- [ ] `session.submit_guess()` → 标记状态
- [ ] `safe_predict(predictor, image_bytes)` → 获取结果
- [ ] `session.receive_result(result.guess)` → 更新状态
- [ ] 返回 `{"guess": ..., "confidence": ..., "model": ...}`

**POST /api/feedback**
- [ ] 请求体：`{ user_says_correct: bool }`
- [ ] `scored, new_score = session.process_feedback(user_says_correct)`
- [ ] `await insert_round(...)`
- [ ] 返回 `{"scored": scored, "score": new_score}`

**GET /api/score**
- [ ] 返回 `{"score": session.score}`

**错误处理**
- [ ] 状态屏障违规 → 400 `{"detail": "invalid state transition"}`
- [ ] 图片过大 → 400 `{"detail": "image exceeds 2MB limit"}`
- [ ] 格式错误 → 400 `{"detail": "only PNG format is allowed"}`
- [ ] base64 解码失败 → 400 `{"detail": "invalid base64 encoding"}`
- [ ] AI 降级 → 200（含降级结果，不是 5xx）
- [ ] DB 错误 → 500

### T4.3 main.py — 应用入口

- [ ] `app = FastAPI(title="你画我猜 AI")`
- [ ] `app.add_middleware(CORSMiddleware, allow_origins=["*"])`
- [ ] `app.include_router(router, prefix="/api")`
- [ ] `@app.on_event("startup")` → `await init_db(get_db_path())`
- [ ] `if __name__ == "__main__"` → `uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)`

---

## 验收标准

| 检查项 | 命令 | 阈值 |
|--------|------|------|
| Ruff | `uv run ruff check src/api/ src/main.py` | 0 errors |
| Mypy | `uv run mypy src/api/ src/main.py --strict` | 0 issues |
| Pytest | `uv run pytest tests/test_api.py --cov=src/api --cov-fail-under=90` | 全绿 |
| 覆盖率 | line≥90%, branch≥85% | — |

### 测试用例最小覆盖

- [ ] GET /api/topic → 200，返回合法 topic
- [ ] POST /api/guess → 200，返回 guess/confidence/model
- [ ] POST /api/guess（图片过大）→ 400
- [ ] POST /api/guess（非 PNG 前缀）→ 400
- [ ] POST /api/guess（无效 base64）→ 400
- [ ] POST /api/guess（AI 超时降级）→ 200（非 5xx）
- [ ] POST /api/feedback（得分）→ 200，scored=true
- [ ] POST /api/feedback（不得分）→ 200，scored=false
- [ ] POST /api/feedback（状态屏障）→ 400
- [ ] GET /api/score → 200，返回当前分数
- [ ] 完整流程：topic → guess → feedback → score

---

## 依赖

- `src/core/contracts.py`
- `src/core/state_machine.py`
- `src/core/config.py`
- `src/core/word_bank.py`
- `src/services/ai_predictor.py`
- `src/services/providers/deepseek.py`
- `src/services/db.py`
