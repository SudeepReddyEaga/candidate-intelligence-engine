import json
from pathlib import Path
from unittest import mock

import pytest
from pydantic import ValidationError

from candidate_transformer.api.app import create_app
from candidate_transformer.cli.main import _load_projection, main
from candidate_transformer.domain import PartialCandidate, SourcePayload, SourceType, TransformInput
from candidate_transformer.embeddings.provider import (
    HashEmbeddingProvider,
    cosine_similarity,
    create_embedding_provider,
)
from candidate_transformer.extraction.parsers import (
    _split_skills,
    parse_ats_json,
    parse_csv,
    parse_github_json,
    parse_resume_pdf,
    parse_source,
)
from candidate_transformer.ingestion.detection import detect_source_type, load_source
from candidate_transformer.normalization.normalizer import (
    canonicalize_skill,
    normalize_url,
    normalize_phone,
)
from candidate_transformer.pipeline import CandidateTransformer
from candidate_transformer.utils.errors import CandidateTransformerError, ParseError, UnsupportedSourceError


def test_cosine_similarity():
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0


def test_hash_embedding_zero_norm():
    provider = HashEmbeddingProvider(dimensions=1)
    vec = provider.encode(["   "])
    assert vec == [[0.0]]


@mock.patch("os.getenv")
def test_create_embedding_provider(mock_getenv):
    # test sentence-transformer backend instantiation
    # mock to avoid downloading model
    mock_getenv.side_effect = lambda k, d: "sentence-transformer" if k == "CANDIDATE_TRANSFORMER_EMBEDDING_BACKEND" else d
    with mock.patch("candidate_transformer.embeddings.provider.SentenceTransformerProvider"):
        provider = create_embedding_provider()
        assert provider is not None


def test_split_skills():
    assert _split_skills(None) == ()


def test_parse_csv_unicode_error():
    payload = SourcePayload(source_type=SourceType.CSV, name="bad.csv", content=b"\xff\xfe\x00")
    with pytest.raises(ParseError, match="not valid UTF-8"):
        parse_csv(payload)


def test_parse_csv_empty():
    payload = SourcePayload(source_type=SourceType.CSV, name="empty.csv", content=b"name,email\n")
    with pytest.raises(ParseError, match="no candidate rows"):
        parse_csv(payload)


def test_parse_ats_json_not_dict():
    payload = SourcePayload(source_type=SourceType.ATS_JSON, name="arr.json", content=b'{"candidate": []}')
    with pytest.raises(ParseError, match="must be an object"):
        parse_ats_json(payload)


def test_parse_github_json_unicode_error():
    payload = SourcePayload(source_type=SourceType.GITHUB_JSON, name="bad.json", content=b"\xff\xfe\x00")
    with pytest.raises(ParseError, match="malformed"):
        parse_github_json(payload)


def test_parse_github_json_not_dict():
    payload = SourcePayload(source_type=SourceType.GITHUB_JSON, name="arr.json", content=b"[]")
    with pytest.raises(ParseError, match="must be an object"):
        parse_github_json(payload)


def test_parse_resume_pdf_exception():
    payload = SourcePayload(source_type=SourceType.RESUME_PDF, name="bad.pdf", content=b"not a pdf")
    with pytest.raises(ParseError, match="could not be parsed"):
        parse_resume_pdf(payload)


def test_parse_resume_pdf_empty():
    # Empty pdf
    with mock.patch("candidate_transformer.extraction.parsers.PdfReader") as MockReader:
        mock_reader = MockReader.return_value
        mock_reader.pages = [mock.Mock(extract_text=lambda: "")]
        payload = SourcePayload(source_type=SourceType.RESUME_PDF, name="empty.pdf", content=b"fake")
        with pytest.raises(ParseError, match="did not contain extractable text"):
            parse_resume_pdf(payload)


def test_parse_source_unsupported():
    payload = SourcePayload(source_type=SourceType.CSV, name="fake", content=b"")
    with mock.patch.dict("candidate_transformer.extraction.parsers.PARSERS", {}, clear=True):
        with pytest.raises(UnsupportedSourceError, match="No parser registered"):
            parse_source(payload)



def test_normalize_phone_start_1_11_digits():
    assert normalize_phone("12345678901") == "+12345678901"


def test_normalize_url():
    assert normalize_url("google.com") == "https://google.com"
    assert normalize_url("http://") is None


def test_canonicalize_skill_empty():
    assert canonicalize_skill("   ") == ""


def test_canonicalize_skill_match_no_match():
    # exact match tested elsewhere, fuzzy match
    assert canonicalize_skill("ml") == "Machine Learning"
    # no match
    assert canonicalize_skill("some random skill") == "Some Random Skill"


def test_detect_source_type_unsupported():
    with pytest.raises(UnsupportedSourceError, match="Unsupported source extension"):
        detect_source_type(Path("test.xyz"))


def test_pipeline_validation_error():
    transformer = CandidateTransformer()
    with mock.patch.object(transformer.validator, "validate", side_effect=CandidateTransformerError("bad")):
        with pytest.raises(CandidateTransformerError, match="bad"):
            from candidate_transformer.domain import ProjectionConfig
            request = TransformInput(sources=[], projection=ProjectionConfig())
            with mock.patch.object(transformer, "_parse", return_value=[PartialCandidate(source_name="a", source_type=SourceType.NOTES, name="Test")]):
                transformer.transform(request)


def test_cli_load_projection_none():
    assert _load_projection(None) is not None


def test_cli_main_exception(capsys):
    assert main(["--csv", "non_existent.csv"]) == 2
    out, err = capsys.readouterr()
    assert "Input file does not exist" in err


def test_api_health():
    from fastapi.testclient import TestClient
    app = create_app()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

