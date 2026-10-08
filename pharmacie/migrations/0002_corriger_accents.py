"""
Corrige les noms dont les accents avaient été abîmés (caractère « � »)
lors du premier chargement du catalogue : médicaments, familles, fournisseur.
Seuls les noms encore abîmés sont modifiés ; un nom corrigé à la main
entre-temps n'est pas touché.
"""

from django.db import migrations

REMPLACEMENTS = {
    "Thi�s": "Thiès",
    "S�n�gal": "Sénégal",
    "Compl�ments": "Compléments",
    "D�sinfectants": "Désinfectants",
    "H�patoprotecteurs": "Hépatoprotecteurs",
    "R�gulateurs": "Régulateurs",
    "Oxyt�tracycline": "Oxytétracycline",
    "�rythromycine": "Érythromycine",
    "Cyperm�thrine": "Cyperméthrine",
    "Perm�thrine": "Perméthrine",
    "Cr�syl": "Crésyl",
    "v�t�rinaire": "vétérinaire",
    "Glutarald�hyde": "Glutaraldéhyde",
    "concentr�e": "concentrée",
    "�lectrolytes": "Électrolytes",
    "multivitamin�": "multivitaminé",
    "M�thionine": "Méthionine",
    "Pr�biotiques": "Prébiotiques",
    "amin�s": "aminés",
    "M�loxicam": "Méloxicam",
}


def _corriger(texte):
    for abime, correct in REMPLACEMENTS.items():
        texte = texte.replace(abime, correct)
    return texte


def corriger_accents(apps, schema_editor):
    cibles = [
        ("pharmacie", "CatalogueMedicament", ["nom"]),
        ("pharmacie", "FamilleMedicament", ["nom"]),
        ("fournisseurs", "Fournisseur", ["nom", "adresse"]),
    ]
    for app, modele, champs in cibles:
        Modele = apps.get_model(app, modele)
        for obj in Modele.objects.all():
            modifies = []
            for champ in champs:
                valeur = getattr(obj, champ, None)
                if isinstance(valeur, str) and "�" in valeur:
                    setattr(obj, champ, _corriger(valeur))
                    modifies.append(champ)
            if modifies:
                obj.save(update_fields=modifies)


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacie", "0001_initial"),
        ("fournisseurs", "0003_alter_fournisseur_id"),
    ]

    operations = [
        migrations.RunPython(corriger_accents, migrations.RunPython.noop),
    ]
