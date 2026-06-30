from __future__ import annotations

import logging
from typing import Any

from candidate_transformer.confidence.scorer import calculate_confidence
from candidate_transformer.domain import PartialCandidate, SourcePayload, TransformInput
from candidate_transformer.embeddings.provider import EmbeddingProvider, create_embedding_provider
from candidate_transformer.entity_resolution.resolver import EntityResolver
from candidate_transformer.extraction.parsers import parse_source
from candidate_transformer.merge.merger import merge_candidates
from candidate_transformer.normalization.normalizer import normalize_partial
from candidate_transformer.projection.projector import project_record
from candidate_transformer.utils.errors import CandidateTransformerError
from candidate_transformer.utils.timing import measure_ms
from candidate_transformer.validation.json_schema import CandidateValidator

LOGGER = logging.getLogger(__name__)


class CandidateTransformer:
    def __init__(
        self,
        embeddings: EmbeddingProvider | None = None,
        validator: CandidateValidator | None = None,
    ) -> None:
        self.embeddings = embeddings or create_embedding_provider()
        self.validator = validator or CandidateValidator()

    def transform(self, request: TransformInput) -> dict[str, Any]:
        metrics: dict[str, float] = {}
        with measure_ms(metrics, "pipeline_duration_ms"):
            with measure_ms(metrics, "parsing_time_ms"):
                partials = self._parse(request.sources)
            with measure_ms(metrics, "normalization_time_ms"):
                normalized = [normalize_partial(partial) for partial in partials]
            with measure_ms(metrics, "merge_time_ms"):
                clusters = EntityResolver(self.embeddings).cluster(normalized)
                records = [merge_candidates(cluster) for cluster in clusters]
            with measure_ms(metrics, "confidence_time_ms"):
                for record in records:
                    record.confidence = calculate_confidence(record)
            outputs = []
            validation_failures = 0
            for record in records:
                projected = project_record(record, request.projection)
                try:
                    self.validator.validate(projected)
                except CandidateTransformerError:
                    validation_failures += 1
                    raise
                outputs.append(projected)
            metrics["validation_failures"] = float(validation_failures)
        LOGGER.info(
            "candidate_transform_complete", extra={f"metric_{k}": v for k, v in metrics.items()}
        )
        return {"candidates": outputs, "metrics": metrics}

    @staticmethod
    def _parse(sources: list[SourcePayload]) -> list[PartialCandidate]:
        partials = []
        for source in sources:
            partials.extend(parse_source(source))
        return partials
