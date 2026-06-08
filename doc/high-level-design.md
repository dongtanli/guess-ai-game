# 你画我猜 AI — 概要设计文档 V1

## 1. 设计概述

本系统采用前后端分离架构：前端负责画板交互与 UI 状态管理，后端负责出题、AI 调用、计分与持久化。两端通过 RESTful API 通信。

---

## 2. 模块总览

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Canvas   │  │  API     │  │  UI State        │  │
│  │ 画板模块  │  │ Client   │  │ 主入口 + 状态管理  │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │  HTTP (REST)
                       ▼
┌─────────────────────────────────────────────────────┐
│                    Backend                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  API Layer  │  │   Services   │  │   Core     │ │
│  │  routes.py  │  │ ai_predictor │  │ contracts  │ │
│  │  deps.py    │  │     db       │  │ config     │ │
│  │             │  │  providers/  │  │ word_bank  │ │
│  │             │  │              │  │ state_mach │ │
│  └─────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 3. 后端模块

### 3.1 Core 层（`src/core/`）

| 文件 | 职责 | 依赖 |
|------|------|------|
| `contracts.py` | 数据结构（`PredictionResult`、`GuessRequest`）、协议接口（`PredictorProtocol`）、常量（超时、阈值） | 无外部依赖 |
| `config.py` | 从 `.env` 加载配置（DEEPSEEK_API_KEY、数据库路径等），使用 Pydantic Settings | `contracts.py` |
| `state_machine.py` | 回合状态管理：当前题目、当前分数、判断 AI 是否正确（包含匹配） | `contracts.py`、`word_bank.py` |
| `word_bank.py` | 中文名词词库常量列表 `WORDS: list[str]`（约 50-100 个，初始化后只读） | 无外部依赖 |

#### 3.1.1 回合状态机（`state_machine.py`）

```
状态流转:
  DRAWING ──[提交猜画]──▶ WAITING_AI ──[AI返回]──▶ RESULT ──[用户反馈]──▶ DONE
     ▲                                                                       │
     └────────────────────[点击下一轮]────────────────────────────────────────┘

各状态说明:
  DRAWING    — 画板可用，用户正在画图
  WAITING_AI — 已提交，等待 AI 响应（前端显示加载动画）
  RESULT     — AI 结果已展示，等待用户点击 ✅/❌
  DONE       — 反馈已记录，等待用户点击"下一轮"
```

#### 3.1.2 包含匹配规则（Q1 确认）

```
判定函数: def is_correct_guess(topic: str, guess: str) -> bool
规则:     topic in guess  (不区分大小写)
示例:     topic="苹果", guess="这是一个红苹果" → True
          topic="苹果", guess="apple" → False
          topic="苹果", guess="苹果" → True
```

### 3.2 Services 层（`src/services/`）

| 文件 | 职责 | 依赖 |
|------|------|------|
| `ai_predictor.py` | `safe_predict()` 包装器（超时 + 降级 + 阈值校验）；V1 不包含 Mock，Mock 仅用于测试 | `contracts.py`、`providers/` |
| `providers/deepseek.py` | DeepSeek API 调用实现 `PredictorProtocol`：base64 → DeepSeek Vision API → `PredictionResult` | `contracts.py`、`config.py` |
| `db.py` | SQLite 初始化（建表）、回合记录插入与查询 | `contracts.py`、`config.py` |

#### 3.2.1 DeepSeek Provider 调用流程

```
输入: image_bytes (PNG)
  ↓
构造 multipart 或 JSON 请求到 https://api.deepseek.com
  ├─ Authorization: Bearer {DEEPSEEK_API_KEY}
  ├─ model: deepseek-v4-pro
  └─ prompt: "请用中文猜测这幅简笔画画的是什么，只返回物品名称，不要多余解释。"
  ↓
解析响应 → PredictionResult(guess=..., confidence=..., model_name="deepseek-v4-pro")
```

### 3.3 API 层（`src/api/`）

| 文件 | 职责 | 依赖 |
|------|------|------|
| `routes.py` | 定义 4 个 API 端点，编排调用顺序 | `contracts.py`、`state_machine.py`、`services/` |
| `deps.py` | 依赖注入：单例 StateMachine、DB 会话、Predictor 实例 | `state_machine.py`、`db.py`、`ai_predictor.py` |

#### 3.3.1 端点设计

```
GET  /api/topic
  → 从 word_bank 随机抽取题目
  → 存入状态机（覆盖上轮 topic）
  → 返回 { topic: "苹果" }

POST /api/guess
  → 请求体: { image_b64: "data:image/png;base64,..." }
  → 校验图片大小 < 2MB，格式为 PNG
  → 调用 safe_predict(predictor, image_bytes)
  → 将 AI 结果存入状态机
  → 返回 { guess: "苹果", confidence: 0.92, model: "deepseek-v4-pro" }

POST /api/feedback
  → 请求体: { user_says_correct: true | false }
  → 状态机判定: is_correct_guess(current_topic, ai_guess)
  → 计分: 仅当 user_says_correct=true 且 is_correct_guess=true → +1
  → 写入 DB: (topic, guess, is_correct, model_name, created_at)
  → 返回 { score: 3, correct: true, ai_guess: "苹果" }

GET  /api/score
  → 返回 { score: 3 }
```

#### 3.3.2 计分判定矩阵

```
 is_correct_guess = (topic in ai_guess)

 user_says_correct │ is_correct_guess │ 得分
───────────────────┼──────────────────┼──────
       true        │      true        │  +1
       true        │      false       │  +0
       false       │      true        │  +0
       false       │      false       │  +0
```

### 3.4 入口（`src/main.py`）

```
创建 FastAPI app
→ 挂载 routes.router
→ 启动时注册 DeepSeek Provider 到 ModelRegistry
→ 启动时初始化 SQLite 数据库
```

---

## 4. 前端模块

### 4.1 模块职责

| 文件 | 职责 |
|------|------|
| `types.ts` | 前端类型定义：`GuessResponse`、`TopicResponse`、`FeedbackRequest`、`AppState` 枚举 |
| `canvas.ts` | `DrawingCanvas` 类：画笔绘制、橡皮擦、清空、导出 base64 |
| `api.ts` | 封装 4 个后端 API 调用（`fetchTopic`、`submitGuess`、`sendFeedback`、`getScore`） |
| `main.ts` | 应用入口：初始化 Canvas、绑定 UI 事件、管理全局状态、驱动页面渲染 |

### 4.2 前端状态

```typescript
enum AppState {
  DRAWING,       // 等待用户画图
  GUESSING,      // 已提交，等待 AI 返回
  RESULT,        // AI 结果已展示，等待反馈
  FEEDBACK_DONE, // 反馈完成，等待下一轮
}
```

### 4.3 UI 事件流

```
页面加载
  → main.ts 调用 GET /api/topic → 显示题目
  → 初始化 DrawingCanvas
  → 状态 = DRAWING

[提交猜画] 点击
  → canvas.exportBase64()
  → 状态 = GUESSING，显示"推断中…"
  → POST /api/guess → 等待响应
  → 状态 = RESULT，显示 AI 猜测结果

[✅]/[❌] 点击
  → POST /api/feedback
  → 更新分数显示
  → 状态 = FEEDBACK_DONE
  → 禁用 ✅/❌，启用 [下一轮]

[下一轮] 点击
  → canvas.clear()
  → GET /api/topic → 更新题目
  → 状态 = DRAWING
```

---

## 5. 数据库设计

### 5.1 表结构

```sql
CREATE TABLE IF NOT EXISTS rounds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic       TEXT    NOT NULL,   -- 题目
    guess       TEXT    NOT NULL,   -- AI 猜测结果
    is_correct  INTEGER NOT NULL,   -- 是否正确 (0/1)
    model_name  TEXT    NOT NULL,   -- 模型名称
    created_at  TEXT    NOT NULL    -- ISO 8601 时间戳
);
```

### 5.2 索引

```sql
CREATE INDEX IF NOT EXISTS idx_rounds_created_at ON rounds(created_at);
```

---

## 6. 模块关系图

```
浏览器
  │
  ├─ index.html ─▶ main.ts
  │                  ├─ canvas.ts ─▶ HTMLCanvasElement
  │                  ├─ api.ts ────▶ HTTP fetch()
  │                  └─ types.ts
  │
  ▼ HTTP
FastAPI (main.py)
  │
  ├─ routes.py ─────────────▶ state_machine.py ──▶ word_bank.py
  │    │                           │
  │    ├─ GET  /api/topic ─────────┘
  │    ├─ POST /api/guess ─▶ ai_predictor.py ─▶ providers/deepseek.py ─▶ DeepSeek API
  │    ├─ POST /api/feedback ▶ state_machine.py ─▶ db.py ─▶ SQLite
  │    └─ GET  /api/score ──▶ state_machine.py
  │
  ├─ deps.py (注入 StateMachine, DB, Predictor)
  └─ config.py ─▶ .env
```

---

## 7. 文件变更清单（相对于当前代码库）

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/core/contracts.py` | 修改 | `ALLOWED_IMAGE_FORMATS` 改为仅 PNG；新增 `DEEPSEEK_MODEL` 常量 |
| `src/core/word_bank.py` | 新建 | 50-100 个中文名词常量列表 |
| `src/core/state_machine.py` | 重写 | 实现状态流转、包含匹配、计分逻辑 |
| `src/core/config.py` | 重写 | Pydantic Settings 加载 DEEPSEEK_API_KEY 等 |
| `src/services/providers/deepseek.py` | 新建 | DeepSeek API Provider 实现 |
| `src/services/ai_predictor.py` | 修改 | 已有 `safe_predict`，补充 Provider 注册逻辑 |
| `src/services/db.py` | 重写 | SQLite 初始化 + rounds 表 CRUD |
| `src/api/routes.py` | 重写 | 4 个端点实现 |
| `src/api/deps.py` | 重写 | 依赖注入 fixture |
| `src/main.py` | 重写 | FastAPI app 创建与启动逻辑 |
| `frontend/src/canvas.ts` | 重写 | 画笔/橡皮擦/清空/导出 base64 |
| `frontend/src/api.ts` | 重写 | 4 个 API 调用封装 |
| `frontend/src/types.ts` | 重写 | 前端类型与 AppState 枚举 |
| `frontend/src/main.ts` | 重写 | 入口 + 状态管理 + 事件绑定 |
| `frontend/index.html` | 不需改 | 已有基本结构 |
