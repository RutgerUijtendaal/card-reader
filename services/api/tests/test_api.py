from fastapi.testclient import TestClient

from card_reader_api.main import app


def test_health_openapi() -> None:
    with TestClient(app) as client:
        response = client.get('/openapi.json')
    assert response.status_code == 200

def test_create_import_upload_rejects_unknown_template() -> None:
    files = [("files", ("card.png", b"fake-image-content", "image/png"))]
    with TestClient(app) as client:
        response = client.post(
            "/imports/upload",
            data={"template_id": "unknown-template", "options_json": "{}"},
            files=files,
        )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown template_id 'unknown-template'"


def test_create_import_upload_rejects_unsupported_files() -> None:
    files = [("files", ("note.txt", b"not-an-image", "text/plain"))]
    with TestClient(app) as client:
        response = client.post(
            "/imports/upload",
            data={"template_id": "mtg-like-v1", "options_json": "{}"},
            files=files,
        )
    assert response.status_code == 400
    assert response.json()["detail"] == "No supported image files found in upload"
