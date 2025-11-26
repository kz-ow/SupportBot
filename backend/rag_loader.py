import os
import chromadb
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
# 追加: Issue/PR用のリーダーとクライアントをインポート
from llama_index.readers.github import (
    GithubRepositoryReader,
    GithubClient,
    GitHubRepositoryIssuesReader,
    GitHubIssuesClient
)
from google.oauth2 import service_account 

from config import settings

pro_model = None
flash_model = None

def initialize_llama_index_settings():
    """Llama Indexの設定を初期化"""

    pro_model = None
    flash_model = None
    embed_model = None

    if settings.USE_VERTEX_AI:
        # === Vertex AIモード ===
        from llama_index.llms.vertex import Vertex
        from llama_index.embeddings.vertex import VertexTextEmbedding

        print("🔧 Llama Index: Vertex AIモードの設定を初期化中...")

        json_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        credentials = None
        if json_path and os.path.exists(json_path):
            credentials = service_account.Credentials.from_service_account_file(json_path)

        embed_model = VertexTextEmbedding(
            model_name="text-embedding-004",
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
            credentials=credentials
        )

        pro_model = Vertex(
            model=settings.GEMINI_PRO_MODEL_NAME,
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
            credentials=credentials,
            max_tokens=4096,
            temperature=0.1,
            context_window=1000000 
        )
        
        flash_model = Vertex(
            model=settings.GEMINI_FLASH_MODEL_NAME,
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
            credentials=credentials,
            max_tokens=4096,
            temperature=0.1,
            context_window=1000000 
        )

        print("✅ Llama Index: Vertex AIモードの設定が完了しました。")
    
    else:
        # === AI Studioモード ===
        from llama_index.llms.gemini import Gemini
        from llama_index.embeddings.gemini import GeminiEmbedding

        print("🔧 Llama Index: Gemini APIモードの設定を初期化中...")
        
        os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

        embed_model = GeminiEmbedding(
            model_name="models/text-embedding-004"
        )

        pro_model = Gemini(
            model=settings.GEMINI_PRO_MODEL_NAME,
            max_tokens=4096,
            temperature=0.1,
            context_window=1000000
        )

        flash_model = Gemini(
            model=settings.GEMINI_FLASH_MODEL_NAME,
            max_tokens=4096,
            temperature=0.1,
            context_window=1000000
        )

        print("✅ Llama Index: Gemini APIモードの設定が完了しました。")

    # --- グローバル設定 ---
    Settings.embed_model = embed_model
    Settings.llm = flash_model

    # modelsとembedに分けて返す
    models = {"pro": pro_model, "flash": flash_model}


    # 両方のモデルインスタンスを返す
    return models, embed_model
    

def get_index():
    """
    ChromaDBからインデックスをロード，なければGithubリポジトリからデータを取得してインデックスを作成し保存
    """

    # Llama Indexの設定を初期化
    models, embed_model = initialize_llama_index_settings()

    # ChromaDBのクライアントの設定
    db_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
    chroma_collection = db_client.get_or_create_collection(name=settings.CHROMA_COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    if chroma_collection.count() > 0:
        print("📂 既存のインデックスをChromaDBからロード中...")
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
        
        # Issueリーダー (PRもIssueとして扱われます)
        issues_reader = GitHubRepositoryIssuesReader(
            github_client=issues_client,
            owner=settings.GITHUB_REPO_OWNER,
            repo=settings.GITHUB_REPO_NAME,
            verbose=True
        )

        # データをロード (State.ALL で Open/Closed 両方取得)
        # ※データ量が多い場合は state=GitHubRepositoryIssuesReader.IssueState.OPEN に絞ることも可能
        issue_documents = issues_reader.load_data(
            state=GitHubRepositoryIssuesReader.IssueState.ALL
        )
        print(f"   👉 {len(issue_documents)} 件のIssue/PRデータを取得しました")

        # --- 3. データの結合とインデックス作成 ---
        print("🧠 データを結合してインデックスを作成中...")
        all_documents = code_documents + issue_documents

        index = VectorStoreIndex.from_documents(
            all_documents,
            storage_context=storage_context
        )

        print("✅ インデックスの作成と保存が完了しました。")
        return index, models