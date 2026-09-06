"""Offline validation of an Investigation or Response Agent JSON fixture."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.integrations.adapters.investigation import parse_investigation_response
from app.integrations.adapters.response import parse_response_result
from app.integrations.contracts.investigation import InvestigationRequestV1
from app.integrations.contracts.response import ResponseRequestV1


def validate(agent: str, kind: str, payload: dict) -> None:
    if agent == "investigation" and kind == "request":
        InvestigationRequestV1.model_validate(payload)
        return
    if agent == "investigation":
        parse_investigation_response(payload)
        return
    if kind == "request":
        ResponseRequestV1.model_validate(payload)
        return
    parse_response_result(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an agent contract fixture without calling a remote agent.")
    parser.add_argument("--agent", required=True, choices=("investigation", "response"))
    parser.add_argument("--file", required=True)
    parser.add_argument("--kind", choices=("request", "response"), default="response")
    args = parser.parse_args()
    path = Path(args.file)
    if not path.is_file():
        print(f"File not found: {path}")
        return 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    try:
        validate(args.agent, args.kind, payload)
    except Exception as exc:
        print(f"INVALID: {exc}")
        return 1
    print("VALID: fixture matches AquaPulse contract 1.0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
