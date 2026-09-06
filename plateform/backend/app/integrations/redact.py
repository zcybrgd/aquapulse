"""Remove secrets before persistence or API responses. Never log credentials."""

from copy import deepcopy
from typing import Any

SECRET_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "access_token",
    "refresh_token",
    "token",
    "password",
    "secret",
    "client_secret",
    "groq_api_key",
    "groq",
    "bearer",
    "private_key",
}


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in SECRET_KEYS or "api_key" in str(key).lower() or "secret" in str(key).lower():
                redacted[key] = "[redacted]"
            else:
                redacted[key] = redact_payload(item)
        return redacted
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    return deepcopy(value) if isinstance(value, dict) else value


def contains_secret(value: Any) -> bool:
    text = str(value).lower()
    return any(token in text for token in ("groq-", "sk-", "bearer ", "password="))
