from fastapi.testclient import TestClient

from card_reader_api.main import app


def test_health_openapi() -> None:
    client = TestClient(app)
    response = client.get('/openapi.json')
    assert response.status_code == 200


def test_create_import_rejects_missing_directory() -> None:
    client = TestClient(app)
    response = client.post('/imports', json={"source_path": "C:/definitely-missing", "template_id": "mtg-like-v1", "options": {}})
    assert response.status_code == 400
