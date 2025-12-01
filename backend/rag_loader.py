import os
import chromadb
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.readers.github import (
    GithubRepositoryReader,
    GithubClient,
    GitHubRepositoryIssuesReader,
    GitHubIssuesClient
)

from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

from config import settings

def initialize_llama_index_settings():
    """
    Llama Indexの設定を初期化 (Google GenAI SDK版)
    ProモデルとFlashモデルの両方を初期化し返す
    """
    
    # 共通の埋め込みモデル名 (新SDKでは "models/" プレフィックス不要)
    embed_model_name = "text-embedding-004"

    pro_model = None
    flash_model = None
    embed_model = None

    if settings.USE_VERTEX_AI:
        # === Vertex AIモード ===
        print("🔧 Llama Index: Vertex AIモード (via Google GenAI SDK) を初期化中...")

        # Vertex AI 接続設定
        # GOOGLE_APPLICATION_CREDENTIALS は SDK が環境変数から自動的に読み込みます
        vertex_config = {
            "project": settings.GCP_PROJECT_ID,
            "location": settings.GCP_LOCATION,
        }

        # Embeddingモデル
        embed_model = GoogleGenAIEmbedding(
            model_name=embed_model_name,
            vertexai_config=vertex_config
        )

        # Proモデル (推論・高精度用)
        pro_model = GoogleGenAI(
            model=settings.GEMINI_PRO_MODEL_NAME,
            vertexai_config=vertex_config,
            max_tokens=4096,
            temperature=0.1
        )
        
        # Flashモデル (高速・大量処理用)
        flash_model = GoogleGenAI(
            model=settings.GEMINI_FLASH_MODEL_NAME,
            vertexai_config=vertex_config,
            max_tokens=4096,
            temperature=0.1
        )

        print("✅ Llama Index: Vertex AIモードの設定が完了しました。")
    
    else:
        # === AI Studioモード ===
        print("🔧 Llama Index: AI Studioモード (via Google GenAI SDK) を初期化中...")
        
        # API Keyを設定
        os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

        # Embeddingモデル
        embed_model = GoogleGenAIEmbedding(
            model_name=embed_model_name
        )

        # Proモデル
        pro_model = GoogleGenAI(
            model=settings.GEMINI_PRO_MODEL_NAME,
            max_tokens=4096,
            temperature=0.1
        )

        # Flashモデル
        flash_model = GoogleGenAI(
            model=settings.GEMINI_FLASH_MODEL_NAME,
            max_tokens=4096,
            temperature=0.1
        )

        print("✅ Llama Index: AI Studioモードの設定が完了しました。")

    # --- グローバル設定 ---
    # デフォルトは Flash モデルなどを設定しておくと安全です
    Settings.embed_model = embed_model
    Settings.llm = flash_model

    # モデル群を辞書で返す
    models = {"pro": pro_model, "flash": flash_model}

    return models, embed_model
    

def get_index():
    """
    ChromaDBからインデックスをロード，なければGithubリポジトリからデータを取得してインデックスを作成し保存
    """

    # Llama Indexの設定を初期化し、モデルを取得
    models, embed_model = initialize_llama_index_settings()

    # ChromaDBのクライアントの設定
    db_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
    chroma_collection = db_client.get_or_create_collection(name=settings.CHROMA_COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    if chroma_collection.count() > 0:
        print("📂 既存のインデックスをChromaDBからロード中...")
        # ロード時にも embed_model を明示的に渡すことで埋め込みの一貫性を保つ
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context,
            embed_model=embed_model
        )
        print("✅ インデックスのロードが完了しました。")
        return index, models

    else:
        print("🚀 既存のインデックスが見つからないため，Githubからデータを取得して新規作成します...")

        # --- 1. ソースコードの取得 ---
        print("📥 [1/2] ソースコードを取得中...")
        github_client = GithubClient(
            github_token=settings.GITHUB_TOKEN,
            verbose=True
        )

        repo_reader = GithubRepositoryReader(
            github_client=github_client,
            owner=settings.GITHUB_REPO_OWNER,
            repo=settings.GITHUB_REPO_NAME,
            filter_file_extensions=(
                [".py", ".js", ".ts", ".md", ".html", ".css", ".json", ".yaml", ".yml", ".sql", ".go", ".java", ".txt"],
                GithubRepositoryReader.FilterType.INCLUDE
            ),
            verbose=True,
            concurrent_requests=5
        )

        code_documents = repo_reader.load_data(branch=settings.GITHUB_BRANCH_NAME)
        print(f"   👉 {len(code_documents)} ファイルのコードを取得しました")

        # --- 2. Issue / PR の取得 ---
        print("📥 [2/2] IssueとPull Requestの履歴を取得中...")
        # Issue用クライアント
        issues_client = GitHubIssuesClient(
            github_token=settings.GITHUB_TOKEN,
            verbose=True
        )
        
        # Issueリーダー
        issues_reader = GitHubRepositoryIssuesReader(
            github_client=issues_client,
            owner=settings.GITHUB_REPO_OWNER,
            repo=settings.GITHUB_REPO_NAME,
            verbose=True
        )

        # データをロード
        issue_documents = issues_reader.load_data(
            state=GitHubRepositoryIssuesReader.IssueState.ALL
        )
        print(f"   👉 {len(issue_documents)} 件のIssue/PRデータを取得しました")

        # --- 3. データの結合とインデックス作成 ---
        print("🧠 データを結合してインデックスを作成中...")
        all_documents = code_documents + issue_documents

        index = VectorStoreIndex.from_documents(
            all_documents,
            storage_context=storage_context,
            embed_model=embed_model  # 明示的に指定
        )

        print("✅ インデックスの作成と保存が完了しました。")
        return index, models