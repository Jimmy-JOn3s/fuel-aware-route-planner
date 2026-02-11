from unittest.mock import Mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from ingest.models import Ingestion


@pytest.mark.django_db
def test_ingest_upload_requires_file():
    client = APIClient()
    response = client.post("/api/ingest/upload/", data={}, format="multipart")

    assert response.status_code == 400
    assert response.json()["detail"] == "file is required"


@pytest.mark.django_db
def test_ingest_upload_queues_task(monkeypatch):
    delay_mock = Mock()
    monkeypatch.setattr("ingest.views.ingest_csv.delay", delay_mock)

    upload = SimpleUploadedFile(
        "fuel.csv",
        b"OPIS Truckstop ID,Truckstop Name,Address,City,State,Retail Price\n1,Demo,1 Main,New York,NY,3.111\n",
        content_type="text/csv",
    )
    client = APIClient()
    response = client.post("/api/ingest/upload/", data={"file": upload}, format="multipart")

    assert response.status_code == 200
    ingestion = Ingestion.objects.get(id=response.json()["ingestion_id"])
    assert ingestion.status == Ingestion.Status.PENDING

    delay_mock.assert_called_once()
    queued_ingestion_id, queued_path = delay_mock.call_args.args
    assert queued_ingestion_id == ingestion.id
    assert queued_path.startswith("/app/tmp_ingest/ingest_")


@pytest.mark.django_db
def test_ingest_status_returns_payload():
    ingestion = Ingestion.objects.create(source="upload", status=Ingestion.Status.SUCCESS)
    client = APIClient()

    response = client.get(f"/api/ingest/status/{ingestion.id}/")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == ingestion.id
    assert body["status"] == Ingestion.Status.SUCCESS


@pytest.mark.django_db
def test_bdd_given_missing_file_when_upload_called_then_returns_400():
    # Given: ingest API is available.
    client = APIClient()

    # When: upload is called without multipart "file".
    response = client.post("/api/ingest/upload/", data={}, format="multipart")

    # Then: request is rejected with clear validation error.
    assert response.status_code == 400
    assert response.json()["detail"] == "file is required"
