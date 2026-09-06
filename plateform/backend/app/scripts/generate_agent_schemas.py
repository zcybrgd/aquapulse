"""Generate JSON Schema files from Pydantic contracts so docs stay aligned."""

from pathlib import Path
import json

from app.integrations.contracts.investigation import InvestigationRequestV1, InvestigationResponseV1
from app.integrations.contracts.response import ResponseRequestV1, ResponseResultV1

ROOT = Path(__file__).resolve().parents[2] / "contracts" / "agents"


def write_schema(path: Path, model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8")


def main() -> None:
    write_schema(ROOT / "investigation" / "v1" / "request.schema.json", InvestigationRequestV1)
    write_schema(ROOT / "investigation" / "v1" / "response.schema.json", InvestigationResponseV1)
    write_schema(ROOT / "response" / "v1" / "request.schema.json", ResponseRequestV1)
    write_schema(ROOT / "response" / "v1" / "response.schema.json", ResponseResultV1)
    print(f"Wrote JSON Schema files under {ROOT}")


if __name__ == "__main__":
    main()
