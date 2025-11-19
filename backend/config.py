from pydantic_settings import BaseSettings

# AWS Secrets Managerからの設定を取得するための設定
class Settings(BaseSettings):
    # Slack Bot設定
    SLACK_BOT_TOKEN: str
    SLACK_APP_TOKEN: str

    # Gemini API設定
    GEMINI_API_KEY: str
    GEMINI_REGION: str


settings = Settings()

