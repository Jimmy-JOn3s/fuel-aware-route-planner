import tempfile
from typing import Any
from pathlib import Path

from django.http import FileResponse, HttpRequest
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ingestion
from .serializers import IngestionSerializer
from .tasks import ingest_csv
import logging

logger = logging.getLogger(__name__)


class IngestionUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

        ingestion = Ingestion.objects.create(source="upload")
        logger.info("Ingestion %s: received upload %s (%s bytes)", ingestion.id, upload.name, upload.size)

        shared_dir = Path("/app/tmp_ingest")
        shared_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = shared_dir / f"ingest_{ingestion.id}_{upload.name}"
        with open(tmp_path, "wb") as tmp:
            for chunk in upload.chunks():
                tmp.write(chunk)

        ingest_csv.delay(ingestion.id, tmp_path.as_posix())
        logger.info("Ingestion %s: queued Celery task with temp file %s", ingestion.id, str(tmp_path))
        return Response({"ingestion_id": ingestion.id, "status": ingestion.status})


class IngestionStatusView(APIView):
    def get(self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any) -> Response:
        ingestion = Ingestion.objects.get(pk=pk)
        return Response(IngestionSerializer(ingestion).data)


class IngestionDownloadView(APIView):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> FileResponse:
        response = FileResponse(open("fuel-prices-for-be-assessment.csv", "rb"))
        response["Content-Disposition"] = "attachment; filename=fuel-prices.csv"
        return response
