from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import settings
from rag_loader import get_index

# Slackアプリを初期化
app = App(token=settings.SLACK_BOT_TOKEN)

# indexの初期化
index, models = get_index()

# モデルの定義
flash_model_engine = index.as_query_engine(similarity_top_k=5, llm=models["flash"])
pro_model_engine = index.as_query_engine(similarity_top_k=5, llm=models["pro"])
    
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
        response = pro_model_engine.query(user_text)
    else:
        response = flash_model_engine.query(user_text)

    # 結果をスレッドで返信
    say(response.text, thread_ts=thread_ts)
    

# ソケットモードでアプリを起動
if __name__ == "__main__":
    # Slackアプリをソケットモードで起動
    SocketModeHandler(app, settings.SLACK_APP_TOKEN).start()
    


    