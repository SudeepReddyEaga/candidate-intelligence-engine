from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError as PydanticValidationError

from candidate_transformer.domain import ProjectionConfig, SourceType, TransformInput
from candidate_transformer.ingestion.detection import load_source
from candidate_transformer.pipeline import CandidateTransformer
from candidate_transformer.utils.errors import CandidateTransformerError
from candidate_transformer.utils.logging import configure_logging


def _load_projection(path: Path | None) -> ProjectionConfig:
    if path is None:
        return ProjectionConfig()
    return ProjectionConfig.model_validate_json(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transform multi-source candidate data into canonical JSON."
    )
    parser.add_argument("--resume", type=Path, help="Resume PDF path")
    parser.add_argument("--csv", type=Path, help="Recruiter CSV path")
    parser.add_argument("--ats-json", type=Path, help="ATS JSON path")
    parser.add_argument("--github-json", type=Path, help="GitHub profile JSON path")
    parser.add_argument("--notes", type=Path, help="Recruiter notes text file")
    parser.add_argument("--config", type=Path, help="Projection config JSON path")
    parser.add_argument("--output", type=Path, help="Optional output JSON path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    source_args = [
        (args.resume, SourceType.RESUME_PDF),
        (args.csv, SourceType.CSV),
        (args.ats_json, SourceType.ATS_JSON),
        (args.github_json, SourceType.GITHUB_JSON),
        (args.notes, SourceType.NOTES),
    ]
    try:
        sources = [load_source(path, source_type) for path, source_type in source_args if path]
        if not sources:
            raise CandidateTransformerError("At least one input source is required")
        request = TransformInput(sources=sources, projection=_load_projection(args.config))
        result = CandidateTransformer().transform(request)
        output = json.dumps(result, indent=2, sort_keys=True)
        if args.output:
            args.output.write_text(output + "\n", encoding="utf-8")
        else:
            sys.stdout.write(output + "\n")
        return 0
    except (CandidateTransformerError, PydanticValidationError, OSError, KeyError) as exc:
        sys.stderr.write(f"candidate-transformer: {exc}\n")
        return 2
