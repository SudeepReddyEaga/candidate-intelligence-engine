from __future__ import annotations

import re
from urllib.parse import urlparse

from rapidfuzz import process

from candidate_transformer.domain import PartialCandidate

SKILL_ALIASES = {
    "py": "Python",
    "python": "Python",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "fastapi": "FastAPI",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
}


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return f"+1{digits}"
    if digits.startswith("1") and len(digits) == 11:
        return f"+{digits}"
    return f"+{digits}" if digits else ""


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None
    return " ".join(part.capitalize() for part in name.split())


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    candidate = url.strip()
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if not parsed.netloc:
        return None
    return parsed.geturl().rstrip("/")


def canonicalize_skill(skill: str) -> str:
    cleaned = re.sub(r"\s+", " ", skill.strip().lower())
    if not cleaned:
        return ""
    if cleaned in SKILL_ALIASES:
        return SKILL_ALIASES[cleaned]
    match = process.extractOne(cleaned, SKILL_ALIASES.keys(), score_cutoff=88)
    if match:
        return SKILL_ALIASES[match[0]]
    return " ".join(part.capitalize() for part in cleaned.split())


def normalize_partial(candidate: PartialCandidate) -> PartialCandidate:
    emails = tuple(sorted({normalize_email(email) for email in candidate.emails if email.strip()}))
    phones = tuple(
        sorted({phone for phone in (normalize_phone(p) for p in candidate.phones) if phone})
    )
    skills = tuple(
        sorted({skill for skill in (canonicalize_skill(raw) for raw in candidate.skills) if skill})
    )
    github_url = normalize_url(candidate.github_url)
    location = " ".join(candidate.location.split()) if candidate.location else None
    return candidate.model_copy(
        update={
            "name": normalize_name(candidate.name),
            "emails": emails,
            "phones": phones,
            "location": location,
            "skills": skills,
            "github_url": github_url,
        }
    )
