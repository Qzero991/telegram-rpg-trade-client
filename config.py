from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    engine_url: str
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    telegram_api_id: int
    telegram_api_hash: str
    telegram_session_name: str
    telegram_bot_token: str
    trade_group_id: int
    my_id: int | None = None
    items_info_group_id: str
    equipment_last_id: int
    resource_last_id: int
    app_mode: str

    model_config = SettingsConfigDict(
        env_file=".env" if Path(".env").exists() else None,
        case_sensitive=False
    )

settings = Settings()
