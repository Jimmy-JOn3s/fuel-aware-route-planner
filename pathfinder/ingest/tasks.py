import csv
from decimal import Decimal
from typing import Iterable

from celery import shared_task
from django.contrib.gis.geos import Point
from django.conf import settings

from pathfinder.geocode import geocode_address

from .models import FuelStation, Ingestion
import logging
import time

logger = logging.getLogger(__name__)

def parse_price(value: str) -> Decimal:
    return Decimal(value).quantize(Decimal("0.001"))


def read_rows(path: str) -> Iterable[dict]:
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


@shared_task
def ingest_csv(ingestion_id: int, path: str) -> None:
    ingestion = Ingestion.objects.get(id=ingestion_id)
    ingestion.status = Ingestion.Status.PROCESSING
    ingestion.save(update_fields=["status"])
    logger.info("Ingestion %s: started", ingestion.id)

    try:
        processed = 0
        for row in read_rows(path):
            address = row.get("Address", "")
            city = row.get("City", "")
            state = row.get("State", "")
            opis_id = row.get("OPIS Truckstop ID", "")
            name = row.get("Truckstop Name", "")
            price = parse_price(row.get("Retail Price", "0"))
            full_address = f"{address}, {city}, {state}"
            geom = None
            if getattr(settings, "INGEST_GEOCODE", False):
                coords = geocode_address(full_address)
                geom = Point(coords[0], coords[1]) if coords else None

            FuelStation.objects.update_or_create(
                opis_id=opis_id,
                state=state,
                defaults={
                    "name": name,
                    "address": address,
                    "city": city,
                    "price": price,
                    "geom": geom,
                },
            )
            processed += 1
            if processed % 500 == 0:
                logger.info("Ingestion %s: processed %s rows", ingestion.id, processed)
                # gentle throttle to avoid hammering provider; ~20 qps
                time.sleep(0.1)
        ingestion.mark_success()
        logger.info("Ingestion %s: completed (%s rows)", ingestion.id, processed)
    except Exception as exc:  # pragma: no cover - logged via celery
        ingestion.mark_failed(str(exc))
        logger.exception("Ingestion %s: failed: %s", ingestion.id, exc)
        raise


@shared_task
def geocode_pending(batch_size: int = 5000) -> int:
    """
    Geocode stations with null geom up to batch_size.
    Returns number geocoded.
    """
    to_process = list(
        FuelStation.objects.filter(geom__isnull=True).values("id", "address", "city", "state")[:batch_size]
    )
    updated = 0
    for row in to_process:
        full_address = f"{row['address']}, {row['city']}, {row['state']}"
        coords = geocode_address(full_address)
        if coords:
            FuelStation.objects.filter(id=row["id"]).update(geom=Point(coords[0], coords[1]))
            updated += 1
    logger.info("geocode_pending: updated %s stations (batch_size=%s)", updated, batch_size)
    return updated
