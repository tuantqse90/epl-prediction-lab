"""Register (or deregister) the Telegram webhook with Telegram's Bot API.

Idempotent. Run once on deploy; re-run if the webhook URL or secret changes.

Env:
    TELEGRAM_BOT_TOKEN       — required
    TELEGRAM_WEBHOOK_URL     — required, e.g. https://predictor.nullshift.sh/api/telegram/webhook
    TELEGRAM_WEBHOOK_SECRET  — optional but recommended; forwarded as X-Telegram-Bot-Api-Secret-Token

Usage:
    python scripts/telegram_setup_webhook.py           # set / refresh
    python scripts/telegram_setup_webhook.py --delete  # detach
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


def _post(path: str, token: str, data: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{path}"
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--delete", action="store_true")
    args = p.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("[webhook] missing TELEGRAM_BOT_TOKEN")
        sys.exit(1)

    if args.delete:
        print(_post("deleteWebhook", token, {}))
        return

    url = os.environ.get("TELEGRAM_WEBHOOK_URL")
    if not url:
        print("[webhook] missing TELEGRAM_WEBHOOK_URL")
        sys.exit(1)

    payload: dict = {
        "url": url,
        "allowed_updates": json.dumps(["message", "edited_message", "callback_query"]),
        "drop_pending_updates": "true",
    }
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if secret:
        payload["secret_token"] = secret

    resp = _post("setWebhook", token, payload)
    print(resp)

    # Verify + print diagnostic info
    info = _post("getWebhookInfo", token, {})
    print("getWebhookInfo:", info)


if __name__ == "__main__":
    main()
