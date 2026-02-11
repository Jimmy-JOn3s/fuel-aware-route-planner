from django.contrib.gis.db import models
from django.utils import timezone


class Ingestion(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    source = models.CharField(max_length=64, default="upload")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    meta = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    def mark_success(self) -> None:
        self.status = self.Status.SUCCESS
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

    def mark_failed(self, message: str) -> None:
        self.status = self.Status.FAILED
        self.error_message = message
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "error_message", "finished_at"])


class FuelStation(models.Model):
    opis_id = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=32)
    price = models.DecimalField(max_digits=6, decimal_places=3)
    geom = models.PointField(geography=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("opis_id", "state")
        indexes = [
            models.Index(fields=["state"]),
            models.Index(fields=["price"]),
            models.Index(fields=["geom"], name="fuelstation_geom_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.name} ({self.state})"
