from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    engine_url: str
    deepseek_api_key: str
    deepseek_base_url: str
    telegram_api_id: int
    telegram_api_hash: str
    telegram_session_name: str
    trade_group_id: int
    items_info_group_id: str
    equipment_last_id: int
    resource_last_id: int

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
