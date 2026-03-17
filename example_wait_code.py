from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from client import SkyMailClient  # noqa: E402
from config import load_config, validate_config  # noqa: E402


CODE_PATTERNS = (
    re.compile(r"\b(\d{4,8})\b"),
    re.compile(r"\b([A-Z0-9]{6,8})\b"),
)


def extract_code(message: dict) -> str | None:
    chunks = [
        str(message.get("subject") or ""),
        str(message.get("text") or ""),
        str(message.get("html") or ""),
    ]
    content = "\n".join(chunks)

    for pattern in CODE_PATTERNS:
        match = pattern.search(content)
        if match:
            return match.group(1)
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a random SkyMail inbox, optionally self-send a test mail, and wait for a message."
    )
    parser.add_argument("--domain", default="", help="Preferred domain, e.g. example.com")
    parser.add_argument("--timeout-ms", type=int, default=30000, help="Wait timeout in milliseconds")
    parser.add_argument("--poll-ms", type=int, default=3000, help="Polling interval in milliseconds")
    parser.add_argument("--self-test", action="store_true", help="Send a test message from the logged-in account")
    parser.add_argument("--subject", default="", help="Custom subject for self-test mail")
    parser.add_argument("--local-length", type=int, default=10, help="Random local-part length")
    return parser.parse_args()


def main() -> None:
    config = load_config()
    validate_config(config)
    args = parse_args()

    client = SkyMailClient(
        base_url=config.skymail_base_url,
        email=config.skymail_email,
        password=config.skymail_password,
        default_domain=config.default_domain,
        random_local_length=config.random_local_length,
        request_timeout_sec=config.request_timeout_sec,
    )

    inbox = client.create_random_inbox(
        domain=args.domain or config.default_domain,
        local_length=args.local_length,
    )

    before = client.list_inbox_messages(inbox["address"], limit=5)
    after_id = 0
    if before["messages"]:
        after_id = max(int(item.get("emailId", 0) or 0) for item in before["messages"])

    sent = None
    if args.self_test:
        user = client.get_user_info()
        subject = args.subject or f"Python self test {int(time.time() * 1000)}"
        text = "Your verification code is 123456"
        sent = client.send_email(
            account_id=int(user["accountId"]),
            receive_emails=[inbox["address"]],
            subject=subject,
            text=text,
            content=f"<div>{text}</div>",
        )

    result = client.wait_for_messages(
        inbox["address"],
        after_id=after_id,
        timeout_ms=args.timeout_ms,
        poll_ms=args.poll_ms,
    )

    first_message = result["messages"][0] if result["messages"] else None
    payload = {
        "inbox": inbox,
        "selfTestSent": bool(args.self_test),
        "sendResult": sent,
        "messageCount": len(result["messages"]),
        "firstMessage": {
            "emailId": first_message.get("emailId"),
            "from": first_message.get("from"),
            "subject": first_message.get("subject"),
            "text": first_message.get("text"),
            "createdAt": first_message.get("createdAt"),
            "code": extract_code(first_message),
        }
        if first_message
        else None,
    }

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
