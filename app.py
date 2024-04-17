import os
import openai
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY", "")
default_system_prompt = os.getenv("SYSTEM_PROMPT") or os.getenv(
    "CHAT_ROLE") or "You are a helpful assistant."
system_prompt = default_system_prompt

app = App(token=os.getenv("SLACK_BOT_TOKEN", ""))

try:
    response = app.client.auth_test()
    bot_user_id = response["user_id"]
except Exception as e:
    print("Error fetching bot user ID:", e)
    bot_user_id = None


@app.message("")
def message_hello(message, say, client):
    channel_id = message["channel"]
    thread_ts = message['thread_ts'] if 'thread_ts' in message else message['ts']

    if f"<@{bot_user_id}>" in message["text"]:
        update_role(message["text"].replace(
            f"<@{bot_user_id}>", "").strip(), thread_ts, say)
        return

    message_ts = say(text="...", thread_ts=thread_ts)["ts"]
    context_messages = fetch_thread_context(
        client, channel_id, thread_ts)

    report = []
    token_count = 0
    for resp in openai.chat.completions.create(
            model='gpt-4-turbo-2024-04-09',
            messages=[
                {"role": "system", "content": system_prompt},
            ] + context_messages,
            temperature=0.5,
            stream=True):

        if resp.choices[0].delta.content is None or len(resp.choices[0].delta.content) == 0:
            continue

        report.append(resp.choices[0].delta.content)
        result = "".join(report).strip()

        token_count += 1
        if token_count % 5 == 0:
            update_text(channel_id, message_ts, result)

    update_text(channel_id, message_ts, result)


def update_role(text, thread_ts, say):
    new_role = text
    if new_role == "":
        new_role = default_system_prompt
    global system_prompt
    system_prompt = new_role
    say(text="Updated the system prompt.", thread_ts=thread_ts)


def fetch_thread_context(client, channel_id, thread_ts):
    try:
        response = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts
        )
        # Get the last 7 messages excluding the latest one
        messages = response['messages'][-8:-1]
        context = []
        for msg in messages:
            if msg['user'] == bot_user_id:
                role = "assistant"
            else:
                role = "user"
            context.append({"role": role, "content": msg['text']})
        return context
    except SlackApiError as e:
        print(f"Error fetching context: {e}")
        return []


def update_text(channel_id, message_ts, text):
    try:
        app.client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=text
        )
    except SlackApiError as e:
        print(f"Error updating message: {e}")


if __name__ == "__main__":
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN", "")).start()
