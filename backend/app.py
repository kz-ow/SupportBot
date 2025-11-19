from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import settings

# Slackアプリを初期化
app = App(token=settings.SLACK_BOT_TOKEN)

# メンションイベントをキャッチしてオウム返し
@app.event("app_mention")
def echo_message(event, say):
    say(event["text"])

# ソケットモードでアプリを起動
if __name__ == "__main__":
    SocketModeHandler(app, settings.SLACK_APP_TOKEN).start()