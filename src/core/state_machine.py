"""回合状态机、分数/反馈逻辑。"""

from src.core.contracts import GameState


def is_correct_guess(topic: str, guess: str) -> bool:
    """包含匹配：不区分大小写，判断 topic 是否为 guess 的子串。"""
    return topic.lower() in guess.lower()


def calculate_score(user_says_correct: bool, ai_correct: bool) -> int:
    """计分纯函数：仅当用户判定正确且 AI 实际正确时得分 1，否则 0。"""
    return 1 if (user_says_correct and ai_correct) else 0


class GameSession:
    """管理单次游戏会话的回合状态流转与计分。"""

    def __init__(self) -> None:
        self._state: GameState = GameState.DRAFT
        self._current_topic: str = ""
        self._ai_guess: str | None = None
        self._score: int = 0

    # --------------- 只读属性 ---------------

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def score(self) -> int:
        return self._score

    @property
    def current_topic(self) -> str:
        return self._current_topic

    @property
    def ai_guess(self) -> str | None:
        return self._ai_guess

    # --------------- 状态流转方法 ---------------

    def start_round(self, topic: str) -> None:
        """设置本轮题目，可从 DRAFT 或 DONE 状态调用。"""
        if self._state not in (GameState.DRAFT, GameState.DONE):
            raise ValueError(
                f"start_round 仅允许在 DRAFT 或 DONE 状态调用，当前状态: {self._state.value}"
            )
        self._state = GameState.DRAFT
        self._current_topic = topic
        self._ai_guess = None

    def submit_guess(self) -> None:
        """提交猜画请求，状态从 DRAFT 迁移到 GUESSING。"""
        if self._state != GameState.DRAFT:
            raise ValueError(
                f"submit_guess 仅允许在 DRAFT 状态调用，当前状态: {self._state.value}"
            )
        self._state = GameState.GUESSING

    def receive_result(self, guess: str) -> None:
        """接收 AI 猜测结果，状态从 GUESSING 迁移到 RESULT。"""
        if self._state != GameState.GUESSING:
            raise ValueError(
                f"receive_result 仅允许在 GUESSING 状态调用，当前状态: {self._state.value}"
            )
        self._ai_guess = guess
        self._state = GameState.RESULT

    def process_feedback(self, user_says_correct: bool) -> tuple[bool, int]:
        """处理用户反馈，状态从 RESULT 迁移到 DONE。

        返回 (scored: 本轮是否得分, new_score: 最新累计分数)。
        """
        if self._state != GameState.RESULT:
            raise ValueError(
                f"process_feedback 仅允许在 RESULT 状态调用，当前状态: {self._state.value}"
            )
        ai_correct = is_correct_guess(self._current_topic, self._ai_guess or "")
        scored = calculate_score(user_says_correct, ai_correct) == 1
        if scored:
            self._score += 1
        self._state = GameState.DONE
        return (scored, self._score)

    def next_round(self) -> None:
        """进入下一轮，状态从 DONE 迁移到 DRAFT，清空本轮数据。"""
        if self._state != GameState.DONE:
            raise ValueError(
                f"next_round 仅允许在 DONE 状态调用，当前状态: {self._state.value}"
            )
        self._state = GameState.DRAFT
        self._ai_guess = None
        self._current_topic = ""
