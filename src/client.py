from __future__ import annotations

import json
import random
import secrets
import string
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
}


def _normalize_domain(value: str) -> str:
    return str(value or "").strip().lstrip("@").lower()


def _is_usable_domain(value: str) -> bool:
    domain = _normalize_domain(value)
    if not domain or domain.startswith("-") or "." not in domain:
        return False
    return all(32 < ord(ch) < 127 for ch in domain)


def _detect_challenge(content_type: str, body: str, headers: dict[str, str]) -> bool:
    cf_mitigated = headers.get("cf-mitigated", "").lower()
    if cf_mitigated == "challenge":
        return True

    content_type = (content_type or "").lower()
    sample = body[:2000].lower()
    if "text/html" not in content_type:
        return False

    markers = ("just a moment", "attention required", "cf-challenge", "challenge-platform", "cloudflare")
    return any(marker in sample for marker in markers)


@dataclass
class RawResponse:
    status: int
    headers: dict[str, str]
    text: str
    payload: Any
    challenge: bool


class SkyMailApiError(RuntimeError):
    def __init__(self, message: str, *, code: Any = None, status: int | None = None, payload: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.payload = payload


class SkyMailClient:
    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        password: str,
        default_domain: str = "",
        random_local_length: int = 10,
        request_timeout_sec: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.default_domain = _normalize_domain(default_domain)
        self.random_local_length = random_local_length
        self.request_timeout_sec = request_timeout_sec
        self.token: str | None = None

    def _raw_request(
        self,
        path: str,
        *,
        method: str = "GET",
        query: dict[str, Any] | None = None,
        body: Any = None,
        headers: dict[str, str] | None = None,
        auth: bool = False,
    ) -> RawResponse:
        if auth and not self.token:
            self.login()

        pairs: list[tuple[str, str]] = []
        for key, value in (query or {}).items():
            if value in (None, ""):
                continue
            pairs.append((key, str(value)))

        url = f"{self.base_url}{path}"
        if pairs:
            url = f"{url}?{urllib.parse.urlencode(pairs)}"

        request_headers = dict(DEFAULT_HEADERS)
        if headers:
            request_headers.update(headers)
        if auth and self.token:
            request_headers["Authorization"] = self.token

        data = None
        if body is not None:
            request_headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")

        request = urllib.request.Request(url, data=data, headers=request_headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout_sec) as response:
                status = response.status
                response_headers = {key.lower(): value for key, value in response.headers.items()}
                text = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            status = exc.code
            response_headers = {key.lower(): value for key, value in exc.headers.items()}
            text = exc.read().decode("utf-8", errors="replace")

        content_type = response_headers.get("content-type", "")
        challenge = _detect_challenge(content_type, text, response_headers)
        if challenge:
            raise SkyMailApiError(
                "Cloudflare challenge detected while calling SkyMail",
                code="CF_CHALLENGE",
                status=status,
                payload={"path": path, "method": method},
            )

        payload = None
        if text.strip():
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise SkyMailApiError(
                    f"Expected JSON response from SkyMail, got: {content_type or 'unknown'}",
                    status=status,
                    payload={"body": text[:500], "error": str(exc)},
                ) from exc

        if isinstance(payload, dict) and payload.get("cloudflare_error"):
            raise SkyMailApiError(
                payload.get("detail", "Cloudflare blocked the request"),
                code=payload.get("error_code"),
                status=status,
                payload=payload,
            )

        return RawResponse(
            status=status,
            headers=response_headers,
            text=text,
            payload=payload,
            challenge=challenge,
        )

    def login(self, force: bool = False) -> str:
        if self.token and not force:
            return self.token

        response = self._raw_request(
            "/api/login",
            method="POST",
            body={"email": self.email, "password": self.password},
        )

        payload = response.payload or {}
        token = payload.get("data", {}).get("token")
        if response.status != 200 or payload.get("code") != 200 or not token:
            raise SkyMailApiError(
                payload.get("message", "Login failed"),
                code=payload.get("code"),
                status=response.status,
                payload=payload,
            )

        self.token = token
        return token

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        query: dict[str, Any] | None = None,
        body: Any = None,
        auth: bool = False,
        retry_on_auth_error: bool = True,
    ) -> Any:
        response = self._raw_request(path, method=method, query=query, body=body, auth=auth)
        payload = response.payload or {}

        if auth and retry_on_auth_error and payload.get("code") == 401:
            self.token = None
            self.login(force=True)
            return self.request(
                path,
                method=method,
                query=query,
                body=body,
                auth=auth,
                retry_on_auth_error=False,
            )

        if response.status != 200 or payload.get("code") != 200:
            raise SkyMailApiError(
                payload.get("message", f"Request failed: {path}"),
                code=payload.get("code"),
                status=response.status,
                payload=payload,
            )

        return payload.get("data")

    def get_website_config(self) -> dict[str, Any]:
        return self.request("/api/setting/websiteConfig")

    def get_private_settings(self) -> dict[str, Any]:
        return self.request("/api/setting/query", auth=True)

    def get_user_info(self) -> dict[str, Any]:
        return self.request("/api/my/loginUserInfo", auth=True)

    def get_domains(self) -> list[str]:
        config = self.get_website_config()
        raw_domains = config.get("domainList", [])
        return [domain for domain in (_normalize_domain(item) for item in raw_domains) if _is_usable_domain(domain)]

    def assert_no_recipient_mode(self) -> dict[str, Any]:
        settings = self.get_private_settings()
        if settings.get("noRecipient") != 0:
            raise SkyMailApiError(
                "Target site has noRecipient disabled, so random unregistered inboxes will bounce.",
                code="NO_RECIPIENT_DISABLED",
                payload=settings,
            )
        return settings

    def random_local_part(self, length: int | None = None) -> str:
        size = max(4, int(length or self.random_local_length))
        first = random.choice(string.ascii_lowercase)
        tail = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(size - 1))
        return first + tail

    def create_random_inbox(self, *, domain: str = "", local_length: int | None = None) -> dict[str, Any]:
        self.assert_no_recipient_mode()
        domains = self.get_domains()
        if not domains:
            raise SkyMailApiError("No usable domains were exposed by the target site.")

        preferred = _normalize_domain(domain or self.default_domain)
        selected = preferred or domains[0]
        if selected not in domains:
            raise SkyMailApiError(f"Requested domain is not available: {selected}")

        local_part = self.random_local_part(local_length)
        return {
            "address": f"{local_part}@{selected}",
            "localPart": local_part,
            "domain": selected,
            "mode": "noRecipient",
        }

    @staticmethod
    def _format_messages(messages: list[dict[str, Any]], address: str) -> list[dict[str, Any]]:
        target = address.strip().lower()
        matched = [item for item in messages if str(item.get("toEmail", "")).strip().lower() == target]
        matched.sort(key=lambda item: int(item.get("emailId", 0)))

        return [
            {
                "emailId": item.get("emailId"),
                "from": item.get("sendEmail"),
                "fromName": item.get("name"),
                "to": item.get("toEmail"),
                "subject": item.get("subject"),
                "text": item.get("text"),
                "html": item.get("content"),
                "status": item.get("status"),
                "createdAt": item.get("createTime"),
                "raw": item,
            }
            for item in matched
        ]

    def list_inbox_messages(self, address: str, *, limit: int = 20, mode: str = "noone") -> dict[str, Any]:
        query = {
            "size": max(1, min(int(limit), 50)),
            "accountEmail": address,
        }
        if mode:
            query["type"] = mode

        data = self.request("/api/allEmail/list", query=query, auth=True)
        messages = self._format_messages(data.get("list", []), address)
        return {
            "address": address,
            "total": int(data.get("total", 0)),
            "latestEmail": data.get("latestEmail"),
            "messages": messages,
        }

    def wait_for_messages(
        self,
        address: str,
        *,
        after_id: int = 0,
        timeout_ms: int = 30000,
        poll_ms: int = 3000,
        limit: int = 20,
        mode: str = "noone",
    ) -> dict[str, Any]:
        deadline = time.time() + max(1000, timeout_ms) / 1000
        cursor = max(0, int(after_id))

        while time.time() <= deadline:
            listed = self.list_inbox_messages(address, limit=limit, mode=mode)
            messages = [item for item in listed["messages"] if int(item.get("emailId", 0) or 0) > cursor]
            if messages:
                return {
                    "address": address,
                    "afterId": after_id,
                    "messages": messages,
                }

            if listed["messages"]:
                cursor = max(cursor, max(int(item.get("emailId", 0) or 0) for item in listed["messages"]))

            if time.time() + (poll_ms / 1000) > deadline:
                break

            time.sleep(max(1000, poll_ms) / 1000)

        return {
            "address": address,
            "afterId": after_id,
            "messages": [],
        }

    def send_email(
        self,
        *,
        account_id: int,
        receive_emails: list[str],
        subject: str,
        text: str,
        content: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> Any:
        html = content if content is not None else f"<div>{text}</div>"
        return self.request(
            "/api/email/send",
            method="POST",
            auth=True,
            body={
                "accountId": account_id,
                "receiveEmail": receive_emails,
                "subject": subject,
                "text": text,
                "content": html,
                "attachments": attachments or [],
            },
        )
