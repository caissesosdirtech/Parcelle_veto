from django.db import migrations
from django.db.models import Q

VETERINAIRE_PAR_DEFAUT = "Dr Ibrahima Pierre GUISSE"


def remplir_veterinaire(apps, schema_editor):
    """Consultations créées depuis l'app sans vétérinaire : on complète."""
    Consultation = apps.get_model("consultations", "Consultation")
    Consultation.objects.filter(
        Q(veterinaire__isnull=True) | Q(veterinaire="")
    ).update(veterinaire=VETERINAIRE_PAR_DEFAUT)


class Migration(migrations.Migration):

    dependencies = [
        ("consultations", "0005_rendezvous_consultation_origine_and_more"),
    ]

    operations = [
        migrations.RunPython(remplir_veterinaire, migrations.RunPython.noop),
    ]
