"""Recursive redaction of secrets, identities, paths and internal URLs."""

from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"
SENSITIVE_TOKENS = (
    "api_key",
    "token",
    "authorization",
    "secret",
    "password",
    "cookie",
    "operator_contact",
    "device_msisdn",
    "base_url",
    "service_url",
    "webhook_url",
)
PATH_RE = re.compile(r"(?i)(/home/|/Users/|[A-Za-z]:\\Users\\)")
INTERNAL_URL_RE = re.compile(r"(?i)https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d+|192\.168\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+)[^\s]*")
URL_KEY_RE = re.compile(r"(?i)(^|_)url$")


def _is_sensitive_key(key: str) -> bool:
    lowered = key.casefold()
    if any(token in lowered for token in SENSITIVE_TOKENS):
        return True
    return bool(URL_KEY_RE.search(lowered))


def _is_sensitive_value(value: str) -> bool:
    if PATH_RE.search(value):
        return True
    return bool(INTERNAL_URL_RE.search(value))


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(str(key)):
                cleaned[key] = REDACTED
            else:
                cleaned[key] = sanitize_payload(item)
        return cleaned
    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_payload(item) for item in value]
    if isinstance(value, str) and _is_sensitive_value(value):
        return REDACTED
    return value
