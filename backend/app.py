import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from llama_index.core import Document
from config import settings
from rag_loader import get_index

# Slackアプリを初期化
app = App(token=settings.SLACK_BOT_TOKEN)

# indexの初期化
index, models = get_index()

# 1. RAG用のクエリエンジンをモデルごとに作成
flash_model_engine = index.as_query_engine(similarity_top_k=5, llm=models["flash"])
pro_model_engine = index.as_query_engine(similarity_top_k=5, llm=models["pro"])

# 2. ドキュメントとして保存する際の要約用モデル
summary_model_engine = models["flash"]

# === ユーティリティ関数 ===
def clean_text(text):
    # Slackのメンション表記を削除
    return re.sub(r'<@[^>]+>', '', text).strip()
    
# Slackメンションされた際の返信処理
@app.event("app_mention")
def echo_message(event, say):

    # スレッドのタイムスタンプを取得（スレッド内返信用）
    thread_ts = event.get("thread_ts") or event.get("ts")
    
    # ユーザーメッセージを取得
    user_text = clean_text(event["text"])

    # コマンド "/why" や "深く考えて" などのキーワードがあれば Pro を使う
    if "/why" in user_text or "深く" in user_text:
        say("🤔 過去の経緯を含めて深く分析しています...少々お待ちください。", thread_ts=thread_ts)
        response = pro_model_engine.query(user_text)
    else:
        response = flash_model_engine.query(user_text)

    # 結果をスレッドで返信
    say(str(response), thread_ts=thread_ts)

# Reactionが追加された際の処理（例: メモリアクションで要約保存）
@app.event("reaction_added")
def handle_reaction(event, say):
   if event["reaction"] != "memo":
       return 
   
   channel = event["item"]["channel"]
   ts = event["item"]["ts"]

   try:
        # スレッドの会話履歴を全部取得
        history = app.client.conversations_replies(channel=channel, ts=ts)
        messages = history.get["messages"]

        # 会話のログを整形
        conversation_log = ""
        for msg in messages:
            user = msg.get("user", "unknown")
            text = clean_text(msg.get("text", ""))
            conversation_log += f"User({user}): {text}\n"

        # 通知：保存を開始します
        app.client.chat_postMessage(
            channel=channel,
            text="💾 会話内容を要約して知識ベースに保存しています...少々お待ちください。",
            thread_ts=ts
        )

        # ドキュメントとして保存するために要約を生成
        prompt = f"""
        以下の開発チャットのログから、将来役に立つ「技術的な知見」を抽出して要約してください。
        
        フォーマット:
        【タイトル】（簡潔に）
        【問題の概要】
        【解決策・結論】
        【関連技術】

        === チャットログ ===
        {conversation_log}
        """
        summary = summary_model_engine.complete(prompt).text

        # LlamaIndex (Vector DB) に保存
        new_doc = Document(
            text=summary,
            metadata={
                "source": "slack_thread",
                "channel_id": channel,
                "thread_ts": ts,
                "type": "knowledge_base"
            }
        )
        index.insert(new_doc)

        # 完了通知
        app.client.chat_postMessage(
            channel=channel, 
            thread_ts=ts, 
            text=f"✅ 保存しました！次回以降の会話ではこの内容も回答に使われます。\n```{summary}```"
        )
   except Exception as e:
       print(f"❌ エラーが発生しました: {e}")


# ソケットモードでアプリを起動
if __name__ == "__main__":
    # Slackアプリをソケットモードで起動
    SocketModeHandler(app, settings.SLACK_APP_TOKEN).start()

