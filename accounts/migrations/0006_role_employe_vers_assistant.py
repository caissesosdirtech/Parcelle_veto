from django.db import migrations


def employe_vers_assistant(apps, schema_editor):
    """
    Anciens comptes créés avec le rôle « EMPLOYE », qui n'existe plus dans
    la liste des rôles : ils deviennent « ASSISTANT » (Employé / Assistant).
    """
    Utilisateur = apps.get_model("accounts", "Utilisateur")
    Utilisateur.objects.filter(role__iexact="EMPLOYE").update(role="ASSISTANT")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_utilisateur_telephone"),
    ]

    operations = [
        migrations.RunPython(employe_vers_assistant, migrations.RunPython.noop),
    ]
