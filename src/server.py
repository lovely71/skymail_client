from __future__ import annotations

import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from client import SkyMailApiError, SkyMailClient
from config import load_config, validate_config


CONFIG = load_config()
validate_config(CONFIG)

CLIENT = SkyMailClient(
    base_url=CONFIG.skymail_base_url,
    email=CONFIG.skymail_email,
    password=CONFIG.skymail_password,
    default_domain=CONFIG.default_domain,
    random_local_length=CONFIG.random_local_length,
    request_timeout_sec=CONFIG.request_timeout_sec,
)


def _parse_int(value: str | None, fallback: int) -> int:
    if value is None:
        return fallback
    try:
        return int(value)
    except ValueError:
        return fallback


class SkyMailHandler(BaseHTTPRequestHandler):
    server_version = "SkyMailPython/0.1"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        self._handle_request()

    def do_POST(self) -> None:  # noqa: N802
        self._handle_request()

    def _handle_request(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if self.command == "GET" and path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "service": "skymail-client-py",
                    "baseUrl": CONFIG.skymail_base_url,
                },
            )
            return

        if not self._is_authorized():
            self._send_error_json(HTTPStatus.UNAUTHORIZED, "Unauthorized")
            return

        try:
            if self.command == "GET" and path == "/domains":
                self._send_json(HTTPStatus.OK, {"ok": True, "domains": CLIENT.get_domains()})
                return

            if self.command == "POST" and path == "/inboxes/random":
                body = self._read_json_body()
                inbox = CLIENT.create_random_inbox(
                    domain=str(body.get("domain", "")),
                    local_length=body.get("localLength"),
                )
                self._send_json(HTTPStatus.OK, {"ok": True, "inbox": inbox})
                return

            messages_match = re.fullmatch(r"/inboxes/(.+)/messages", path)
            if self.command == "GET" and messages_match:
                address = unquote(messages_match.group(1))
                params = parse_qs(parsed.query)
                result = CLIENT.list_inbox_messages(
                    address,
                    limit=_parse_int(params.get("limit", [None])[0], 20),
                    mode=(params.get("mode", ["noone"])[0] or "noone"),
                )
                self._send_json(HTTPStatus.OK, {"ok": True, **result})
                return

            wait_match = re.fullmatch(r"/inboxes/(.+)/wait", path)
            if self.command == "GET" and wait_match:
                address = unquote(wait_match.group(1))
                params = parse_qs(parsed.query)
                result = CLIENT.wait_for_messages(
                    address,
                    after_id=_parse_int(params.get("afterId", [None])[0], 0),
                    timeout_ms=_parse_int(params.get("timeoutMs", [None])[0], CONFIG.default_wait_timeout_ms),
                    poll_ms=_parse_int(params.get("pollMs", [None])[0], CONFIG.default_poll_ms),
                )
                self._send_json(HTTPStatus.OK, {"ok": True, **result})
                return

            self._send_error_json(HTTPStatus.NOT_FOUND, "Not found")
        except SkyMailApiError as exc:
            self._send_error_json(
                HTTPStatus.BAD_GATEWAY,
                str(exc),
                {"code": exc.code, "status": exc.status},
            )
        except ValueError as exc:
            self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:  # noqa: BLE001
            self._send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def _read_json_body(self) -> dict:
        length = _parse_int(self.headers.get("Content-Length"), 0)
        if length <= 0:
            return {}

        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        if not raw.strip():
            return {}

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON body") from exc

        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def _is_authorized(self) -> bool:
        if not CONFIG.app_token:
            return True
        return self.headers.get("x-api-key") == CONFIG.app_token

    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_error_json(self, status: HTTPStatus, message: str, details: dict | None = None) -> None:
        self._send_json(
            status,
            {
                "ok": False,
                "error": message,
                "details": details,
            },
        )


def main() -> None:
    server = ThreadingHTTPServer((CONFIG.host, CONFIG.port), SkyMailHandler)
    print(f"SkyMail client listening on http://{CONFIG.host}:{CONFIG.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
