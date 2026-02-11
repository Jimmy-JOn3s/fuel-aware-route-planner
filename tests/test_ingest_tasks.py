import pytest

from ingest.models import FuelStation, Ingestion
from ingest.tasks import ingest_csv, parse_price


def test_parse_price_quantizes_to_three_decimals():
    assert str(parse_price("3.1")) == "3.100"
    assert str(parse_price("3.1234")) == "3.123"


@pytest.mark.django_db
def test_ingest_csv_happy_path(tmp_path):
    csv_path = tmp_path / "stations.csv"
    csv_path.write_text(
        "OPIS Truckstop ID,Truckstop Name,Address,City,State,Retail Price\n"
        "1,Demo One,1 Main St,New York,NY,3.111\n",
        encoding="utf-8",
    )
    ingestion = Ingestion.objects.create(source="upload")

    ingest_csv(ingestion.id, str(csv_path))

    ingestion.refresh_from_db()
    assert ingestion.status == Ingestion.Status.SUCCESS
    station = FuelStation.objects.get(opis_id="1", state="NY")
    assert station.name == "Demo One"
    assert str(station.price) == "3.111"


@pytest.mark.django_db
def test_ingest_csv_failure_marks_ingestion_failed(tmp_path):
    csv_path = tmp_path / "bad_stations.csv"
    csv_path.write_text(
        "OPIS Truckstop ID,Truckstop Name,Address,City,State,Retail Price\n"
        "1,Bad Price,1 Main St,New York,NY,not-a-number\n",
        encoding="utf-8",
    )
    ingestion = Ingestion.objects.create(source="upload")

    with pytest.raises(Exception):
        ingest_csv(ingestion.id, str(csv_path))

    ingestion.refresh_from_db()
    assert ingestion.status == Ingestion.Status.FAILED
    assert "not-a-number" in ingestion.error_message
