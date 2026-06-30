from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from candidate_transformer.domain import PartialCandidate
from candidate_transformer.embeddings.provider import EmbeddingProvider, cosine_similarity


@dataclass(frozen=True)
class MatchExplanation:
    score: float
    reasons: tuple[str, ...]


def _candidate_text(candidate: PartialCandidate) -> str:
    parts = [
        candidate.name or "",
        " ".join(candidate.emails),
        " ".join(candidate.skills),
        candidate.location or "",
        candidate.github_url or "",
    ]
    return " ".join(part for part in parts if part)


class EntityResolver:
    def __init__(self, embeddings: EmbeddingProvider, threshold: float = 0.78) -> None:
        self.embeddings = embeddings
        self.threshold = threshold

    def score(self, left: PartialCandidate, right: PartialCandidate) -> MatchExplanation:
        reasons: list[str] = []
        scores: list[float] = []

        if set(left.emails) & set(right.emails):
            scores.append(1.0)
            reasons.append("shared normalized email")
        if set(left.phones) & set(right.phones):
            scores.append(0.95)
            reasons.append("shared normalized phone")
        if left.github_url and left.github_url == right.github_url:
            scores.append(0.95)
            reasons.append("shared GitHub URL")
        if left.name and right.name:
            name_score = fuzz.token_sort_ratio(left.name, right.name) / 100.0
            scores.append(name_score * 0.75)
            reasons.append(f"name fuzzy score {name_score:.2f}")
        semantic_vectors = self.embeddings.encode([_candidate_text(left), _candidate_text(right)])
        semantic_score = cosine_similarity(semantic_vectors[0], semantic_vectors[1])
        scores.append(semantic_score * 0.70)
        reasons.append(f"semantic score {semantic_score:.2f}")

        return MatchExplanation(score=max(scores) if scores else 0.0, reasons=tuple(reasons))

    def cluster(self, candidates: list[PartialCandidate]) -> list[list[PartialCandidate]]:
        clusters: list[list[PartialCandidate]] = []
        for candidate in candidates:
            placed = False
            for cluster in clusters:
                if any(
                    self.score(candidate, existing).score >= self.threshold for existing in cluster
                ):
                    cluster.append(candidate)
                    placed = True
                    break
            if not placed:
                clusters.append([candidate])
        return clusters
