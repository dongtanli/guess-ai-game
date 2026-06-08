# 你画我猜 AI — 详细设计文档 V1

---

## 1. 模块详细设计

### 1.1 `src/core/contracts.py` — 契约定义（只读仲裁）

```
导出接口:
  PredictionResult(BaseModel)  — AI 预测结果
  GuessRequest(BaseModel)      — 前端提交请求
  PredictorProtocol(Protocol)  — AI Provider 接口协议
  ModelRegistry                — Provider 注册表（单例）
  
常量:
  MAX_IMAGE_SIZE_BYTES: 2MB
  ALLOWED_IMAGE_FORMATS: ["image/png"]
  AI_TIMEOUT_SECONDS: 5.0
  CONFIDENCE_THRESHOLD: 0.65
  FEEDBACK_OPTIONS: ["correct", "incorrect"]
  DEEPSEEK_MODEL_NAME: "deepseek-v4-pro"
```

**`PredictionResult`**:
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| model_name | str | 非空 | Provider 名称 |
| guess | str | 非空 | AI 猜测内容 |
| confidence | float | [0.0, 1.0] | 置信度 |
| reasoning | str\|None | — | AI 推理说明 |
| fallback_triggered | bool | 默认 False | 是否触发降级 |

**`GuessRequest`**:
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| image_b64 | str | min_length=10 | PNG base64，前缀 `data:image/png;base64,` |

---

### 1.2 `src/core/config.py` — 配置管理

```
class Settings(BaseSettings):
    deepseek_api_key: str          # 从 .env 加载 DEEPSEEK_API_KEY
    deepseek_api_url: str = "https://api.deepseek.com/v1/chat/completions"
    deepseek_model: str = "deepseek-v4-pro"
    database_url: str = "sqlite:///./guess.db"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

依赖：`pydantic-settings`

---

### 1.3 `src/core/word_bank.py` — 词库

```
导出:
  WORDS: list[str]  — 50-100 个常见中文名词（只读常量）
  get_random_topic() -> str  — 随机抽取一个题目

实现:
  import random
  WORDS = ["苹果", "自行车", "太阳", ...]
  def get_random_topic() -> str: return random.choice(WORDS)
```

依赖：无外部依赖。

---

### 1.4 `src/core/state_machine.py` — 回合状态机

```
类: GameSession

属性:
  _state: GameState                  # 当前状态
  _current_topic: str                # 当前题目
  _ai_guess: str | None              # AI 猜测结果
  _score: int                        # 累计分数

状态枚举:
  GameState = DRAFT | GUESSING | RESULT | DONE

方法签名:
  def __init__(self) -> None                                                # 初始状态 DRAFT, score=0
  def start_round(self, topic: str) -> None                                 # DRAFT → 设置 topic
  def submit_guess(self, guess: str) -> None                                # DRAFT → GUESSING
  def receive_result(self, guess: str) -> None                              # GUESSING → RESULT
  def process_feedback(self, user_says_correct: bool) -> tuple[bool, int]   # RESULT → DONE; 返回 (是否得分, 新分数)
  def next_round(self) -> None                                              # DONE → DRAFT

辅助函数:
  def is_correct_guess(topic: str, guess: str) -> bool   # 包含匹配: topic in guess
  def calculate_score(user_says_correct: bool, ai_correct: bool) -> int  # 返回 1 或 0

public:
  @property state -> GameState
  @property score -> int
  @property current_topic -> str
  @property ai_guess -> str | None
```

**计分逻辑（纯函数）**:
```
def calculate_score(user_says_correct: bool, ai_correct: bool) -> int:
    return 1 if (user_says_correct and ai_correct) else 0
```

**依赖**: `word_bank.py`（仅引用，不 import），`contracts.py`（GameState 枚举定义于此）。

---

### 1.5 `src/services/providers/deepseek.py` — DeepSeek Provider

```
类: DeepSeekProvider

实现 PredictorProtocol:
  @property
  def name(self) -> str                                → return "deepseek-v4-pro"
  async def predict(self, image_bytes: bytes) -> PredictionResult  → 调用 DeepSeek API

内部方法:
  def _build_request(self, image_bytes: bytes) -> dict   → 构造 OpenAI 兼容 JSON
  def _parse_response(self, raw: dict) -> PredictionResult → 解析 API 响应

请求体格式:
  POST https://api.deepseek.com/v1/chat/completions
  Headers: Authorization: Bearer {api_key}, Content-Type: application/json
  Body:
    {
      "model": "deepseek-v4-pro",
      "messages": [{
        "role": "user",
        "content": [
          {"type": "text", "text": "请用中文猜测这幅简笔画画的是什么，只返回物品名称，不要多余解释。"},
          {"type": "image_url", "image_url": {"url": "data:image/png;base64,<base64>"}}
        ]
      }],
      "max_tokens": 50,
      "temperature": 0.1
    }

响应解析:
  choices[0].message.content → PredictionResult.guess
  无 confidence 字段 → 固定返回 0.8
  model → PredictionResult.model_name
```

**依赖**: `contracts.py`、`config.py`（api_key）、`httpx`

---

### 1.6 `src/services/ai_predictor.py` — 安全预测包装器

```
导出:
  async def safe_predict(predictor: PredictorProtocol, image_bytes: bytes) -> PredictionResult

行为:
  1. asyncio.wait_for(predictor.predict(...), timeout=5s)
  2. 成功 → 检查 confidence >= 0.65, 低于则 mark fallback_triggered=True
  3. TimeoutError → 返回降级 PredictionResult(guess="timeout", confidence=0.0, fallback_triggered=True)
  4. 其他异常 → 返回降级 PredictionResult(guess="error", confidence=0.0, fallback_triggered=True)
```

**依赖**: `contracts.py`（AI_TIMEOUT_SECONDS、CONFIDENCE_THRESHOLD、PredictorProtocol、PredictionResult）

---

### 1.7 `src/services/db.py` — 数据持久化

```
导出:
  async def init_db(db_path: str) -> None              → 创建表 + 索引
  async def insert_round(db_path: str, topic: str, guess: str, is_correct: bool, model_name: str) -> None
  async def list_rounds(db_path: str, limit: int = 20) -> list[dict]

SQL:
  CREATE TABLE IF NOT EXISTS rounds (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      topic       TEXT NOT NULL,
      guess       TEXT NOT NULL,
      is_correct  INTEGER NOT NULL,
      model_name  TEXT NOT NULL,
      created_at  TEXT NOT NULL DEFAULT (datetime('now'))
  );
  CREATE INDEX IF NOT EXISTS idx_rounds_created_at ON rounds(created_at);
```

**依赖**: `aiosqlite`（已在 pyproject.toml）

---

### 1.8 `src/api/deps.py` — 依赖注入

```
导出:
  def get_session() -> GameSession    → 全局单例 GameSession
  def get_predictor() -> DeepSeekProvider  → 全局单例 DeepSeekProvider
  def get_db_path() -> str            → 从 config 获取数据库路径

实现: 模块级懒加载单例。
```

**依赖**: `state_machine.py`、`providers/deepseek.py`、`config.py`

---

### 1.9 `src/api/routes.py` — API 路由

```
路由前缀: /api
全局 router = APIRouter()

1. GET /api/topic
   → 调用 get_random_topic()
   → session.start_round(topic)
   → 返回 200 {"topic": topic}

2. POST /api/guess
   → 请求体: GuessRequest { image_b64: str }
   → 校验: 解析 base64 大小 < 2MB, 前缀必须为 data:image/png;base64,
   → 解码为 bytes
   → session.submit_guess(placeholder)  # 先标记状态
   → result = await safe_predict(predictor, image_bytes)
   → session.receive_result(result.guess)
   → 返回 200 {"guess": result.guess, "confidence": result.confidence, "model": result.model_name}

3. POST /api/feedback
   → 请求体: { user_says_correct: bool }
   → scored, new_score = session.process_feedback(user_says_correct)
   → await insert_round(db_path, session.current_topic, session.ai_guess, scored, "deepseek-v4-pro")
   → 返回 200 {"scored": scored, "score": new_score}

4. GET /api/score
   → 返回 200 {"score": session.score}
```

**依赖**: `contracts.py`、`state_machine.py`、`services/`

---

### 1.10 `src/main.py` — 应用入口

```
1. 创建 FastAPI app (title="你画我猜 AI")
2. 注册 CORS 中间件 (allow_origins=["*"], V1 开发环境)
3. 挂载 routes.router
4. @app.on_event("startup") → init_db()
5. if __name__ == "__main__" → uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
```

---

### 1.11 `frontend/src/types.ts` — 前端类型

```typescript
export enum AppState {
  DRAWING       = "drawing",
  GUESSING      = "guessing",
  RESULT        = "result",
  FEEDBACK_DONE = "feedback_done",
}

export interface TopicResponse  { topic: string }
export interface GuessResponse  { guess: string; confidence: number; model: string }
export interface FeedbackRequest  { user_says_correct: boolean }
export interface FeedbackResponse { scored: boolean; score: number }
export interface ScoreResponse  { score: number }

export type Tool = "pen" | "eraser";
```

---

### 1.12 `frontend/src/api.ts` — API 客户端

```typescript
const BASE = "/api";

export async function fetchTopic(): Promise<TopicResponse>;
export async function submitGuess(imageB64: string): Promise<GuessResponse>;
export async function sendFeedback(userSaysCorrect: boolean): Promise<FeedbackResponse>;
export async function getScore(): Promise<ScoreResponse>;
```

每个函数：
- 使用 `fetch()`
- 统一错误处理：非 2xx → throw `Error(await res.text())`
- POST 请求 Content-Type: application/json

---

### 1.13 `frontend/src/canvas.ts` — 画板模块

```
export class DrawingCanvas
  constructor(canvasElement: HTMLCanvasElement)

  // 属性
  BRUSH_SIZE: 3
  ERASER_SIZE: 15
  BRUSH_COLOR: "#000000"

  // 方法
  setTool(tool: Tool): void                          → 切换 pen/eraser
  clear(): void                                      → 清空画板并填充白色
  exportBase64(): string                             → toDataURL("image/png"), 返回完整 data:image/png;base64,...

  // 内部事件处理 (构造函数中绑定)
  onMouseDown(e: MouseEvent): void
  onMouseMove(e: MouseEvent): void
  onMouseUp(e: MouseEvent): void
```

绘制逻辑：
- 画笔模式：`ctx.strokeStyle = "#000000"`, `ctx.lineWidth = 3`, `ctx.lineCap = "round"`
- 橡皮擦模式：`ctx.globalCompositeOperation = "destination-out"`, `ctx.lineWidth = 15`
- Canvas 尺寸：500×400（HTML 属性 + CSS 均设置），devicePixelRatio 缩放适配高清屏

---

### 1.14 `frontend/src/main.ts` — 应用入口

```
全局变量:
  let appState: AppState = AppState.DRAWING
  let currentScore: number = 0
  let canvas: DrawingCanvas
  let currentTool: Tool = "pen"

初始化:
  DOMContentLoaded →
    1. 获取 DOM 引用: canvasEl, btnClear, btnEraser, btnPen, btnSubmit, btnNext, btnYes, btnNo,
       elTopic, elResult, elScore, elLoading
    2. canvas = new DrawingCanvas(canvasEl)
    3. loadTopic() → 显示题目
    4. 绑定按钮事件

关键函数:
  async loadTopic(): Promise<void>
    → const { topic } = await fetchTopic()
    → elTopic.textContent = `请画：${topic}`

  async handleSubmit(): Promise<void>
    → setState(AppState.GUESSING)
    → 禁用提交按钮，显示加载动画
    → const b64 = canvas.exportBase64()
    → const result = await submitGuess(b64)
    → elResult.textContent = `AI 猜：${result.guess}`
    → setState(AppState.RESULT)
    → 显示 ✅/❌ 按钮

  async handleFeedback(userSaysCorrect: boolean): Promise<void>
    → const res = await sendFeedback(userSaysCorrect)
    → currentScore = res.score
    → elScore.textContent = `得分：${currentScore}`
    → setState(AppState.FEEDBACK_DONE)
    → 禁用 ✅/❌，启用 [下一轮]

  async handleNextRound(): Promise<void>
    → canvas.clear()
    → await loadTopic()
    → elResult.textContent = ""
    → setState(AppState.DRAWING)
    → 恢复按钮状态

  setState(newState: AppState): void
    → 根据状态启用/禁用对应按钮区域
```

---

## 2. 数据结构设计

### 2.1 内存数据结构

```
GameSession (state_machine.py):
  _state: GameState           # enum: DRAFT | GUESSING | RESULT | DONE
  _current_topic: str          # "苹果"
  _ai_guess: str | None        # "一个红苹果" 或 None
  _score: int                  # 0, 1, 2, ...
```

### 2.2 持久化数据结构

```sql
rounds 表:
  id          INTEGER   -- 自增主键
  topic       TEXT      -- "苹果"
  guess       TEXT      -- "一个红苹果"
  is_correct  INTEGER   -- 1 (得分) 或 0 (未得分)
  model_name  TEXT      -- "deepseek-v4-pro"
  created_at  TEXT      -- "2026-05-29T12:00:00"
```

### 2.3 API 数据传输结构

| 端点 | 请求体 | 响应体 |
|------|--------|--------|
| GET /api/topic | — | `{"topic": "苹果"}` |
| POST /api/guess | `{"image_b64": "data:image/png;base64,..."}` | `{"guess": "苹果", "confidence": 0.92, "model": "deepseek-v4-pro"}` |
| POST /api/feedback | `{"user_says_correct": true}` | `{"scored": true, "score": 3}` |
| GET /api/score | — | `{"score": 3}` |

---

## 3. 配置文件设计

### 3.1 `.env` 文件结构

```env
# DeepSeek API
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 可选覆盖
# DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
# DEEPSEEK_MODEL=deepseek-v4-pro
# DATABASE_URL=sqlite:///./guess.db
# LOG_LEVEL=INFO
```

### 3.2 `config.py` Settings 字段

| 字段 | 类型 | 默认值 | 来源 |
|------|------|--------|------|
| deepseek_api_key | str | 必填 | `.env` |
| deepseek_api_url | str | `https://api.deepseek.com/v1/chat/completions` | `.env`（可选） |
| deepseek_model | str | `deepseek-v4-pro` | `.env`（可选） |
| database_url | str | `sqlite:///./guess.db` | `.env`（可选） |
| log_level | str | `INFO` | `.env`（可选） |

---

## 4. 状态机时序设计

```
[DRAFT] ──── get /api/topic ────▶ [DRAFT with topic]
                                         │
                                   POST /api/guess
                                         ▼
                                    [GUESSING]  ← 等待 AI 响应（最长 5s）
                                         │
                                   safe_predict 返回
                                         ▼
                                     [RESULT]  ← 展示 AI 猜测，等待用户反馈
                                         │
                                   POST /api/feedback
                                         ▼
                                      [DONE]  ← 反馈已记录
                                         │
                                   GET /api/topic (下一轮)
                                         ▼
                                    [DRAFT]  (循环)

状态持续时间（预期）:
  DRAFT:      无限（等用户画图并提交）
  GUESSING:   0.5 – 5.0 秒（取决于 AI 响应速度）
  RESULT:     无限（等用户判断）
  DONE:       无限（等用户点下一轮）
```

**状态屏障规则**（后端状态机强制校验）:
| 操作 | 允许的状态 | 拒绝时返回 |
|------|-----------|-----------|
| start_round | DRAFT, DONE | — |
| submit_guess | DRAFT | 400 |
| receive_result | GUESSING | 400 |
| process_feedback | RESULT | 400 |
| next_round | DONE | 400 |

---

## 5. 测试策略

### 5.1 测试分层

```
测试金字塔:
  ┌─────────────┐
  │  E2E (0)    │  ← V1 不做端到端，由人工验收
  ├─────────────┤
  │  集成 (3)    │  test_api.py
  ├─────────────┤
  │  单元 (4)    │  test_state_machine.py, test_ai_contract.py, (test_word_bank.py)
  └─────────────┘
```

### 5.2 测试文件清单

| 文件 | 测试目标 | 用例数（预估） |
|------|---------|-------------|
| `tests/test_state_machine.py` | 状态流转、屏障校验、计分矩阵、包含匹配 | 12+ |
| `tests/test_ai_contract.py` | PredictionResult 校验、safe_predict 超时/降级/正常 | 8+ |
| `tests/test_api.py` | 4 个端点：正常/异常/边界 | 10+ |
| `tests/test_word_bank.py` | 词库非空、get_random_topic 返回合法值 | 3+ |

### 5.3 每模块独立测试策略

| 模块 | 如何独立测试 | Mock 对象 |
|------|------------|----------|
| state_machine.py | 纯逻辑，直接 import 测试 | 无需 Mock |
| word_bank.py | 纯数据 + 随机函数，直接 import 测试 | 无需 Mock |
| contracts.py | Pydantic 模型验证，直接 import 测试 | 无需 Mock |
| safe_predict | pytest-asyncio + MockPredictor | Mock PredictorProtocol |
| deepseek.py | Mock httpx.AsyncClient | Mock httpx 响应 |
| routes.py | FastAPI TestClient + Mock StateMachine + Mock Predictor | Mock Session + Mock Provider |
| db.py | 临时 SQLite 文件（pytest tmp_path） | 无需 Mock |
| canvas.ts | 暂不单元测试（Canvas 需 DOM 环境） | — |
| api.ts | 暂不单元测试（依赖 fetch） | — |

### 5.4 conftest.py fixtures

```python
@pytest.fixture
def game_session() -> GameSession

@pytest.fixture
def mock_predictor() -> MockPredictor  # 可控制返回结果

@pytest.fixture
async def test_db(tmp_path) -> str  # 临时数据库路径

@pytest.fixture
def test_client(mock_predictor, test_db) -> TestClient  # 完整测试 app
```

---

## 6. 项目文件详细结构

```
guess/
├── .env                            # API Key（gitignore）
├── .gitignore
├── .python-version                 # 3.13
├── pyproject.toml                  # uv 管理
│
├── doc/
│   ├── proposal.md                 # 需求文档
│   ├── high-level-design.md        # 概要设计
│   └── detailed-design.md          # 本文档
│
├── src/
│   ├── main.py                     # FastAPI app + uvicorn 启动
│   │
│   ├── core/
│   │   ├── contracts.py            # 数据结构 + 协议 + 常量
│   │   ├── config.py               # Pydantic Settings
│   │   ├── state_machine.py        # GameSession + 计分
│   │   └── word_bank.py            # 词库 + get_random_topic()
│   │
│   ├── services/
│   │   ├── ai_predictor.py         # safe_predict() 包装器
│   │   ├── db.py                   # init_db + insert_round + list_rounds
│   │   └── providers/
│   │       ├── __init__.py
│   │       └── deepseek.py         # DeepSeekProvider
│   │
│   └── api/
│       ├── __init__.py
│       ├── routes.py               # 4 个端点
│       └── deps.py                 # 依赖注入（单例）
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.ts                # 入口 + 全局状态 + 事件绑定
│       ├── canvas.ts              # DrawingCanvas 类
│       ├── api.ts                 # fetchTopic / submitGuess / sendFeedback / getScore
│       └── types.ts               # AppState 枚举 + 接口定义
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # fixtures
│   ├── test_state_machine.py
│   ├── test_ai_contract.py
│   ├── test_api.py
│   └── test_word_bank.py
│
└── scripts/
    └── ci_gate.py                 # CI 门禁
```

---

## 7. 接口约定

### 7.1 HTTP 状态码约定

| 状态码 | 场景 |
|--------|------|
| 200 | 正常响应 |
| 400 | 请求参数校验失败（图片过大、格式错误、状态屏障） |
| 422 | Pydantic 校验失败（FastAPI 自动返回） |
| 500 | 服务端未预期异常 |
| 503 | AI 服务超时/不可用（降级后仍返回 200，仅供路由层日志） |

### 7.2 API 响应示例

**GET /api/topic**
```json
{"topic": "苹果"}
```

**POST /api/guess** (成功)
```json
{
  "guess": "苹果",
  "confidence": 0.92,
  "model": "deepseek-v4-pro"
}
```

**POST /api/guess** (AI 超时，降级)
```json
{
  "guess": "timeout",
  "confidence": 0.0,
  "model": "deepseek-v4-pro"
}
```

**POST /api/feedback** (得分)
```json
{"scored": true, "score": 3}
```

**POST /api/feedback** (未得分)
```json
{"scored": false, "score": 2}
```

**GET /api/score**
```json
{"score": 3}
```

### 7.3 PredictorProtocol 约定

```python
class PredictorProtocol(Protocol):
    async def predict(self, image_bytes: bytes) -> PredictionResult: ...
    @property
    def name(self) -> str: ...
```

所有 Provider 必须：
- `predict()` 不自行处理超时（由 `safe_predict` 包装）
- 可能抛出异常（`safe_predict` 捕获并降级）
- `name` 属性返回唯一标识符

---

## 8. 性能设计

| 项目 | 设计决策 | 依据 |
|------|---------|------|
| 图片传输 | Canvas 导出为 PNG base64，前端直接 POST JSON | PNG 无损；500×400 约 10-30KB base64，远低于 2MB 上限 |
| AI 超时 | 5 秒硬超时（asyncio.wait_for） | 防止用户等待过久 |
| 并发 | SyncIO = 单用户，无并发压力 | V1 本地运行，单浏览器 |
| SQLite | 单连接，aiosqlite 异步访问 | 避免阻塞事件循环 |
| 内存 | GameSession 单例，size < 1KB | 可忽略 |
| 静态资源 | Vite 开发服务器 + HMR | 开发体验，无构建性能瓶颈 |

---

## 9. 关键流程步骤

### 9.1 完整请求-响应序列

```
阶段1: 初始化
  浏览器 → GET /api/topic
  后端 → random.choice(WORDS) → session.start_round("苹果")
  浏览器 ← {"topic": "苹果"}
  浏览器 → 渲染 "请画：苹果"

阶段2: 提交猜画
  浏览器 → canvas.exportBase64()
  浏览器 → POST /api/guess {"image_b64": "data:image/png;base64,iVBOR..."}
  后端 → 解码 base64 → size 校验
  后端 → session.submit_guess()  [状态 → GUESSING]
  后端 → safe_predict(predictor, image_bytes)
          └─ predictor.predict(image_bytes)
               └─ POST https://api.deepseek.com/v1/chat/completions
                    ← {"choices":[{"message":{"content":"苹果"}}]}
  后端 → session.receive_result("苹果")  [状态 → RESULT]
  浏览器 ← {"guess": "苹果", "confidence": 0.8, "model": "deepseek-v4-pro"}

阶段3: 用户反馈
  用户 → 点击 ✅
  浏览器 → POST /api/feedback {"user_says_correct": true}
  后端 → session.process_feedback(true)
          └─ ai_correct = ("苹果" in "苹果") = True
          └─ scored = (true and true) = True → score++
  后端 → db.insert_round("苹果", "苹果", True, "deepseek-v4-pro")
  浏览器 ← {"scored": true, "score": 3}
  用户 → 点击 [下一轮]
  浏览器 → GET /api/topic  [循环至阶段1]
```

---

## 10. 异常处理

### 10.1 后端异常矩阵

| 异常类型 | 捕获位置 | 处理方式 | HTTP 返回 |
|---------|---------|---------|----------|
| 图片 > 2MB | routes.py | 直接返回错误 | 400 `{"detail": "image exceeds 2MB limit"}` |
| 格式非 PNG | routes.py | 检查 MIME 前缀 | 400 `{"detail": "only PNG format is allowed"}` |
| base64 解码失败 | routes.py | try/except binascii.Error | 400 `{"detail": "invalid base64 encoding"}` |
| AI 超时 (5s) | safe_predict | 返回降级 PredictionResult | 200 (降级结果) |
| DeepSeek API 4xx | deepseek.py | 抛出 ProviderError → safe_predict 捕获 | 200 (降级结果) |
| DeepSeek API 5xx | deepseek.py | 抛出 ProviderError → safe_predict 捕获 | 200 (降级结果) |
| 状态屏障违规 | state_machine.py | 抛出 ValueError → routes.py 捕获 | 400 `{"detail": "invalid state transition"}` |
| DB 写入失败 | db.py | 抛出 → routes.py 返回 500 | 500 |
| 未预期异常 | main.py | 全局异常处理器 | 500 |
| .env 缺失 API Key | config.py | Pydantic ValidationError → 启动失败 | 应用无法启动 |

### 10.2 前端异常处理

| 场景 | 处理方式 |
|------|---------|
| fetch 网络错误 | catch → 显示"网络错误，请重试" |
| API 返回 4xx/5xx | 检查 `res.ok` → 显示 `res.text()` 错误信息 |
| AI 返回 guess="timeout" | 显示"AI 推断超时，请简化图画后重试" |
| AI 返回 guess="error" | 显示"AI 服务异常，请稍后重试" |
| Canvas 未初始化时点击提交 | 禁用提交按钮直到加载完成 |
| 提交为空画板 | 不阻止（用户可能画得很简单） |

---

## 11. 模块依赖图（禁止循环依赖）

```
contracts.py ─────────────────────────────────────────────┐
    │ (被所有模块 import)                                    │
    ▼                                                       │
config.py ────▶ contracts.py                                │
word_bank.py  (无依赖)                                       │
state_machine.py ────▶ contracts.py                         │
                                                             │
deepseek.py ────▶ contracts.py, config.py                   │
ai_predictor.py ────▶ contracts.py (不 import providers)     │
db.py ────▶ contracts.py                                    │
                                                             │
deps.py ────▶ state_machine.py, deepseek.py, config.py      │
routes.py ────▶ contracts.py, deps.py (间接获取所有依赖)      │
main.py ────▶ routes.py, deps.py, db.py                     │
                                                             │
types.ts (无依赖)                                             │
api.ts ────▶ types.ts                                        │
canvas.ts ────▶ (无内部依赖，仅浏览器 API)                      │
main.ts ────▶ types.ts, api.ts, canvas.ts                    │
```

**验证**: 无循环依赖。所有箭头单向。

---

## 12. 未覆盖项说明

| 项目 | 状态 |
|------|------|
| 用户认证 | V1 不需要（单用户本地运行） |
| 国际化 (i18n) | V1 仅中文 |
| CD/部署 | V1 本地运行，不涉及 |
| 日志系统 | V1 使用 Python logging 默认配置即可 |
| Canvas 单元测试 | Canvas 操作依赖浏览器 DOM，V1 通过人工验收 |
