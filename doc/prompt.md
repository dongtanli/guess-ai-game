# 你画我猜 AI — 开发团队总提示词

---

## 一、项目背景

"你画我猜 AI" 是一个网页游戏：系统随机出题 → 用户 Canvas 画图 → AI（DeepSeek）猜测 → 用户判断 → 计分 → 下一轮。

| 属性 | 值 |
|------|-----|
| 版本 | V1 |
| 后端 | FastAPI + Pydantic V2 + Python 3.13 |
| 前端 | Vite + TypeScript + Canvas API |
| AI 服务 | DeepSeek API（`deepseek-v4-pro`），OpenAI 兼容 JSON 格式 |
| 数据库 | SQLite（`aiosqlite`） |
| 测试 | pytest + pytest-asyncio + pytest-cov |
| 类型检查 | mypy --strict / tsc --noEmit |
| 代码风格 | Ruff |

---

## 二、团队角色

| 角色 | 实体 | 职责 |
|------|------|------|
| **项目负责人** | 人工 | 定方向、审计划、验收结果、修改 progress.md |
| **主 Agent** | AI | 架构决策、任务分发、审查 CI 结果、合并 PR |
| **子 Agent** | AI（每模块新会话） | 独立功能开发、自测、提交 PR |

---

## 三、前置强制加载清单

每个子 Agent 新会话的首条响应之前，必须逐项确认已读取以下文件：

- [ ] `src/core/contracts.py` — 所有常量、枚举、数据结构的唯一来源
- [ ] `doc/tasks/<module-name>.md` — 当前模块的任务列表与验收标准
- [ ] `doc/detailed-design.md` — 当前模块的详细设计章节
- [ ] `doc/proposal.md` — 需求文档（首会话读取一次即可）

未确认完整读取，**禁止输出任何代码**。

---

## 四、新会话首条指令内容

每个子 Agent 新会话的首条消息必须包含**进度同步**：

```
模块名称: <module-name>
当前阶段: <任务编号: T1.1 / T2.3 / ...>
分支: feat/<module-name>
已完成: <已完成的 checklist 项>
待实现: <当前要做的 checklist 项>
测试覆盖: <已通过的测试文件>
门禁状态: <ruff/mypy/pytest/cov 通过情况>
```

---

## 五、契约驱动铁律

1. `src/core/contracts.py` 为执行实施时是的**唯一仲裁文件**，只读，禁止修改
2. 所有核心参数、数据结构、接口签名严格以 contracts.py 为准
3. 禁止推算、假设或补充 contracts.py 未定义的字段
4. 若发现 contracts.py 与实际需求冲突，**暂停并上报项目负责人**，由人工决策

---

## 六、分支策略

| 规则 | 说明 |
|------|------|
| 功能分支命名 | `feat/<module-name>`（如 `feat/01-core-contracts`） |
| 禁止操作 | 禁止直接 push 至 `main` 分支 |
| 合并方式 | 所有代码通过 Pull Request 合并 |
| Git 为唯一真相 | `git log` + `uv run pytest --cache-clear` 输出才有法律效力 |
| 冲突处理 | 主 Agent 审查 CI 结果、解决冲突、合并至 main |

---

## 七、测试驱动开发（TDD）

严格遵循 **测试 → 反馈 → 实现** 顺序：

1. 阅读 contracts.py + detailed-design.md，理解接口契约
2. 编写测试用例（pytest），确保测试失败
3. 实现模块代码
4. 运行 `uv run pytest tests/test_<module>.py --cache-clear`，确保全绿
5. 补齐覆盖率不足的分支

> 所有功能以 `pytest` 断言结果为最终判定标准。任何"调试分歧"一律以 `pytest --cache-clear` 结果为准。

---

## 八、模块质量门禁

### 后端模块（01-04）

| 门禁 | 命令 | 通过标准 |
|------|------|---------|
| 代码风格 | `uv run ruff check src/ tests/` | 0 errors |
| 类型检查 | `uv run mypy src/ --strict` | 0 issues |
| 单元测试 | `uv run pytest tests/test_<module>.py --cov=src/<module> --cov-fail-under=90 --cache-clear` | 全绿 |
| 覆盖率 | line≥90%, branch≥85% | — |
| Mock 100%（03 专属） | 不直连真实 API/DB | 全部通过 Mock |
| TestClient（04 专属） | 4 端点全绿 + 降级返回 200 | — |

### 前端模块（05）

| 门禁 | 命令 | 通过标准 |
|------|------|---------|
| 类型检查 | `cd frontend && npx tsc --noEmit` | 0 errors |
| 构建 | `cd frontend && npx vite build` | 0 warnings |
| 预览验收 | `cd frontend && npx vite preview` | 人工确认 |

---

## 九、调试铁律

| 禁止 | 替代做法 |
|------|---------|
| ❌ 创建 `debug_*.py` / `debug_*.ts` | ✅ 在模块内使用结构化日志 |
| ❌ 覆盖原类的 `DebugXXX` | ✅ 通过 Mock 注入测试行为 |
| ❌ `print()` / `console.log()` 调试 | ✅ `pytest` 断言 或 `logging` |
| ❌ 临时验证脚本 | ✅ 写入正规测试文件 |
| ❌ 以"推测"修复 bug | ✅ 先用 `git log` 定位，再修复，最后 `pytest --cache-clear` 验证 |

修改代码后必须运行 `uv run pytest --cache-clear`。若测试与脚本结果不一致，立即检查 `sys.path` 与 `__pycache__`。

---

## 十、CI 隔离铁律

| 规则 | 说明 |
|------|------|
| AI 不运行 CI | 严禁在对话中生成或运行 `pytest`/`mypy`/`ruff`/`vite` 命令 |
| 仅接收 1 行摘要 | 项目负责人本地执行后，仅向 AI 反馈 1 行失败摘要 |
| 格式 | `FAILED test_xxx - AssertionError: expected X, got Y` |
| AI 禁止 | 输出完整日志、生成排查脚本、推测 CI 结果 |

---

## 十一、模块交付验收

1. 子 Agent 完成开发 → 所有自动化门禁通过
2. 提交 PR 至 `feat/<module-name>` 分支
3. 项目负责人审查代码 + 运行 `uv run pytest --cache-clear`
4. 主 Agent 合并至 `main`
5. 项目负责人更新 `doc/tasks/progress.md` 中的 CheckList 状态

---

## 十二、Plan 审核流程

1. 子 Agent 收到任务 → 先输出实现计划（不写代码）
2. 计划格式：要修改的文件列表 + 每个文件的变更概述 + 接口签名变化
3. 项目负责人回复 `✅ 按此执行` 或 `❌ 修改第X点`
4. 确认后子 Agent 方可写代码

---

## 十三、全局门禁（所有模块完成后）

| 门禁 | 命令 |
|------|------|
| 全量 Ruff | `uv run ruff check src/ tests/` |
| 全量 Mypy | `uv run mypy src/ --strict` |
| 全量 Pytest | `uv run pytest --cache-clear` |
| CI 脚本 | `uv run python scripts/ci_gate.py` |

---

## 十四、文件速查表

| 用途 | 路径 |
|------|------|
| 需求文档 | `doc/proposal.md` |
| 概要设计 | `doc/high-level-design.md` |
| 详细设计 | `doc/detailed-design.md` |
| 只读契约 | `src/core/contracts.py` |
| 总进度 | `doc/tasks/progress.md` |
| 任务 01 | `doc/tasks/01-core-contracts.md` |
| 任务 02 | `doc/tasks/02-state-machine.md` |
| 任务 03 | `doc/tasks/03-ai-services.md` |
| 任务 04 | `doc/tasks/04-api-layer.md` |
| 任务 05 | `doc/tasks/05-frontend.md` |
| 项目宪法 | `.trae/rules/project_rules.md` |
| 后端配置 | `pyproject.toml` |
| 前端配置 | `frontend/package.json` |

---

## 十五、执行顺序

```
01-core-contracts ──▶ 02-state-machine ──▶ 03-ai-services ──▶ 04-api-layer
                                                                      │
                                                    05-frontend ◀─────┘（并行开发，Mock API）
```

每阶段完成后，项目负责人更新 `progress.md` 状态并开启下一阶段。
