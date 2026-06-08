# 01-core-contracts — 核心契约与基础模块

## 概述

实现项目的基础层：数据结构契约、常量枚举、配置管理、词库、前端类型定义。所有模块均无外部依赖，可独立实现和测试。

## 涉及文件

| 文件 | 说明 |
|------|------|
| `src/core/contracts.py` | 数据结构 + GameState 枚举 + PredictorProtocol + ModelRegistry |
| `src/core/config.py` | Pydantic Settings，从 .env 加载 DEEPSEEK_API_KEY |
| `src/core/word_bank.py` | 50-100 个中文名词词库 + `get_random_topic()` |
| `frontend/src/types.ts` | AppState 枚举 + API 请求/响应类型 |

---

## 任务清单

### T1.1 contracts.py — 数据结构契约

- [ ] `PredictionResult(BaseModel)`：5 字段 + confidence field_validator [0,1]
- [ ] `GuessRequest(BaseModel)`：image_b64 字段，min_length=10
- [ ] `GameState(str, Enum)`：DRAFT / GUESSING / RESULT / DONE
- [ ] `PredictorProtocol(Protocol)`：`predict()` + `name` property
- [ ] `ModelRegistry`：register / get / list_models 类方法
- [ ] 常量：MAX_IMAGE_SIZE_BYTES, ALLOWED_IMAGE_FORMATS, AI_TIMEOUT_SECONDS, CONFIDENCE_THRESHOLD, FEEDBACK_OPTIONS, DEEPSEEK_MODEL_NAME

### T1.2 config.py — 配置管理

- [ ] `class Settings(BaseSettings)`：deepseek_api_key（必填）、deepseek_api_url、deepseek_model、database_url、log_level
- [ ] `SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")`
- [ ] 模块级单例 `settings = Settings()`

### T1.3 word_bank.py — 词库

- [ ] `WORDS: list[str]` — 50-100 个常见中文名词
- [ ] `get_random_topic() -> str` — 使用 `random.choice(WORDS)`

### T1.4 types.ts — 前端类型

- [ ] `enum AppState { DRAWING, GUESSING, RESULT, FEEDBACK_DONE }`
- [ ] `interface TopicResponse { topic: string }`
- [ ] `interface GuessResponse { guess: string; confidence: number; model: string }`
- [ ] `interface FeedbackRequest { user_says_correct: boolean }`
- [ ] `interface FeedbackResponse { scored: boolean; score: number }`
- [ ] `interface ScoreResponse { score: number }`
- [ ] `type Tool = "pen" | "eraser"`

---

## 验收标准

### 后端

| 检查项 | 命令 | 阈值 |
|--------|------|------|
| Ruff | `uv run ruff check src/core/` | 0 errors |
| Mypy | `uv run mypy src/core/ --strict` | 0 issues |
| Pytest | `uv run pytest tests/test_word_bank.py tests/test_ai_contract.py --cov=src/core --cov-fail-under=90` | 全绿 |
| 覆盖率 | line≥90%, branch≥85% | — |

### 前端

| 检查项 | 命令 | 阈值 |
|--------|------|------|
| TypeScript | `cd frontend && npx tsc --noEmit` | 0 errors |

---

## 依赖

无外部模块依赖。本模块是其他所有模块的基础。
