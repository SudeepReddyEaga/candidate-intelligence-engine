from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Callable
from typing import Any

from pypdf import PdfReader

from candidate_transformer.domain import (
    PartialCandidate,
    ProvenanceEntry,
    SourcePayload,
    SourceType,
)
from candidate_transformer.utils.errors import ParseError, UnsupportedSourceError

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?:\+?\d[\d().\-\s]{7,}\d)")
SKILL_SPLIT_RE = re.compile(r"[,;/|]")
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+")
PORTFOLIO_URL_RE = re.compile(r"\b(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})*(?:/[^\s]*)?\b")


def _prov(source: SourcePayload, field: str, raw_value: Any, parser: str) -> ProvenanceEntry:
    return ProvenanceEntry(
        source_type=source.source_type,
        source_name=source.name,
        field_path=field,
        raw_value=raw_value,
        parser=parser,
    )


def _with_provenance(
    source: SourcePayload, parser: str, values: dict[str, Any]
) -> dict[str, tuple[ProvenanceEntry, ...]]:
    return {
        field: (_prov(source, field, raw, parser),)
        for field, raw in values.items()
        if raw not in (None, "", [], ())
    }


def _split_skills(raw: str | list[str] | None) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, list):
        return tuple(str(item) for item in raw if str(item).strip())
    return tuple(part.strip() for part in SKILL_SPLIT_RE.split(raw) if part.strip())


def parse_csv(source: SourcePayload) -> list[PartialCandidate]:
    try:
        text = source.content.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
    except UnicodeDecodeError as exc:
        raise ParseError(f"CSV is not valid UTF-8: {source.name}") from exc
    if not rows:
        raise ParseError(f"CSV contained no candidate rows: {source.name}")
    parsed = []
    for index, row in enumerate(rows):
        name = row.get("name") or row.get("full_name")
        email = row.get("email") or row.get("emails")
        phone = row.get("phone") or row.get("phones")
        experience = row.get("experience_years")
        raw_values = {
            "name": name,
            "emails": email,
            "phones": phone,
            "location": row.get("location"),
            "skills": row.get("skills"),
            "experience_years": experience,
        }
        parsed.append(
            PartialCandidate(
                source_name=f"{source.name}#{index}",
                source_type=source.source_type,
                name=name,
                emails=tuple(EMAIL_RE.findall(email or "")),
                phones=tuple(PHONE_RE.findall(phone or "")),
                location=row.get("location") or None,
                skills=_split_skills(row.get("skills")),
                experience_years=float(experience) if experience else None,
                provenance=_with_provenance(source, "csv", raw_values),
            )
        )
    return parsed


def parse_ats_json(source: SourcePayload) -> list[PartialCandidate]:
    try:
        payload = json.loads(source.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParseError(f"ATS JSON is malformed: {source.name}") from exc
    candidate = payload.get("candidate", payload) if isinstance(payload, dict) else {}
    if not isinstance(candidate, dict):
        raise ParseError(f"ATS JSON root must be an object: {source.name}")
    email = candidate.get("email") or candidate.get("emails")
    phone = candidate.get("phone") or candidate.get("phones")
    raw_values = {
        "name": candidate.get("full_name") or candidate.get("name"),
        "emails": email,
        "phones": phone,
        "location": candidate.get("location"),
        "skills": candidate.get("skills"),
        "experience_years": candidate.get("experience_years"),
        "github_url": candidate.get("github") or candidate.get("github_url"),
    }
    return [
        PartialCandidate(
            source_name=source.name,
            source_type=source.source_type,
            name=raw_values["name"],
            emails=tuple(
                EMAIL_RE.findall(" ".join(email) if isinstance(email, list) else str(email or ""))
            ),
            phones=tuple(
                PHONE_RE.findall(" ".join(phone) if isinstance(phone, list) else str(phone or ""))
            ),
            location=raw_values["location"],
            skills=_split_skills(raw_values["skills"]),
            experience_years=(
                float(raw_values["experience_years"])
                if raw_values["experience_years"] is not None
                else None
            ),
            github_url=raw_values["github_url"],
            provenance=_with_provenance(source, "ats_json", raw_values),
        )
    ]


def parse_github_json(source: SourcePayload) -> list[PartialCandidate]:
    try:
        payload = json.loads(source.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParseError(f"GitHub JSON is malformed: {source.name}") from exc
    if not isinstance(payload, dict):
        raise ParseError(f"GitHub JSON root must be an object: {source.name}")
    raw_values = {
        "name": payload.get("name"),
        "github_url": payload.get("html_url") or payload.get("url"),
        "location": payload.get("location"),
        "skills": payload.get("skills") or payload.get("topics"),
    }
    return [
        PartialCandidate(
            source_name=source.name,
            source_type=source.source_type,
            name=raw_values["name"],
            location=raw_values["location"],
            github_url=raw_values["github_url"],
            skills=_split_skills(raw_values["skills"]),
            provenance=_with_provenance(source, "github_json", raw_values),
        )
    ]


def parse_notes(source: SourcePayload) -> list[PartialCandidate]:
    text = source.content.decode("utf-8", errors="replace").strip()
    raw_values = {
        "emails": EMAIL_RE.findall(text),
        "phones": PHONE_RE.findall(text),
        "notes": text,
    }
    return [
        PartialCandidate(
            source_name=source.name,
            source_type=source.source_type,
            emails=tuple(raw_values["emails"]),
            phones=tuple(raw_values["phones"]),
            notes=text,
            provenance=_with_provenance(source, "notes", raw_values),
        )
    ]


def parse_resume_pdf(source: SourcePayload) -> list[PartialCandidate]:
    try:
        reader = PdfReader(io.BytesIO(source.content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        
        embedded_urls = []
        for page in reader.pages:
            if "/Annots" in page:
                for annot in page["/Annots"]:
                    try:
                        obj = annot.get_object()
                        if "/A" in obj and "/URI" in obj["/A"]:
                            embedded_urls.append(str(obj["/A"]["/URI"]))
                    except Exception:
                        pass
        if embedded_urls:
            text += "\n" + "\n".join(embedded_urls)
    except Exception as exc:  # pypdf raises several parser-specific exceptions.
        raise ParseError(f"Resume PDF could not be parsed: {source.name}") from exc
    if not text:
        raise ParseError(f"Resume PDF did not contain extractable text: {source.name}")
        
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    name = None
    if lines:
        first_line = lines[0]
        first_line = EMAIL_RE.sub("", first_line)
        first_line = PHONE_RE.sub("", first_line)
        name = first_line.strip()
        if not name and len(lines) > 1:
            name = lines[1].strip()
            
    github_match = GITHUB_RE.search(text)
    github_url = github_match.group(0) if github_match else None
    if github_url and not github_url.startswith("http"):
        github_url = "https://" + github_url
        
    linkedin_match = LINKEDIN_RE.search(text)
    linkedin_url = linkedin_match.group(0) if linkedin_match else None
    if linkedin_url and not linkedin_url.startswith("http"):
        linkedin_url = "https://" + linkedin_url
        
    portfolio_url = None
    text_no_emails = EMAIL_RE.sub(" ", text)
    url_matches = PORTFOLIO_URL_RE.findall(text_no_emails)
    valid_urls = []
    for url in url_matches:
        lower_url = url.lower()
        if "github.com" not in lower_url and "linkedin.com" not in lower_url and "gmail.com" not in lower_url and "google.com" not in lower_url and "@" not in url:
            if not re.match(r"^[a-zA-Z]\.[a-zA-Z]\.$", url):
                valid_urls.append(url)
                
    if valid_urls:
        best_url = valid_urls[0]
        for u in valid_urls:
            lu = u.lower()
            if ".github.io" in lu or "portfolio" in lu:
                best_url = u
                break
        portfolio_url = best_url
        if not portfolio_url.startswith("http"):
            portfolio_url = "https://" + portfolio_url
        
    location = None
    for line in lines[:20]:
        loc_match = re.search(r"([A-Za-z\s]+,\s*(?:India|USA|UK|Canada|Australia|Germany))", line)
        if loc_match:
            location = loc_match.group(1).strip()
            break
            
    skills_raw = []
    
    experiences = []
    current_exp = None
    
    projects = []
    current_proj = None
    
    educations = []
    current_edu = None
    
    date_re = re.compile(r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4}(?:\s*[-–]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4}|(?:\s*[-–]\s*Present))?|\d{4}\s*[-–]\s*\d{4})", re.IGNORECASE)

    current_section = None
    for line in lines:
        lower_line = line.lower()
        if "technical skills" in lower_line or lower_line == "skills":
            current_section = "skills"
            continue
        elif lower_line == "projects":
            current_section = "projects"
            continue
        elif lower_line == "experience" or lower_line == "work experience":
            current_section = "experience"
            continue
        elif lower_line == "education" or lower_line == "education & training":
            current_section = "education"
            continue
        elif lower_line == "certifications" or lower_line == "positions of responsibility" or lower_line == "coding profiles & achievements":
            current_section = None
            continue
        
        clean_line = line.replace("•", "").replace("*", "").strip()
        if not clean_line:
            continue
            
        if current_section == "skills":
            if ":" in clean_line:
                clean_line = clean_line.split(":", 1)[1].strip()
            if clean_line:
                skills_raw.append(clean_line)
                
        elif current_section in ("experience", "projects"):
            clean_line_stripped = clean_line
            is_bullet = line.startswith("–") or line.startswith("-") or line.startswith("•") or line.startswith("*")
            if is_bullet:
                clean_line_stripped = re.sub(r"^[–\-•*]\s*", "", clean_line)
                
            date_match = date_re.search(clean_line_stripped)
            
            # Use appropriate collection
            is_exp = current_section == "experience"
            collection = experiences if is_exp else projects
            current_item = current_exp if is_exp else current_proj
            
            is_new_item = False
            if current_item is None:
                is_new_item = True
            elif date_match and not line.startswith("–") and not line.startswith("-"):
                is_new_item = True
                
            if is_new_item:
                current_item = {"company": None, "title": None, "start": None, "end": None, "summary_lines": []}
                collection.append(current_item)
                if is_exp:
                    current_exp = current_item
                else:
                    current_proj = current_item
                
            if not current_item["title"]:
                if date_match:
                    date_str = date_match.group(1)
                    header_text = clean_line_stripped.replace(date_str, "").strip()
                    if "-" in date_str or "–" in date_str:
                        parts = re.split(r"[-–]", date_str)
                        current_item["start"] = parts[0].strip()
                        current_item["end"] = parts[1].strip()
                    else:
                        current_item["end"] = date_str.strip()
                else:
                    header_text = clean_line_stripped
                    
                if ":" in header_text:
                    parts = header_text.split(":", 1)
                    current_item["company"] = parts[0].strip()
                    current_item["title"] = parts[1].strip()
                else:
                    current_item["title"] = header_text
            else:
                current_item["summary_lines"].append(clean_line_stripped)

        elif current_section == "education":
            date_match = date_re.search(clean_line)
            is_new_edu = date_match is not None
            
            if current_edu is None or (is_new_edu and current_edu.get("institution")):
                current_edu = {"institution": None, "degree": None, "field": None, "end_year": None, "details": []}
                educations.append(current_edu)
            
            if not current_edu["institution"]:
                if date_match:
                    date_str = date_match.group(1)
                    clean_line = clean_line.replace(date_str, "").strip()
                    if "-" in date_str or "–" in date_str:
                        parts = re.split(r"[-–]", date_str)
                        current_edu["end_year"] = parts[1].strip()
                    else:
                        current_edu["end_year"] = date_str.strip()
                current_edu["institution"] = clean_line
            else:
                current_edu["details"].append(clean_line)
                if " in " in clean_line:
                    parts = clean_line.split(" in ", 1)
                    current_edu["degree"] = parts[0].strip()
                    field_part = parts[1]
                    loc_match = re.search(r"([A-Za-z\s]+,\s*[A-Za-z]+)$", field_part)
                    if loc_match:
                        field_part = field_part.replace(loc_match.group(1), "")
                    current_edu["field"] = field_part.strip()
                elif "Specializations:" in clean_line:
                    current_edu["field"] = clean_line.replace("Specializations:", "").strip()

    for exp in experiences:
        exp["summary"] = " ".join(exp.pop("summary_lines")).strip() if exp.get("summary_lines") else None
        
    for proj in projects:
        proj["summary"] = " ".join(proj.pop("summary_lines")).strip() if proj.get("summary_lines") else None
    
    for edu in educations:
        edu.pop("details", None)

    skills_str = ", ".join(skills_raw)
    skills = _split_skills(skills_str) if skills_raw else ()
    
    experience = tuple(experiences)
    education = tuple(educations)

    raw_values = {
        "name": name,
        "emails": list(dict.fromkeys(EMAIL_RE.findall(text))),
        "phones": list(dict.fromkeys(PHONE_RE.findall(text))),
        "location": location,
        "skills": skills,
        "github_url": github_url,
        "linkedin_url": linkedin_url,
        "portfolio_url": portfolio_url,
        "experience": experience,
        "projects": tuple(projects),
        "education": education,
        "experience_years": None,
        "resume_text": text,
    }
    
    return [
        PartialCandidate(
            source_name=source.name,
            source_type=source.source_type,
            name=raw_values["name"],
            emails=tuple(raw_values["emails"]),
            phones=tuple(raw_values["phones"]),
            location=raw_values["location"],
            skills=skills,
            github_url=raw_values["github_url"],
            linkedin_url=raw_values["linkedin_url"],
            portfolio_url=raw_values["portfolio_url"],
            experience=experience,
            projects=tuple(projects),
            education=education,
            experience_years=None,
            resume_text=text,
            provenance=_with_provenance(source, "resume_pdf", raw_values),
        )
    ]



PARSERS: dict[SourceType, Callable[[SourcePayload], list[PartialCandidate]]] = {
    SourceType.CSV: parse_csv,
    SourceType.ATS_JSON: parse_ats_json,
    SourceType.RESUME_PDF: parse_resume_pdf,
    SourceType.GITHUB_JSON: parse_github_json,
    SourceType.NOTES: parse_notes,
}


def parse_source(source: SourcePayload) -> list[PartialCandidate]:
    parser = PARSERS.get(source.source_type)
    if parser is None:
        raise UnsupportedSourceError(f"No parser registered for {source.source_type}")
    return parser(source)
