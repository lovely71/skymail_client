from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def _read_int(name: str, fallback: int) -> int:
    value = os.getenv(name)
    if not value:
        return fallback

    try:
        return int(value)
    except ValueError:
        return fallback


def _read_domains(value: str) -> tuple[str, ...]:
    if not value:
        return tuple()

    domains: list[str] = []
    for item in value.split(","):
        domain = item.strip().lstrip("@").lower()
        if domain and domain not in domains:
            domains.append(domain)
    return tuple(domains)


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    app_token: str
    skymail_base_url: str
    skymail_email: str
    skymail_password: str
    preferred_domains: tuple[str, ...]
    random_local_length: int
    default_poll_ms: int
    default_wait_timeout_ms: int
    request_timeout_sec: int
    domain_failure_threshold: int


def load_config() -> Config:
    load_dotenv()
    preferred_domains = _read_domains(
        os.getenv("PREFERRED_DOMAINS", "") or os.getenv("DEFAULT_DOMAIN", "")
    )

    return Config(
        host=os.getenv("HOST", "127.0.0.1"),
        port=_read_int("PORT", 3000),
        app_token=os.getenv("APP_TOKEN", ""),
        skymail_base_url=os.getenv("SKYMAIL_BASE_URL", "").rstrip("/"),
        skymail_email=os.getenv("SKYMAIL_EMAIL", ""),
        skymail_password=os.getenv("SKYMAIL_PASSWORD", ""),
        preferred_domains=preferred_domains,
        random_local_length=max(4, _read_int("RANDOM_LOCAL_LENGTH", 10)),
        default_poll_ms=max(1000, _read_int("DEFAULT_POLL_MS", 3000)),
        default_wait_timeout_ms=max(1000, _read_int("DEFAULT_WAIT_TIMEOUT_MS", 30000)),
        request_timeout_sec=max(5, _read_int("REQUEST_TIMEOUT_SEC", 30)),
        domain_failure_threshold=max(1, _read_int("DOMAIN_FAILURE_THRESHOLD", 3)),
    )


def validate_config(config: Config) -> None:
    missing = []

    if not config.skymail_base_url:
        missing.append("SKYMAIL_BASE_URL")
    if not config.skymail_email:
        missing.append("SKYMAIL_EMAIL")
    if not config.skymail_password:
        missing.append("SKYMAIL_PASSWORD")

    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
