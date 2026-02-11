from django.db import migrations, models
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Route",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_point", django.contrib.gis.db.models.fields.PointField(geography=True, srid=4326)),
                ("end_point", django.contrib.gis.db.models.fields.PointField(geography=True, srid=4326)),
                ("geometry", django.contrib.gis.db.models.fields.LineStringField(blank=True, geography=True, null=True, srid=4326)),
                ("fuel_stops", models.JSONField(default=list, blank=True)),
                ("total_cost", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
