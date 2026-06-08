"""测试词库模块。"""

from src.core.word_bank import WORDS, get_random_topic


def test_words_not_empty() -> None:
    """词库不为空。"""
    assert len(WORDS) > 0
    assert 50 <= len(WORDS) <= 100


def test_get_random_topic_returns_string() -> None:
    """get_random_topic 返回非空字符串。"""
    topic = get_random_topic()
    assert isinstance(topic, str)
    assert len(topic) > 0


def test_get_random_topic_returned_in_words() -> None:
    """get_random_topic 返回的内容来自词库。"""
    topic = get_random_topic()
    assert topic in WORDS


def test_get_random_topic_multiple_calls() -> None:
    """多次调用 get_random_topic 可以返回不同结果。"""
    results: set[str] = set()
    # 调用足够多次，使得碰巧返回同一结果的概率极低
    for _ in range(100):
        results.add(get_random_topic())
    # 80 个词，调用 100 次，应有至少 2 个不同结果
    assert len(results) >= 2
