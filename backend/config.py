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
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = "global"

    # Geminiモデル名設定
    GEMINI_FLASH_MODEL_NAME: str = "gemini-1.5-flash"
    GEMINI_PRO_MODEL_NAME: str = "gemini-3.0-pro"

    # === GitHub RAG設定 (追加) ===
    GITHUB_TOKEN: str
    GITHUB_REPO_OWNER: str
    GITHUB_REPO_NAME: str
    GITHUB_BRANCH_NAME: str = "main"
    
    # Vector DBの保存先
    CHROMA_DB_PATH: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "repo_data"


settings = Settings()

