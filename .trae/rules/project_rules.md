# 🎨 你画我猜 AI — 项目长期记忆

---

## ⚖️ 项目开发宪法（最高准则）

> 所有开发活动必须严格遵守以下 10 条规则。本宪法优先级高于任何其他文档。

### 1. Plan 门禁
必须先输出完整执行计划，经项目负责人审核回复 `✅ 按此执行` 或 `❌ 修改第X点` 后，方可写代码。未确认前禁止输出任何实现代码。

### 2. 技术栈锁定
技术栈锁定为：**后端** FastAPI + Pydantic V2，**前端** Vite + TypeScript + Canvas API，**AI层** PredictorProtocol + 多 Provider。禁止擅自引入重型替代方案或跨语言编译链。必要依赖写入 `pyproject.toml`/`package.json`，禁止在代码中硬编码第三方逻辑或推荐其他架构。

### 3. 代码规范
结构清晰、可维护、有注释、无冗余。严格遵循类型提示（TypeScript / Python Type Hints），禁止隐式类型转换或动态 eval。

### 4. 交付底线
每个模块必须交付可运行/可预览结果。后端附 API 文档或测试报告，前端附 Vite 预览说明。禁止半成品、烂尾代码或"理论上可行"的逻辑。

### 5. 调试铁律
严禁创建 `debug_*.py`/`debug_*.ts` 或临时验证脚本。后端验证仅通过 `uv run pytest --cache-clear`；前端以 Vite 热更新预览为准。所有调试信息通过结构化日志或断言捕获，禁止 `console.log`/`print` 污染生产代码。

### 6. UI/UX 标准
专业、简洁、现代，严格遵循 Web 响应式设计。AI 交互必须提供明确状态反馈（绘制区 / 推理加载态 / 结果展示区 / 用户打分区），禁止添加需求以外的装饰性动效或弹窗。

### 7. 角色边界
- **项目负责人**：定方向、提需求、审计划、验收结果、拍板变更
- **全栈开发团队（AI）**：架构设计、代码实现、接口定义、数据库模型、页面构建、单元测试与部署方案
- AI 严禁越权修改需求或契约。

### 8. CI 隔离
永远不要让 AI 在聊天框运行 `pytest`/`mypy`/`ruff`/`vite`。项目负责人在本地执行后，仅向 AI 反馈 1 行失败摘要。禁止 AI 输出完整日志或生成排查脚本。

### 9. 契约驱动
所有核心参数、数据结构、接口签名严格以 `contracts.py`/`contracts.ts` 为唯一事实来源。禁止 AI 推算、假设或补充未定义的字段。契约文件为只读仲裁依据。

### 10. 单模块单会话
每个模块必须新开会话。首条指令必须加载项目 `doc/` 目录相关文档、契约文件及任务清单 `tasks/<module>.md`。单次响应 ≤1.5k tokens，超长内容按文件分步交付，待确认后再继续。

---

## 项目概述

一个网页游戏：用户在页面 Canvas 画图区域绘制图形，通过外部 AI 大模型接口识别/猜测用户画的内容并给出答案。用户可切换不同 AI 模型，并对 AI 给出的答案进行正误判断。

## 技术栈

### 后端
- **框架**: FastAPI + Pydantic V2
- **语言**: Python 3.10+
- **包管理**: uv（pyproject.toml）

### 前端
- **构建工具**: Vite
- **语言**: TypeScript
- **画板**: 原生 HTML5 Canvas API

### AI 服务层
- **架构**: 抽象协议接口 `PredictorProtocol` + 多 Provider 实现
- **目标模型**: Google Gemini、OpenAI GPT-4o、通义千问 VL（可扩展）

### 数据持久化
- **数据库**: SQLite（Python 内置 `sqlite3`，后续可通过 SQLAlchemy 迁移到 PostgreSQL）

### 测试 / CI
- **测试框架**: pytest + pytest-asyncio + pytest-cov
- **HTTP Mock**: httpx.MockTransport（通过 conftest.py fixture 注入）
- **CI 门禁**: `scripts/ci_gate.py`（覆盖率 + lint 检查）
- **类型检查**: mypy（后端） / tsc（前端）
- **代码风格**: ruff

## 项目结构

```
guess/
├── doc/                             # 需求到开发的全部文档
├── src/
│   ├── main.py                      # FastAPI 入口，挂载路由
│   ├── core/
│   │   ├── contracts.py             # 只读契约：数据结构、枚举、阈值、接口协议
│   │   ├── config.py                # 配置管理（从 .env 读取，Pydantic Settings）
│   │   └── state_machine.py         # 回合状态机、分数/反馈逻辑
│   ├── services/
│   │   ├── ai_predictor.py          # PredictorProtocol 协议定义 & Mock 实现
│   │   ├── providers/               # openai.py, gemini.py, qwen.py
│   │   └── db.py                    # SQLite 初始化与 CRUD
│   └── api/
│       ├── routes.py                # FastAPI 路由（Orchestrator）
│       └── deps.py                  # 依赖注入（模型配置、DB 会话）
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── main.ts                  # 前端入口
│   │   ├── canvas.ts                # DrawingCanvas 类
│   │   ├── api.ts                   # 后端 API 调用封装
│   │   └── types.ts                 # 前端契约（与 contracts.py 对应）
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   ├── test_state_machine.py        # 状态流转、反馈判定、边界条件
│   ├── test_ai_contract.py          # 接口格式、超时、降级、置信度阈值
│   ├── test_api.py                  # 路由层测试（TestClient + MockTransport）
│   └── conftest.py                  # Mock AI、临时 DB、异步 fixture
├── pyproject.toml                   # uv 管理，含 pytest/mypy/ruff 配置
└── scripts/
    └── ci_gate.py                   # CI 门禁脚本
```

## 核心架构设计

### AI Provider 协议

```
class PredictorProtocol(Protocol):
    async def predict(image_bytes: bytes) -> PredictionResult
```

所有 AI Provider 实现此协议，通过 `registry` 注册。前端传 `model_name`，后端路由到对应 Provider。

### API 设计

```
POST /api/guess
Request:  { image: base64_string, model: "gemini"|"gpt4o"|"qwen" }
Response: { answer: string, confidence: float, model: string }

POST /api/feedback
Request:  { session_id: string, correct: boolean, actual_answer?: string }
Response: { success: true }

GET  /api/models
Response: { models: [{name: string, label: string, available: boolean}] }

GET  /api/history
Response: { records: [...] }
```

### 用户交互流程

1. 用户在 Canvas 上画图
2. 点击"提交猜画"按钮
3. 前端将 Canvas 导出为 base64 图片
4. POST `/api/guess` 发送图片和选中的模型
5. 后端转发给对应 AI Provider，返回识别结果
6. 前端展示 AI 的猜测答案
7. 用户点击 ✅ 正确 / ❌ 错误 给出反馈
8. 反馈记录存入 SQLite

## 关键设计决策

| 决策 | 理由 |
|------|------|
| Pydantic V2 | 多 Provider 出参格式不同，需要统一中间层建模 |
| Protocol 抽象 | 新增 Provider 只需实现接口+注册，不改路由代码 |
| Vite + TypeScript | 前端状态流转复杂（切换模型/结果展示/反馈），TS 类型安全有价值 |
| SQLite | 零配置，Python 内置，单用户场景完全够用 |
| MockTransport 测试 | 不烧 AI API 额度即可验证路由和 Provider 逻辑 |
