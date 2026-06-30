from pathlib import Path

import pytest

from candidate_transformer.domain import SourcePayload, SourceType
from candidate_transformer.extraction.parsers import parse_source
from candidate_transformer.ingestion.detection import detect_source_type, load_source
from candidate_transformer.normalization.normalizer import canonicalize_skill, normalize_partial
from candidate_transformer.utils.errors import ParseError, UnsupportedSourceError


def test_detect_source_type() -> None:
    assert detect_source_type(Path("recruiter.csv")) == SourceType.CSV
    assert detect_source_type(Path("resume.pdf")) == SourceType.RESUME_PDF
    assert detect_source_type(Path("github_profile.json")) == SourceType.GITHUB_JSON
    assert detect_source_type(Path("ats.json")) == SourceType.ATS_JSON


def test_missing_source_is_graceful(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedSourceError):
        load_source(tmp_path / "missing.csv")


def test_parse_csv_and_normalize() -> None:
    source = SourcePayload(
        source_type=SourceType.CSV,
        name="recruiter.csv",
        content=(
            b"name,email,phone,skills\n" b"ADA LOVELACE,ADA@EXAMPLE.COM,(415) 555-0100,py;ml;k8s\n"
        ),
    )
    candidate = normalize_partial(parse_source(source)[0])
    assert candidate.name == "Ada Lovelace"
    assert candidate.emails == ("ada@example.com",)
    assert candidate.phones == ("+14155550100",)
    assert candidate.skills == ("Kubernetes", "Machine Learning", "Python")
    assert "skills" in candidate.provenance


def test_parse_ats_json() -> None:
    source = SourcePayload(
        source_type=SourceType.ATS_JSON,
        name="ats.json",
        content=(
            b'{"candidate":{"full_name":"Ada Byron",'
            b'"email":"ada@example.com","skills":["pytorch"]}}'
        ),
    )
    candidate = normalize_partial(parse_source(source)[0])
    assert candidate.name == "Ada Byron"
    assert candidate.skills == ("PyTorch",)


def test_malformed_json_fails_cleanly() -> None:
    source = SourcePayload(source_type=SourceType.ATS_JSON, name="bad.json", content=b"{")
    with pytest.raises(ParseError, match="malformed"):
        parse_source(source)


def test_github_and_notes_parsers() -> None:
    github = parse_source(
        SourcePayload(
            source_type=SourceType.GITHUB_JSON,
            name="github.json",
            content=b'{"name":"Ada Lovelace","html_url":"github.com/ada","topics":["fastapi"]}',
        )
    )[0]
    notes = parse_source(
        SourcePayload(
            source_type=SourceType.NOTES,
            name="notes.txt",
            content=b"Email ada@example.com and call +1 415 555 0100.",
        )
    )[0]
    assert normalize_partial(github).github_url == "https://github.com/ada"
    assert normalize_partial(github).skills == ("FastAPI",)
    assert notes.emails == ("ada@example.com",)
    assert notes.phones == ("+1 415 555 0100",)


def test_broken_pdf_fails_cleanly() -> None:
    source = SourcePayload(
        source_type=SourceType.RESUME_PDF, name="broken.pdf", content=b"not a pdf"
    )
    with pytest.raises(ParseError, match="could not be parsed"):
        parse_source(source)


def test_duplicate_skills_canonicalize() -> None:
    assert canonicalize_skill("k8s") == "Kubernetes"
    assert canonicalize_skill("machine   learning") == "Machine Learning"
