"""Friend handoff: check that a remote agent matches AquaPulse contract 1.0."""

from __future__ import annotations

import argparse
import sys

from app.integrations.contract_check import check_agent_contract


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Investigation or Response Agent contract compatibility.")
    parser.add_argument("--agent", required=True, choices=("investigation", "response"))
    parser.add_argument("--base-url", required=True, help="Trusted agent base URL from local configuration")
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    result = check_agent_contract(args.agent, args.base_url, timeout=args.timeout)
    print(f"Agent: {result.agent}")
    for step in result.steps:
        mark = "PASS" if step.ok else "FAIL"
        print(f"  [{mark}] {step.name}: {step.detail}")
    if result.compatible:
        print("Compatible with AquaPulse contract 1.0.")
        print("No notification or valve command was executed.")
        return 0
    print("Incompatible with AquaPulse contract 1.0.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
