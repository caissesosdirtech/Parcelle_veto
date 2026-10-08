"""
Outils autour des réglages de la clinique :
lecture/écriture depuis un formulaire ou l'API, traitement du logo,
filtre des notifications et en-tête commun des PDF.
"""

from io import BytesIO

from .models import ReglagesClinique

CHAMPS_TEXTE = {
    # champ: (longueur max, obligatoire)
    "nom_clinique": (120, True),
    "sous_titre": (150, False),
    "nom_veterinaire": (120, False),
    "adresse": (200, False),
    "repere": (200, False),
    "telephones": (120, False),
    "email": (120, False),
    "slogan": (150, False),
}
CHAMPS_NOTIF = [
    ("notif_consultation_nouvelle", "Nouvelle consultation"),
    ("notif_consultation_cloturee", "Consultation clôturée"),
    ("notif_rdv", "Nouveau rendez-vous"),
    ("notif_vente", "Vente / opération en pharmacie"),
    ("notif_stock", "Alerte de stock bas"),
]
LOGO_TAILLE_MAX = 3 * 1024 * 1024  # 3 Mo avant redimensionnement
LOGO_COTE_MAX = 400                # pixels


def _vrai(valeur):
    if isinstance(valeur, bool):
        return valeur
    return str(valeur).strip().lower() in {"1", "true", "on", "oui", "yes"}


def appliquer(reglages, donnees, cases_a_cocher=True):
    """
    Met à jour les réglages à partir d'un dict (formulaire ou JSON).
    Renvoie un message d'erreur, ou None si tout est bon (les réglages
    sont alors enregistrés).

    `cases_a_cocher` : dans un formulaire HTML, une case décochée n'est pas
    envoyée du tout ; on la considère donc comme « non ». Pour l'API, seules
    les clés présentes sont modifiées.
    """
    for champ, (longueur, obligatoire) in CHAMPS_TEXTE.items():
        if champ not in donnees:
            continue
        valeur = " ".join(str(donnees.get(champ) or "").split())
        if obligatoire and not valeur:
            return "Le nom de la clinique est obligatoire."
        if len(valeur) > longueur:
            return f"« {ReglagesClinique._meta.get_field(champ).verbose_name} » : {longueur} caractères maximum."
        setattr(reglages, champ, valeur)

    if "mention_ordonnance" in donnees:
        mention = str(donnees.get("mention_ordonnance") or "").strip()
        if len(mention) > 500:
            return "La mention des ordonnances est limitée à 500 caractères."
        reglages.mention_ordonnance = mention

    if "seuil_alerte_defaut" in donnees:
        try:
            seuil = int(str(donnees.get("seuil_alerte_defaut")).strip())
        except (TypeError, ValueError):
            return "Le seuil d'alerte doit être un nombre entier."
        if not 0 <= seuil <= 10000:
            return "Le seuil d'alerte doit être compris entre 0 et 10 000."
        reglages.seuil_alerte_defaut = seuil

    for champ, _ in CHAMPS_NOTIF:
        if champ in donnees:
            setattr(reglages, champ, _vrai(donnees.get(champ)))
        elif cases_a_cocher:
            setattr(reglages, champ, False)

    reglages.save()
    return None


def preparer_logo(fichier):
    """
    Vérifie et réduit une image envoyée. Renvoie (octets_png, erreur).
    Le PNG garde la transparence ; le côté le plus long fait 400 px au plus.
    """
    from PIL import Image, UnidentifiedImageError

    if fichier.size > LOGO_TAILLE_MAX:
        return None, "Image trop lourde (3 Mo maximum)."
    try:
        image = Image.open(fichier)
        image.load()
    except (UnidentifiedImageError, OSError):
        return None, "Ce fichier n'est pas une image reconnue (PNG ou JPG)."
    if image.format not in {"PNG", "JPEG", "WEBP", "GIF"}:
        return None, "Format non pris en charge : utilisez un PNG ou un JPG."

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    image.thumbnail((LOGO_COTE_MAX, LOGO_COTE_MAX))
    sortie = BytesIO()
    image.save(sortie, format="PNG", optimize=True)
    return sortie.getvalue(), None


def enregistrer_logo(reglages, octets):
    reglages.logo = octets
    reglages.logo_version = (reglages.logo_version or 0) + 1
    reglages.save(update_fields=["logo", "logo_version", "modifie_le"])


def retirer_logo(reglages):
    reglages.logo = None
    reglages.logo_version = 0
    reglages.save(update_fields=["logo", "logo_version", "modifie_le"])


def en_dict(reglages, request=None):
    from django.urls import reverse

    donnees = {champ: getattr(reglages, champ) for champ in CHAMPS_TEXTE}
    donnees.update({
        "mention_ordonnance": reglages.mention_ordonnance,
        "seuil_alerte_defaut": reglages.seuil_alerte_defaut,
        "notifications": [
            {"cle": champ, "libelle": libelle, "actif": getattr(reglages, champ)}
            for champ, libelle in CHAMPS_NOTIF
        ],
        "logo_url": None,
        "logo_chemin": None,
    })
    if reglages.a_un_logo:
        chemin = f"{reverse('clinique_logo')}?v={reglages.logo_version}"
        donnees["logo_chemin"] = chemin
        donnees["logo_url"] = request.build_absolute_uri(chemin) if request else chemin
    return donnees


# ─────────────────────────── Notifications ───────────────────────────

def notification_autorisee(titre, data=None):
    """
    Dit si une notification doit partir vers les téléphones, d'après les
    choix faits dans Paramètres › Clinique. En cas de doute (réglages
    illisibles, type inconnu), on envoie : mieux vaut une notification de
    trop qu'une alerte perdue.
    """
    try:
        reglages = ReglagesClinique.charger()
    except Exception:
        return True

    type_ = str((data or {}).get("type") or "").lower()
    titre_min = (titre or "").lower()
    if not type_:
        if "stock" in titre_min:
            type_ = "stock"
        elif "rendez" in titre_min or "rdv" in titre_min:
            type_ = "rdv"
        elif "consultation" in titre_min:
            type_ = "consultation"
        elif "vente" in titre_min or "pharmacie" in titre_min:
            type_ = "vente"

    if type_ == "consultation":
        if "clôtur" in titre_min or "clotur" in titre_min:
            return reglages.notif_consultation_cloturee
        return reglages.notif_consultation_nouvelle
    if type_ == "rdv":
        return reglages.notif_rdv
    if type_ == "vente":
        return reglages.notif_vente
    if type_ == "stock":
        return reglages.notif_stock
    return True


# ─────────────────────────────── PDF ────────────────────────────────

def logo_reportlab(reglages, largeur_max, hauteur_max):
    """Logo prêt pour reportlab (Image de flowable), ou None."""
    if not reglages.a_un_logo:
        return None
    try:
        from PIL import Image as PILImage
        from reportlab.platypus import Image

        octets = reglages.logo
        if octets is None:  # chargé sans le logo (defer)
            octets = ReglagesClinique.charger(avec_logo=True).logo
        octets = bytes(octets)
        largeur, hauteur = PILImage.open(BytesIO(octets)).size
        echelle = min(largeur_max / largeur, hauteur_max / hauteur)
        return Image(BytesIO(octets), width=largeur * echelle, height=hauteur * echelle)
    except Exception:
        return None


def logo_canvas(canvas, reglages, x, y_haut, largeur_max, hauteur_max):
    """
    Dessine le logo sur un canvas reportlab, coin haut-gauche en (x, y_haut).
    Renvoie la largeur occupée (0 s'il n'y a pas de logo).
    """
    if not reglages.a_un_logo:
        return 0
    try:
        from PIL import Image as PILImage
        from reportlab.lib.utils import ImageReader

        octets = reglages.logo
        if octets is None:
            octets = ReglagesClinique.charger(avec_logo=True).logo
        octets = bytes(octets)
        largeur, hauteur = PILImage.open(BytesIO(octets)).size
        echelle = min(largeur_max / largeur, hauteur_max / hauteur)
        l, h = largeur * echelle, hauteur * echelle
        canvas.drawImage(ImageReader(BytesIO(octets)), x, y_haut - h, width=l, height=h, mask="auto")
        return l
    except Exception:
        return 0


def entete_html(reglages, taille_nom=16, majuscules=True):
    """
    Bloc « nom + coordonnées » au format des Paragraph de reportlab
    (les textes saisis sont échappés).
    """
    from html import escape

    nom = reglages.nom_clinique or "Parcelles Véto"
    if majuscules:
        nom = nom.upper()
    lignes = [f'<b><font size="{taille_nom}">{escape(nom)}</font></b>']
    lignes += [escape(ligne) for ligne in reglages.lignes_entete]
    return "<br/>".join(lignes)


def entete_texte(reglages):
    """Coordonnées en une ligne (en-têtes de canevas, Excel)."""
    morceaux = [reglages.adresse]
    if reglages.telephones:
        morceaux.append(f"Tél : {reglages.telephones}")
    if reglages.email:
        morceaux.append(reglages.email)
    return " · ".join(m for m in morceaux if m)
