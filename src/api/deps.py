"""依赖注入（模型配置、DB 会话）。"""

from src.core.config import settings
from src.core.state_machine import GameSession
from src.services.providers.qwen import QwenProvider

_session: GameSession | None = None
_predictor: QwenProvider | None = None


def get_session() -> GameSession:
    """模块级懒加载单例 GameSession。"""
    global _session
    if _session is None:
        _session = GameSession()
    return _session


def get_predictor() -> QwenProvider:
    """从 config 读取 api_key/api_url/model 构造 QwenProvider 单例。"""
    global _predictor
    if _predictor is None:
        _predictor = QwenProvider(
            api_key=settings.dashscope_api_key,
            api_url=settings.dashscope_api_url,
            model=settings.dashscope_model,
        )
    return _predictor


def get_db_path() -> str:
    """从 config 读取 database_url。"""
    return settings.database_url
