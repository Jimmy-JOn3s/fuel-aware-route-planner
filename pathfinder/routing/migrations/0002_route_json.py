from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("routing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="route",
            name="route_json",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
