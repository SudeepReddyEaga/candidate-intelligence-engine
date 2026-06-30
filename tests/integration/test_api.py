from fastapi.testclient import TestClient

from candidate_transformer.api.app import create_app


def test_api_transform() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/transform",
        files={
            "csv": (
                "recruiter.csv",
                b"name,email,skills\nAda Lovelace,ada@example.com,python\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["candidates"][0]["emails"] == ["ada@example.com"]


def test_api_rejects_empty_request() -> None:
    client = TestClient(create_app())
    response = client.post("/transform")
    assert response.status_code == 400
