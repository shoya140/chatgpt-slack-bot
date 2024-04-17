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
def message_hello(message, say, client):
    bot_user_id = client.auth_test()["user_id"]
    if f"<@{bot_user_id}>" in message["text"]:
        new_role = message["text"].replace(f"<@{bot_user_id}>", "").strip()
        if new_role == "":
            new_role = os.getenv("CHAT_ROLE", "You are a helpful assistant.")
        update_role(new_role, say)
    else:
        respond(message, say)


def update_role(new_role, say):
    global contexts
    global chat_role

    contexts = []
    chat_role = new_role
    say("Updated the role and contexts.")


def respond(message, say):
    global contexts

    channel_id = message["channel"]
    message_ts = say("...")["ts"]
    contexts = contexts + [{"role": "user", "content": message["text"]}]

    report = []
    token_count = 0
    for resp in openai.chat.completions.create(
            model='gpt-4-turbo-2024-04-09',
            messages=[
                {"role": "system", "content": chat_role},
            ] + contexts,
            temperature=0.5,
            stream=True):

        if resp.choices[0].delta.content is None or len(resp.choices[0].delta.content) == 0:
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
