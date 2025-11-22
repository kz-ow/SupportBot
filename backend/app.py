from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import settings

# Slackアプリを初期化
app = App(token=settings.SLACK_BOT_TOKEN)


# 環境変数で切り替えフラグを取得
USE_VERTEX_AI = settings.USE_VERTEX_AI


if USE_VERTEX_AI:
    # === Vertex AI モード ===
    import vertexai
    from vertexai.generative_models import GenerativeModel
    
    # GCPの認証は自動(Google Cloud SDK)またはサービスアカウントで行われる
    vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
    
    # モデルの初期化
    flash_model = GenerativeModel(str(settings.GEMINI_FLASH_MODEL_NAME))
    pro_model = GenerativeModel(str(settings.GEMINI_PRO_MODEL_NAME))

    print("🚀 Vertex AI モードで起動しました")

else:
    # === AI Studio モード (個人・手軽な試用向け) ===
    import google.generativeai as genai
    
    # Gemini APIの初期化
    genai.configure(api_key=settings.GEMINI_API_KEY)

    print("=== 利用可能なモデル一覧 ===")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            # モデル名を表示 (例: models/gemini-1.5-pro)
            print(m.name.replace("models/", ""))

    # 各モデルの初期化
    flash_model = genai.GenerativeModel(str(settings.GEMINI_FLASH_MODEL_NAME))
    pro_model = genai.GenerativeModel(str(settings.GEMINI_PRO_MODEL_NAME))

    print("✨ Gemini API (AI Studio) モードで起動しました")

    
# Slackメンションされた際の処理
@app.event("app_mention")
def echo_message(event, say):

    # スレッドのタイムスタンプを取得（スレッド内返信用）
    thread_ts = event.get("thread_ts") or event.get("ts")
    
    # ユーザーメッセージを取得
    user_text = event["text"]

    # コマンド "/why" や "深く考えて" などのキーワードがあれば Pro を使う
    if "/why" in user_text or "深く" in user_text:
        say("🤔 過去の経緯を含めて深く分析しています...少々お待ちください。", thread_ts=thread_ts)
        response = pro_model.generate_content(user_text)

    else:
        response = flash_model.generate_content(user_text)

    # 結果をスレッドで返信
    say(response.text, thread_ts=thread_ts)
    

# ソケットモードでアプリを起動
if __name__ == "__main__":
    SocketModeHandler(app, settings.SLACK_APP_TOKEN).start()