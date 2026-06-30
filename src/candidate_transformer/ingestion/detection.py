from __future__ import annotations

from pathlib import Path

from candidate_transformer.domain import SourcePayload, SourceType
from candidate_transformer.utils.errors import UnsupportedSourceError

EXTENSION_TYPES = {
    ".csv": SourceType.CSV,
    ".pdf": SourceType.RESUME_PDF,
    ".txt": SourceType.NOTES,
}


def detect_source_type(path: Path, explicit_type: SourceType | None = None) -> SourceType:
    if explicit_type is not None:
        return explicit_type
    suffix = path.suffix.lower()
    if suffix == ".json":
        lower_name = path.name.lower()
        if "github" in lower_name:
            return SourceType.GITHUB_JSON
        return SourceType.ATS_JSON
    if suffix in EXTENSION_TYPES:
        return EXTENSION_TYPES[suffix]
    raise UnsupportedSourceError(f"Unsupported source extension for {path}")


def load_source(path: Path, explicit_type: SourceType | None = None) -> SourcePayload:
    if not path.exists():
        raise UnsupportedSourceError(f"Input file does not exist: {path}")
    return SourcePayload(
        source_type=detect_source_type(path, explicit_type),
        name=path.name,
        content=path.read_bytes(),
    )
