# 你画我猜 AI — 总体进度

## 项目信息

| 项目 | 值 |
|------|-----|
| 名称 | 你画我猜 AI |
| 版本 | V1 |
| 技术栈 | FastAPI + Pydantic V2 / Vite + TypeScript + Canvas / DeepSeek API / SQLite |
| 开发模型 | 单模块单会话，依赖链顺序交付 |
| 最后更新 | 2026-06-05 |

---

## 文档清单

| 文档 | 路径 | 状态 |
|------|------|------|
| 需求文档 | `doc/proposal.md` | ✅ 已完成 |
| 概要设计 | `doc/high-level-design.md` | ✅ 已完成 |
| 详细设计 | `doc/detailed-design.md` | ✅ 已完成 |
| 契约文件 | `src/core/contracts.py` | ✅ 已锁定 |
| 模块任务 01 | `doc/tasks/01-core-contracts.md` | ✅ 已生成 |
| 模块任务 02 | `doc/tasks/02-state-machine.md` | ✅ 已生成 |
| 模块任务 03 | `doc/tasks/03-ai-services.md` | ✅ 已生成 |
| 模块任务 04 | `doc/tasks/04-api-layer.md` | ✅ 已生成 |
| 模块任务 05 | `doc/tasks/05-frontend.md` | ✅ 已生成 |

---

## 模块进度

### 阶段 1：基础层

| 模块 | 任务文档 | Ruff | Mypy | Pytest | Cov | 状态 |
|------|---------|------|------|--------|-----|------|
| 01-core-contracts | [tasks/01-core-contracts.md](tasks/01-core-contracts.md) | ✅ | ✅ | ✅ | ✅ | 🟢 已完成 |

### 阶段 2：状态机

| 模块 | 任务文档 | Ruff | Mypy | Pytest | Cov | 状态 |
|------|---------|------|------|--------|-----|------|
| 02-state-machine | [tasks/02-state-machine.md](tasks/02-state-machine.md) | ✅ | ✅ | ✅ | ✅ | 🟢 已完成 |

### 阶段 3：AI 服务层

| 模块 | 任务文档 | Ruff | Mypy | Pytest | Mock | Cov | 状态 |
|------|---------|------|------|--------|------|-----|------|
| 03-ai-services | [tasks/03-ai-services.md](tasks/03-ai-services.md) | ✅ | ✅ | ✅ | ✅ | ✅ | 🟢 已完成 |

### 阶段 4：API 路由层

| 模块 | 任务文档 | Ruff | Mypy | Pytest | Cov | 状态 |
|------|---------|------|------|--------|-----|------|
| 04-api-layer | [tasks/04-api-layer.md](tasks/04-api-layer.md) | ✅ | ✅ | ✅ | ✅ | 🟢 已完成 |

### 阶段 5：前端

| 模块 | 任务文档 | tsc | Build | Preview | 状态 |
|------|---------|-----|-------|---------|------|
| 05-frontend | [tasks/05-frontend.md](tasks/05-frontend.md) | ✅ | ✅ | ⬜ | 🟢 已完成 |

---

## 质量门禁汇总

### 后端模块（01-04）

| 门禁 | 01-core | 02-sm | 03-ai | 04-api |
|------|---------|-------|-------|--------|
| `ruff check` 0 errors | ✅ | ✅ | ✅ | ✅ |
| `mypy --strict` 0 issues | ✅ | ✅ | ✅ | ✅ |
| `pytest` 全绿 | ✅ | ✅ | ✅ | ✅ |
| `line≥90%` | ✅ | ✅ | ✅ | ✅ |
| `branch≥85%` | ✅ | ✅ | ✅ | ✅ |
| Mock 100%（03 专属） | N/A | N/A | ✅ | N/A |
| TestClient 4 端点（04 专属） | N/A | N/A | N/A | ✅ |
| 降级 200 非 5xx（04 专属） | N/A | N/A | N/A | ✅ |

### 前端模块（05）

| 门禁 | 05-frontend |
|------|------------|
| `tsc --noEmit` 0 errors | ✅ |
| `vite build` 0 warnings | ✅ |
| 人工预览验收 | ⬜ |

### 全局门禁（所有模块完成后）

| 门禁 | 状态 |
|------|------|
| `uv run ruff check src/ tests/` 0 errors | ✅ |
| `uv run mypy src/ --strict` 0 issues | ✅ |
| `uv run pytest --cache-clear` 全绿 | ✅ (104 passed) |
| `uv run python scripts/ci_gate.py` 通过 | ✅ |

---

## 统计数据

| 指标 | 数值 |
|------|------|
| 总模块数 | 5 |
| 已完成 | 5 |
| 进行中 | 0 |
| 待开发 | 0 |
| 后端源文件 | 10 |
| 前端源文件 | 4 |
| 测试文件 | 4 |

---
## 更新日志

| 日期 | 更新内容 |
|------|---------|
| 2026-06-05 | Phase 1-5 全部完成，进入全局门禁 + 联调阶段 |
| 2026-05-29 | 初始化进度文档，生成 5 份模块任务文档 |

---

> ⚠️ 仅人工或监工 Agent 可修改本文档的 CheckList 状态。
> 子 Agent 仅可汇报"门禁日志摘要"，禁止直接修改总进度的 CheckList。
