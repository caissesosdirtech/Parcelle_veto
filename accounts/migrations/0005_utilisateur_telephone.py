from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_utilisateur_fcm_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="utilisateur",
            name="telephone",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
    ]
