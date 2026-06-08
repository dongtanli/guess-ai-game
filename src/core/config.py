"""配置管理（从 .env 读取，Pydantic Settings）。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置，优先级：环境变量 > .env > 默认值。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    dashscope_api_key: str
    dashscope_api_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_model: str = "qwen3-vl-flash"
    database_url: str = "guess.db"
    log_level: str = "INFO"


settings = Settings()  # type: ignore[call-arg]  # pydantic-settings reads from env, mypy can't see it
