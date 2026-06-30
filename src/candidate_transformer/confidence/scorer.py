from __future__ import annotations

from candidate_transformer.domain import CandidateRecord, ConfidenceReport

CRITICAL_FIELDS = ("name", "emails", "skills")


def _field_confidence(record: CandidateRecord, field: str) -> tuple[float, str]:
    value = getattr(record, field)
    provenance_count = len(record.provenance.get(field, []))
    has_value = value not in (None, "", [], ())
    if not has_value:
        return 0.0, "missing value"
    base = 0.55
    support = min(0.35, provenance_count * 0.12)
    conflict_penalty = 0.0
    if field in ("emails", "phones", "skills") and isinstance(value, list):
        conflict_penalty = 0.0 if len(value) == len(set(value)) else 0.15
    score = max(0.0, min(1.0, base + support - conflict_penalty))
    entry_label = "entry" if provenance_count == 1 else "entries"
    explanation = f"value present with {provenance_count} provenance {entry_label}"
    return round(score, 3), explanation


def calculate_confidence(record: CandidateRecord) -> ConfidenceReport:
    fields = [
        "name",
        "emails",
        "phones",
        "location",
        "skills",
        "experience_years",
        "github_url",
        "resume_text",
        "notes",
    ]
    field_scores: dict[str, float] = {}
    explanations: dict[str, str] = {}
    for field in fields:
        score, explanation = _field_confidence(record, field)
        field_scores[field] = score
        explanations[field] = explanation
    overall_inputs = [field_scores[field] for field in CRITICAL_FIELDS] + list(
        field_scores.values()
    )
    overall = round(sum(overall_inputs) / len(overall_inputs), 3)
    return ConfidenceReport(overall=overall, fields=field_scores, explanations=explanations)
