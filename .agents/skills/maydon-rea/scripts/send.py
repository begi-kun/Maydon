import json
import os
import sys
import urllib.error
import urllib.request


def main():
    token = os.getenv("MAYDON_REPORT_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    chat = os.getenv("MAYDON_REPORT_CHAT_ID", "")
    if not token or not chat.isascii() or not chat.isdigit() or int(chat) <= 0:
        sys.exit("Bot tokeni va shaxsiy MAYDON_REPORT_CHAT_ID kerak.")
    message = sys.stdin.read().strip()
    if not message or len(message.encode("utf-16-le")) // 2 > 4096:
        sys.exit("Hisobot bo‘sh yoki Telegram limitidan uzun.")
    body = json.dumps({"chat_id": chat, "text": message}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
        if result.get("ok"):
            print(result["result"]["message_id"])
            return
    except urllib.error.HTTPError as error:
        sys.exit(f"Telegram HTTP {error.code}")
    except (OSError, ValueError, KeyError):
        sys.exit("Yetkazilish holati noma’lum.")
    sys.exit("Telegram yuborishni tasdiqlamadi.")


if __name__ == "__main__":
    main()
