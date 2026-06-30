import pytest

from candidate_transformer.confidence.scorer import calculate_confidence
from candidate_transformer.domain import (
    PartialCandidate,
    ProjectionConfig,
    ProvenanceEntry,
    SourceType,
)
from candidate_transformer.embeddings.provider import HashEmbeddingProvider
from candidate_transformer.entity_resolution.resolver import EntityResolver
from candidate_transformer.merge.merger import merge_candidates
from candidate_transformer.projection.projector import project_record
from candidate_transformer.validation.json_schema import CandidateValidator


def _candidate(
    name: str = "Ada Lovelace",
    email: str = "ada@example.com",
    skills: tuple[str, ...] = ("Python",),
) -> PartialCandidate:
    entry = ProvenanceEntry(
        source_type=SourceType.ATS_JSON,
        source_name="ats.json",
        field_path="emails",
        raw_value=email,
        parser="test",
    )
    return PartialCandidate(
        source_name="ats.json",
        source_type=SourceType.ATS_JSON,
        name=name,
        emails=(email,),
        skills=skills,
        provenance={"emails": (entry,), "name": (entry,), "skills": (entry,)},
    )


def test_duplicate_detection_by_shared_email() -> None:
    resolver = EntityResolver(HashEmbeddingProvider())
    left = _candidate(name="Ada Lovelace")
    right = _candidate(name="Ada Byron Lovelace")
    explanation = resolver.score(left, right)
    assert explanation.score == 1.0
    assert resolver.cluster([left, right]) == [[left, right]]


def test_merge_conflicting_emails_keeps_both_and_scores() -> None:
    left = _candidate(email="ada@example.com")
    right = _candidate(email="ada@work.example")
    record = merge_candidates([left, right])
    record.confidence = calculate_confidence(record)
    assert record.emails == ["ada@example.com", "ada@work.example"]
    assert record.confidence.fields["emails"] > 0.5


def test_projection_renames_and_hides_metadata() -> None:
    record = merge_candidates([_candidate()])
    record.confidence = calculate_confidence(record)
    projected = project_record(
        record,
        ProjectionConfig(
            fields=["candidate_id", "emails", "overall_confidence", "provenance"],
            rename={"emails": "contact_emails"},
            include_confidence=False,
            include_provenance=False,
            missing_value_policy="omit",
        ),
    )
    assert "contact_emails" in projected
    assert "overall_confidence" not in projected
    assert "provenance" not in projected


def test_projection_missing_field_policy_error() -> None:
    with pytest.raises(KeyError):
        project_record(
            merge_candidates([_candidate()]),
            ProjectionConfig(fields=["unknown"], missing_value_policy="error"),
        )


def test_json_schema_validation_accepts_canonical_record() -> None:
    record = merge_candidates([_candidate()])
    record.confidence = calculate_confidence(record)
    projected = project_record(record, ProjectionConfig())
    CandidateValidator().validate(projected)
