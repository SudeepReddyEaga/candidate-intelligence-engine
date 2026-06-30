from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from candidate_transformer.utils.errors import ValidationError


def default_schema_path() -> Path:
    return Path(__file__).resolve().parents[3] / "schemas" / "candidate.schema.json"


class CandidateValidator:
    def __init__(self, schema_path: Path | None = None) -> None:
        path = schema_path or default_schema_path()
        self.schema = json.loads(path.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.schema)

    def validate(self, payload: dict[str, Any]) -> None:
        errors = sorted(self.validator.iter_errors(payload), key=lambda error: list(error.path))
        if errors:
            message = "; ".join(error.message for error in errors)
            raise ValidationError(message)
