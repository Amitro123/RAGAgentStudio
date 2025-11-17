import pytest
from unittest.mock import patch, MagicMock
try:
    from fastapi.testclient import TestClient
    from main import app
except ImportError:
    TestClient = None
    app = None

client = TestClient(app) if TestClient and app else None


@patch("app.service.document_processing.rag_pipeline")
def test_upload_and_process(mock_rag_pipeline):
    """
    Test the upload-and-process endpoint.
    """
    mock_rag_pipeline.return_value = {
        "status": "success",
        "final_context": {"message": "Pipeline executed successfully"},
    }

    with open("dummy.pdf", "wb") as f:
        f.write(b"dummy content")

    with open("dummy.pdf", "rb") as f:
        response = client.post(
            "/api/v1/upload-and-process",
            data={"instructions": "test instructions"},
            files={"file": ("dummy.pdf", f, "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "processing_started"
