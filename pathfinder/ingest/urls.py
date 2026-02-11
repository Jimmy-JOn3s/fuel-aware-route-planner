from django.urls import path

from .views import IngestionDownloadView, IngestionStatusView, IngestionUploadView

urlpatterns = [
    path("upload/", IngestionUploadView.as_view(), name="ingest-upload"),
    path("status/<int:pk>/", IngestionStatusView.as_view(), name="ingest-status"),
    path("fuel-prices/", IngestionDownloadView.as_view(), name="fuel-download"),
]
