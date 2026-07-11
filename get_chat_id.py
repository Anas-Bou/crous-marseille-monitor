import requests

from config import TELEGRAM_BOT_TOKEN


def get_chat_id():
    response = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
        timeout=20,
    )

    if response.status_code != 200:
        raise SystemExit(
            f"Telegram error {response.status_code}: verify TELEGRAM_BOT_TOKEN."
        )

    updates = response.json().get("result", [])
    for update in reversed(updates):
        message = update.get("message") or update.get("channel_post")
        if message and message.get("chat", {}).get("id") is not None:
            print(f"TELEGRAM_CHAT_ID={message['chat']['id']}")
            return

    raise SystemExit(
        "No message found. Send /start to the bot on Telegram, then run again."
    )


if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env first.")
    get_chat_id()
