from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    admin_telegram_id: int = Field(..., alias="ADMIN_TELEGRAM_ID")
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-3.6-flash", alias="GEMINI_MODEL")
    database_url: str = Field(
        "sqlite+aiosqlite:///./data/celebrity_management.db",
        alias="DATABASE_URL"
    )
    customer_support_email: str = Field(
        "christianclement463@gmail.com",
        alias="CUSTOMER_SUPPORT_EMAIL"
    )
    timezone: str = Field("America/New_York", alias="TIMEZONE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
