from candidate_transformer.domain import ProjectionConfig, SourcePayload, SourceType, TransformInput
from candidate_transformer.embeddings.provider import HashEmbeddingProvider
from candidate_transformer.pipeline import CandidateTransformer


def test_golden_projection_output_is_stable() -> None:
    request = TransformInput(
        sources=[
            SourcePayload(
                source_type=SourceType.CSV,
                name="recruiter.csv",
                content=b"name,email,skills\nAda Lovelace,ADA@example.com,py;ml;k8s\n",
            )
        ],
        projection=ProjectionConfig(
            include_confidence=True,
            include_provenance=True,
        ),
    )
    result = CandidateTransformer(HashEmbeddingProvider()).transform(request)
    
    # Sort skills by name to ensure stable comparison
    result["candidates"][0]["skills"].sort(key=lambda x: x["name"])
    
    assert result["candidates"] == [
        {
            "candidate_id": "cand_2321c9e55c9f233a",
            "full_name": "Ada Lovelace",
            "emails": ["ada@example.com"],
            "phones": [],
            "location": {"city": None, "region": None, "country": None},
            "links": {"linkedin": None, "github": None, "portfolio": None, "other": []},
            "headline": None,
            "years_experience": None,
            "skills": [
                {"name": "Kubernetes", "confidence": 0.67, "sources": ["recruiter.csv"]},
                {"name": "Machine Learning", "confidence": 0.67, "sources": ["recruiter.csv"]},
                {"name": "Python", "confidence": 0.67, "sources": ["recruiter.csv"]}
            ],
            "experience": [],
            "education": [],
            "provenance": [
                {"field": "name", "source": "recruiter.csv", "method": "csv"},
                {"field": "emails", "source": "recruiter.csv", "method": "csv"},
                {"field": "skills", "source": "recruiter.csv", "method": "csv"},
            ],
            "overall_confidence": 0.335
        }
    ]
