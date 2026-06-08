"""测试状态流转、反馈判定、边界条件。"""

import pytest

from src.core.contracts import GameState
from src.core.state_machine import (
    GameSession,
    calculate_score,
    is_correct_guess,
)

# ================= is_correct_guess 测试 =================

class TestIsCorrectGuess:
    """包含匹配函数单元测试。"""

    def test_exact_match(self) -> None:
        assert is_correct_guess("苹果", "苹果") is True

    def test_contains_at_start(self) -> None:
        assert is_correct_guess("苹果", "苹果很甜") is True

    def test_contains_in_middle(self) -> None:
        assert is_correct_guess("苹果", "这是一个红苹果对吧") is True

    def test_no_match(self) -> None:
        assert is_correct_guess("苹果", "香蕉") is False

    def test_partial_overlap_not_match(self) -> None:
        """部分字符串重叠但不包含 topic，不算匹配。"""
        assert is_correct_guess("苹果", "果树") is False

    def test_case_insensitive_lower(self) -> None:
        assert is_correct_guess("APPLE", "apple pie") is True

    def test_case_insensitive_upper(self) -> None:
        assert is_correct_guess("apple", "APPLE PIE") is True

    def test_mixed_case(self) -> None:
        assert is_correct_guess("ApPlE", "aPpLe is good") is True

    def test_empty_guess(self) -> None:
        """空字符串 guess 不可能包含任何 topic。"""
        assert is_correct_guess("苹果", "") is False

    def test_empty_topic(self) -> None:
        """空 topic 是任意字符串的子串。"""
        assert is_correct_guess("", "anything") is True

    def test_both_empty(self) -> None:
        assert is_correct_guess("", "") is True

    def test_chinese_topic_chinese_guess(self) -> None:
        assert is_correct_guess("太阳", "我猜是太阳吧") is True

    def test_chinese_topic_no_match(self) -> None:
        assert is_correct_guess("太阳", "这是月亮") is False


# ================= calculate_score 测试 =================

class TestCalculateScore:
    """计分矩阵单元测试。"""

    def test_both_true(self) -> None:
        assert calculate_score(True, True) == 1

    def test_user_correct_ai_wrong(self) -> None:
        assert calculate_score(True, False) == 0

    def test_user_wrong_ai_correct(self) -> None:
        assert calculate_score(False, True) == 0

    def test_both_false(self) -> None:
        assert calculate_score(False, False) == 0


# ================= GameSession 合法状态流转测试 =================

class TestGameSessionHappyPath:
    """完整 DRAFT → GUESSING → RESULT → DONE → DRAFT 流转。"""

    def test_full_lifecycle(self) -> None:
        session = GameSession()

        # 初始状态
        assert session.state == GameState.DRAFT
        assert session.score == 0
        assert session.current_topic == ""
        assert session.ai_guess is None

        # DRAFT: start_round 设置题目
        session.start_round("苹果")
        assert session.state == GameState.DRAFT
        assert session.current_topic == "苹果"
        assert session.ai_guess is None

        # DRAFT → GUESSING: submit_guess
        session.submit_guess()
        assert session.state == GameState.GUESSING

        # GUESSING → RESULT: receive_result
        session.receive_result("一个红苹果")
        assert session.state == GameState.RESULT
        assert session.ai_guess == "一个红苹果"

        # RESULT → DONE: process_feedback (用户说正确，AI 猜中包含"苹果")
        scored, new_score = session.process_feedback(True)
        assert scored is True
        assert new_score == 1
        assert session.state == GameState.DONE
        assert session.score == 1

        # DONE → DRAFT: next_round
        session.next_round()
        assert session.state == GameState.DRAFT
        assert session.current_topic == ""
        assert session.ai_guess is None
        assert session.score == 1  # 分数保留

    def test_two_rounds_cumulative_score(self) -> None:
        """两轮游戏验证累计分数。"""
        session = GameSession()

        # 第一轮：得分
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("苹果")
        scored1, score1 = session.process_feedback(True)
        assert scored1 is True
        assert score1 == 1

        # 进入下一轮
        session.next_round()

        # 第二轮：不得分（用户说错）
        session.start_round("香蕉")
        session.submit_guess()
        session.receive_result("香蕉")
        scored2, score2 = session.process_feedback(False)
        assert scored2 is False
        assert score2 == 1  # 分数不变

    def test_three_rounds_accumulate(self) -> None:
        """三轮全得分，累计 3 分。"""
        session = GameSession()

        for i in range(3):
            session.start_round(f"题目{i}")
            session.submit_guess()
            session.receive_result(f"题目{i}")
            scored, score = session.process_feedback(True)
            assert scored is True
            assert score == i + 1
            session.next_round()

        assert session.score == 3

    def test_start_round_from_done(self) -> None:
        """start_round 可从 DONE 状态直接调用。"""
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("苹果")
        session.process_feedback(True)
        # 当前状态 DONE

        session.start_round("香蕉")
        assert session.state == GameState.DRAFT  # 重设为 DRAFT
        assert session.current_topic == "香蕉"
        assert session.ai_guess is None


# ================= GameSession 非法状态流转测试 =================

class TestGameSessionStateBarriers:
    """状态屏障校验：违规操作抛出 ValueError。"""

    # --- submit_guess 屏障 ---

    def test_submit_guess_from_draft_ok(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()  # 不应抛异常

    def test_submit_guess_from_guessing_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        with pytest.raises(ValueError, match="submit_guess"):
            session.submit_guess()

    def test_submit_guess_from_result_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("苹果")
        with pytest.raises(ValueError, match="submit_guess"):
            session.submit_guess()

    def test_submit_guess_from_done_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("苹果")
        session.process_feedback(True)
        with pytest.raises(ValueError, match="submit_guess"):
            session.submit_guess()

    def test_submit_guess_without_start_round_succeeds(self) -> None:
        """未设置 topic 直接 submit，状态仍是 DRAFT，不应抛异常。"""
        session = GameSession()
        session.submit_guess()  # DRAFT → GUESSING，合法

    # --- receive_result 屏障 ---

    def test_receive_result_from_draft_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        with pytest.raises(ValueError, match="receive_result"):
            session.receive_result("苹果")

    def test_receive_result_from_result_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("苹果")
        with pytest.raises(ValueError, match="receive_result"):
            session.receive_result("苹果")

    def test_receive_result_from_done_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("苹果")
        session.process_feedback(True)
        with pytest.raises(ValueError, match="receive_result"):
            session.receive_result("苹果")

    # --- process_feedback 屏障 ---

    def test_process_feedback_from_draft_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        with pytest.raises(ValueError, match="process_feedback"):
            session.process_feedback(True)

    def test_process_feedback_from_guessing_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        with pytest.raises(ValueError, match="process_feedback"):
            session.process_feedback(True)

    def test_process_feedback_from_done_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("苹果")
        session.process_feedback(True)
        with pytest.raises(ValueError, match="process_feedback"):
            session.process_feedback(True)

    # --- next_round 屏障 ---

    def test_next_round_from_draft_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        with pytest.raises(ValueError, match="next_round"):
            session.next_round()

    def test_next_round_from_guessing_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        with pytest.raises(ValueError, match="next_round"):
            session.next_round()

    def test_next_round_from_result_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("苹果")
        with pytest.raises(ValueError, match="next_round"):
            session.next_round()

    # --- start_round 屏障 ---

    def test_start_round_from_guessing_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        with pytest.raises(ValueError, match="start_round"):
            session.start_round("香蕉")

    def test_start_round_from_result_raises(self) -> None:
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("苹果")
        with pytest.raises(ValueError, match="start_round"):
            session.start_round("香蕉")


# ================= GameSession 计分逻辑集成测试 =================

class TestGameSessionScoringIntegration:
    """计分与包含匹配的集成场景。"""

    def test_user_correct_ai_contains(self) -> None:
        """用户说对 + AI 结果包含 topic → 得分。"""
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("一个红苹果")
        scored, score = session.process_feedback(True)
        assert scored is True
        assert score == 1

    def test_user_correct_ai_missed(self) -> None:
        """用户说对 + AI 结果不包含 topic → 不得分。"""
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("一个香蕉")
        scored, score = session.process_feedback(True)
        assert scored is False
        assert score == 0

    def test_user_incorrect_ai_contains(self) -> None:
        """用户说错 + AI 结果包含 topic → 不得分。"""
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("一个红苹果")
        scored, score = session.process_feedback(False)
        assert scored is False
        assert score == 0

    def test_user_incorrect_ai_missed(self) -> None:
        """用户说错 + AI 结果不包含 topic → 不得分。"""
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("一个香蕉")
        scored, score = session.process_feedback(False)
        assert scored is False
        assert score == 0

    def test_case_insensitive_scoring(self) -> None:
        """AI 返回大写 TOPIC → 包含匹配应不区分大小写，得分。"""
        session = GameSession()
        session.start_round("apple")
        session.submit_guess()
        session.receive_result("AN APPLE PIE")
        scored, score = session.process_feedback(True)
        assert scored is True
        assert score == 1


# ================= GameSession 属性测试 =================

class TestGameSessionProperties:
    """只读属性正确性测试。"""

    def test_initial_properties(self) -> None:
        session = GameSession()
        assert session.state == GameState.DRAFT
        assert session.score == 0
        assert session.current_topic == ""
        assert session.ai_guess is None

    def test_properties_after_start_round(self) -> None:
        session = GameSession()
        session.start_round("太阳")
        assert session.current_topic == "太阳"
        assert session.ai_guess is None

    def test_properties_after_receive_result(self) -> None:
        session = GameSession()
        session.start_round("太阳")
        session.submit_guess()
        session.receive_result("太阳公公")
        assert session.ai_guess == "太阳公公"

    def test_properties_after_next_round(self) -> None:
        session = GameSession()
        session.start_round("太阳")
        session.submit_guess()
        session.receive_result("太阳")
        session.process_feedback(True)
        session.next_round()
        assert session.current_topic == ""
        assert session.ai_guess is None
        assert session.score == 1


# ================= 边界条件测试 =================

class TestEdgeCases:
    """边界条件与防御性测试。"""

    def test_ai_guess_none_in_feedback(self) -> None:
        """极端情况：receive_result 未调用但 process_feedback 仍被调用，
        内部 getattr 防护：_ai_guess 为 None 时用空字符串兜底。"""
        # 此场景在正常流程中不会出现（process_feedback 要求 RESULT 状态，
        # 而 receive_result 会设置 _ai_guess），但防御性编码下不应崩溃。
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        # 模拟：直接修改内部状态进入 RESULT 但 _ai_guess 保持 None
        session._state = GameState.RESULT  # 绕过屏障用于测试
        scored, score = session.process_feedback(True)
        # ai_guess 为 None → is_correct_guess("苹果", "") → False → 不得分
        assert scored is False

    def test_repeated_next_round_after_done_to_draft(self) -> None:
        """next_round 后进入 DRAFT，再次 next_round 应报错。"""
        session = GameSession()
        session.start_round("苹果")
        session.submit_guess()
        session.receive_result("苹果")
        session.process_feedback(True)
        session.next_round()
        assert session.state == GameState.DRAFT
        with pytest.raises(ValueError, match="next_round"):
            session.next_round()
