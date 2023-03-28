import os
import openai
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY", "")
chat_role = os.getenv("CHAT_ROLE", "You are a helpful assistant.")

app = App(token=os.getenv("SLACK_BOT_TOKEN", ""))
contexts = []


@app.message("")
def message_hello(message, say):
    global contexts

    channel_id = message["channel"]
    message_ts = say("...")["ts"]
    contexts = contexts + [{"role": "user", "content": message["text"]}]

    report = []
    token_count = 0
    for resp in openai.ChatCompletion.create(
            model='gpt-4',
            messages=[
                {"role": "system", "content": chat_role},
            ] + contexts,
            temperature=0.5,
            stream=True):

        if not "content" in resp.choices[0].delta:
            continue

        report.append(resp.choices[0].delta.content)
        result = "".join(report).strip()

        token_count += 1
        if token_count % 10 == 0:
            update_text(channel_id, message_ts, result)

    update_text(channel_id, message_ts, result)
    contexts = contexts + [{"role": "assistant", "content": result}]
    if len(contexts) >= 6:
        contexts = contexts[2:]


def update_text(channel_id, message_ts, text):
    try:
        app.client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=text
        )
    except SlackApiError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN", "")).start()
