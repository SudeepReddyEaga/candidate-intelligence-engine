from __future__ import annotations

import hashlib

from candidate_transformer.domain import CandidateRecord, PartialCandidate, ProvenanceEntry

SOURCE_PRIORITY = {
    "ats_json": 5,
    "resume_pdf": 4,
    "csv": 3,
    "github_json": 2,
    "notes": 1,
}


def _candidate_id(candidates: list[PartialCandidate]) -> str:
    stable_parts: list[str] = []
    for candidate in candidates:
        stable_parts.extend(candidate.emails)
        stable_parts.extend(candidate.phones)
        if candidate.name:
            stable_parts.append(candidate.name.lower())
    digest = hashlib.sha256("|".join(sorted(stable_parts)).encode("utf-8")).hexdigest()[:16]
    return f"cand_{digest}"


def _best_scalar(candidates: list[PartialCandidate], field: str) -> object:
    values: list[tuple[int, object]] = []
    for candidate in candidates:
        value = getattr(candidate, field)
        if value not in (None, "", [], ()):
            values.append((SOURCE_PRIORITY[candidate.source_type.value], value))
    if not values:
        return None
    values.sort(key=lambda item: item[0], reverse=True)
    return values[0][1]


def _merge_provenance(candidates: list[PartialCandidate]) -> dict[str, list[ProvenanceEntry]]:
    merged: dict[str, list[ProvenanceEntry]] = {}
    for candidate in candidates:
        for field, entries in candidate.provenance.items():
            merged.setdefault(field, []).extend(entries)
    return merged


def merge_candidates(candidates: list[PartialCandidate]) -> CandidateRecord:
    emails = sorted({email for candidate in candidates for email in candidate.emails})
    phones = sorted({phone for candidate in candidates for phone in candidate.phones})
    skills = sorted({skill for candidate in candidates for skill in candidate.skills})
    experience = []
    for candidate in candidates:
        for item in candidate.experience:
            if item not in experience:
                experience.append(item)
    education = []
    for candidate in candidates:
        for item in candidate.education:
            if item not in education:
                education.append(item)
    projects = []
    for candidate in candidates:
        for item in candidate.projects:
            if item not in projects:
                projects.append(item)
    return CandidateRecord(
        candidate_id=_candidate_id(candidates),
        name=_best_scalar(candidates, "name"),
        emails=emails,
        phones=phones,
        location=_best_scalar(candidates, "location"),
        skills=skills,
        experience_years=_best_scalar(candidates, "experience_years"),
        github_url=_best_scalar(candidates, "github_url"),
        linkedin_url=_best_scalar(candidates, "linkedin_url"),
        portfolio_url=_best_scalar(candidates, "portfolio_url"),
        experience=experience,
        projects=projects,
        education=education,
        resume_text=_best_scalar(candidates, "resume_text"),
        notes=_best_scalar(candidates, "notes"),
        provenance=_merge_provenance(candidates),
    )
