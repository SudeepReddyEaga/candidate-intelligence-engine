from candidate_transformer.domain import ProjectionConfig, SourcePayload, SourceType, TransformInput
from candidate_transformer.embeddings.provider import HashEmbeddingProvider
from candidate_transformer.pipeline import CandidateTransformer


def test_pipeline_transforms_multiple_sources() -> None:
    request = TransformInput(
        sources=[
            SourcePayload(
                source_type=SourceType.CSV,
                name="recruiter.csv",
                content=b"name,email,phone,skills\nAda Lovelace,ADA@example.com,4155550100,py;ml\n",
            ),
            SourcePayload(
                source_type=SourceType.ATS_JSON,
                name="ats.json",
                content=(
                    b'{"candidate":{"full_name":"Ada Byron Lovelace",'
                    b'"email":"ada@example.com","skills":["k8s"]}}'
                ),
            ),
            SourcePayload(
                source_type=SourceType.NOTES,
                name="notes.txt",
                content=b"Preferred email is ada@example.com. Strong PyTorch.",
            ),
        ],
        projection=ProjectionConfig(include_provenance=True, include_confidence=True),
    )
    result = CandidateTransformer(HashEmbeddingProvider()).transform(request)
    candidate = result["candidates"][0]
    assert candidate["emails"] == ["ada@example.com"]
    assert sorted(s["name"] for s in candidate["skills"]) == ["Kubernetes", "Machine Learning", "Python"]
    assert candidate["overall_confidence"] > 0
    assert result["metrics"]["pipeline_duration_ms"] >= 0
