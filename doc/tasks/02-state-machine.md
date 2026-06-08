# 02-state-machine — 回合状态机

## 概述

实现 GameSession 类：管理回合状态流转、包含匹配判定、计分逻辑。纯逻辑模块，无 I/O 依赖。

## 涉及文件

| 文件 | 说明 |
|------|------|
| `src/core/state_machine.py` | GameSession + is_correct_guess + calculate_score |

---

## 任务清单

### T2.1 GameState 引用

- [ ] `from src.core.contracts import GameState` — 同源引用

### T2.2 is_correct_guess — 包含匹配

- [ ] `def is_correct_guess(topic: str, guess: str) -> bool`
- [ ] 规则：`topic.lower() in guess.lower()` — 不区分大小写的包含匹配

### T2.3 calculate_score — 计分

- [ ] `def calculate_score(user_says_correct: bool, ai_correct: bool) -> int`
- [ ] 仅当两者均为 True 时返回 1，否则返回 0
- [ ] 纯函数，无副作用

### T2.4 GameSession 类

- [ ] 属性：`_state: GameState`, `_current_topic: str`, `_ai_guess: str | None`, `_score: int`
- [ ] `__init__()`：初始 DRAFT，score=0
- [ ] `start_round(topic: str)`：设置 topic，状态不变（可从 DRAFT 或 DONE 调用）
- [ ] `submit_guess()`：DRAFT → GUESSING，否则抛 ValueError
- [ ] `receive_result(guess: str)`：GUESSING → RESULT，存储 ai_guess
- [ ] `process_feedback(user_says_correct: bool) -> tuple[bool, int]`：RESULT → DONE，返回 (scored, new_score)
- [ ] `next_round()`：DONE → DRAFT，清空 _ai_guess 和 _current_topic
- [ ] 只读 property：`state`, `score`, `current_topic`, `ai_guess`

### T2.5 状态屏障校验

- [ ] submit_guess 仅在 DRAFT 时允许
- [ ] receive_result 仅在 GUESSING 时允许
- [ ] process_feedback 仅在 RESULT 时允许
- [ ] next_round 仅在 DONE 时允许
- [ ] 违规抛出 `ValueError`

---

## 验收标准

| 检查项 | 命令 | 阈值 |
|--------|------|------|
| Ruff | `uv run ruff check src/core/` | 0 errors |
| Mypy | `uv run mypy src/core/ --strict` | 0 issues |
| Pytest | `uv run pytest tests/test_state_machine.py --cov=src/core/state_machine --cov-fail-under=90` | 全绿 |
| 覆盖率 | line≥90%, branch≥85% | — |

### 测试用例最小覆盖

- [ ] 合法状态流转：DRAFT → GUESSING → RESULT → DONE → DRAFT
- [ ] 非法状态流转：每种屏障违规至少 1 个用例
- [ ] 包含匹配：匹配/不匹配/空字符串/大小写
- [ ] 计分矩阵：4 种组合
- [ ] 多轮累计分数

---

## 依赖

- `src/core/contracts.py`（GameState 枚举）
- 无其他模块依赖
