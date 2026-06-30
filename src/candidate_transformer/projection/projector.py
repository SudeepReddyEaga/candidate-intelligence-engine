from __future__ import annotations

from typing import Any

from candidate_transformer.domain import CandidateRecord, ProjectionConfig


def _is_missing(value: Any) -> bool:
    return value in (None, "", [], {})


def project_record(record: CandidateRecord, config: ProjectionConfig) -> dict[str, Any]:
    loc_str = record.location
    loc_obj = {"city": None, "region": None, "country": None}
    if loc_str:
        parts = [p.strip() for p in loc_str.split(",")]
        loc_obj["city"] = parts[0]
        if len(parts) > 1:
            loc_obj["country"] = parts[-1]
            if len(parts) > 2:
                loc_obj["region"] = parts[1]

    def format_url(url: str | None) -> str | None:
        if url and not (url.startswith("http://") or url.startswith("https://")):
            return f"https://{url}"
        return url

    links_obj = {
        "linkedin": format_url(record.linkedin_url),
        "github": format_url(record.github_url),
        "portfolio": format_url(record.portfolio_url),
        "other": []
    }

    skills_arr = []
    for skill in record.skills:
        skill_conf = record.confidence.fields.get("skills", 0.0)
        skill_sources = []
        for prov in record.provenance.get("skills", []):
            if isinstance(prov.raw_value, list) and any(skill.lower() == str(s).lower() for s in prov.raw_value):
                skill_sources.append(prov.source_name)
            elif isinstance(prov.raw_value, str) and skill.lower() in prov.raw_value.lower():
                skill_sources.append(prov.source_name)
        if not skill_sources:
            for prov in record.provenance.get("skills", []):
                skill_sources.append(prov.source_name)
                
        skills_arr.append({
            "name": skill,
            "confidence": skill_conf,
            "sources": list(set(skill_sources))
        })

    prov_arr = []
    for field, entries in record.provenance.items():
        for entry in entries:
            prov_arr.append({
                "field": field,
                "source": entry.source_name,
                "method": entry.parser
            })

    def format_email(email: str) -> str:
        if email and email.startswith("mailto:"):
            return email.replace("mailto:", "").strip()
        return email.strip() if email else email

    full_payload = {
        "candidate_id": record.candidate_id,
        "full_name": record.name,
        "emails": [format_email(e) for e in record.emails],
        "phones": record.phones,
        "location": loc_obj,
        "links": links_obj,
        "headline": None,
        "years_experience": record.experience_years,
        "skills": skills_arr,
        "experience": record.experience,
        "projects": record.projects,
        "education": record.education,
        "provenance": prov_arr,
        "overall_confidence": record.confidence.overall
    }

    if not config.include_confidence:
        full_payload.pop("overall_confidence", None)
    if not config.include_provenance:
        full_payload.pop("provenance", None)

    selected = config.fields or list(full_payload.keys())
    projected: dict[str, Any] = {}
    for field in selected:
        if field not in full_payload:
            if config.missing_value_policy == "error":
                raise KeyError(f"Requested projection field is not available: {field}")
            if config.missing_value_policy == "include_null":
                projected[config.rename.get(field, field)] = None
            continue
        value = full_payload[field]
        if config.missing_value_policy == "omit" and _is_missing(value):
            continue
        projected[config.rename.get(field, field)] = value
    return projected
