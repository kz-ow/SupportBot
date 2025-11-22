from pydantic_settings import BaseSettings

# AWS Secrets Managerからの設定を取得するための設定
class Settings(BaseSettings):
    # Slack Bot設定
    SLACK_BOT_TOKEN: str
    SLACK_APP_TOKEN: str

    # Gemini API設定
    GEMINI_API_KEY: str
    GEMINI_REGION: str

    # Vertex AI使用フラグ
    USE_VERTEX_AI: bool = False

    # GCP設定
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = ""

    # Geminiモデル名設定
    GEMINI_FLASH_MODEL_NAME: str = "gemini-1.5-flash"
    GEMINI_PRO_MODEL_NAME: str = "gemini-3.0-pro"


settings = Settings()

