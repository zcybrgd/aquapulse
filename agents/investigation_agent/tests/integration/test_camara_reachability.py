from __future__ import annotations

from aia.clients.camara_client import build_camara_client


def main() -> None:
    client = build_camara_client()

    test_devices = {
        "+99999991001": "DATA connectivity — expected reachable",
        "+99999991003": "Lost connectivity — expected unreachable",
    }

    for phone_number, description in test_devices.items():
        print("=" * 70)
        print(f"Device:   {phone_number}")
        print(f"Scenario: {description}")

        try:
            status = client.get_device_reachability(phone_number)

            print("\nRaw response:")
            print(status)

            print("\nReachability:")
            print("  reachable   :", getattr(status, "reachable", None))
            print("  connectivity:", getattr(status, "connectivity", None))
            print(
                "  lastStatusTime:",
                getattr(status, "last_status_time", None),
            )

        except Exception as exc:
            print("\nERROR:")
            print(f"  {type(exc).__name__}: {exc}")

    print("=" * 70)


if __name__ == "__main__":
    main()