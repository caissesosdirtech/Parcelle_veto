"""
Règles communes aux pages web et à l'API de l'app mobile pour la gestion
des comptes : qui peut gérer, validation des champs, garde-fous.
"""

from django.contrib.auth import get_user_model

Utilisateur = get_user_model()

ROLES = [code for code, _ in Utilisateur.ROLE_CHOICES]
LONGUEUR_MIN_MDP = 8


def est_docteur(user):
    """Seul le docteur (ou le super-administrateur) gère les comptes."""
    return bool(
        user and user.is_authenticated
        and (user.is_superuser or getattr(user, "role", None) == "DOCTEUR")
    )


def peut_gerer(acteur, cible):
    """Un docteur ne touche pas aux comptes super-administrateur."""
    return est_docteur(acteur) and (acteur.is_superuser or not cible.is_superuser)


def verifier_mot_de_passe(mdp, confirmation=None):
    if not mdp or len(mdp) < LONGUEUR_MIN_MDP:
        return f"Le mot de passe doit contenir au moins {LONGUEUR_MIN_MDP} caractères."
    if mdp.isdigit():
        return "Le mot de passe ne doit pas contenir uniquement des chiffres."
    if confirmation is not None and mdp != confirmation:
        return "Les deux mots de passe ne correspondent pas."
    return None


def nettoyer(donnees, creation=False, cible=None):
    """
    Valide les champs d'un compte. Retourne (champs, erreur).
    `donnees` : dict venant d'un formulaire ou d'un JSON.
    """
    champs = {
        "first_name": str(donnees.get("first_name", "")).strip(),
        "last_name": str(donnees.get("last_name", "")).strip(),
        "telephone": str(donnees.get("telephone", "")).strip(),
        "role": str(donnees.get("role", "")).strip().upper(),
    }
    if not champs["first_name"] and not champs["last_name"]:
        return None, "Indiquez au moins le prénom ou le nom."
    if champs["role"] not in ROLES:
        return None, "Choisissez un rôle : Docteur, Assistant ou Pharmacien."

    if creation:
        username = str(donnees.get("username", "")).strip()
        if not username or " " in username:
            return None, "L'identifiant est obligatoire et ne doit pas contenir d'espace."
        if Utilisateur.objects.filter(username__iexact=username).exists():
            return None, f"L'identifiant « {username} » est déjà utilisé."
        champs["username"] = username
        erreur = verifier_mot_de_passe(str(donnees.get("password", "")))
        if erreur:
            return None, erreur
        champs["password"] = str(donnees.get("password", ""))
    return champs, None


def changer_mot_de_passe(cible, mdp, auteur):
    """
    Change le mot de passe de `cible` et note qui l'a fait et quand.
    Si un membre de l'équipe (autre que le docteur) change lui-même son mot
    de passe, le docteur est prévenu. Le mot de passe n'est jamais transmis.
    """
    from django.utils import timezone

    cible.set_password(mdp)
    cible.mdp_change_le = timezone.now()
    cible.mdp_change_par = auteur
    cible.save(update_fields=["password", "mdp_change_le", "mdp_change_par"])

    if auteur.pk == cible.pk and not est_docteur(cible):
        try:
            from notifications.firebase_utils import notify_all_docteurs
            notify_all_docteurs(
                title="🔑 Mot de passe changé",
                body=f"{cible.get_full_name() or cible.username} ({cible.libelle_role}) "
                     f"a changé son mot de passe le {timezone.localtime(cible.mdp_change_le):%d/%m/%Y à %H:%M}.",
                data={"type": "compte", "id": str(cible.pk)},
            )
        except Exception:
            pass  # une notification ratée ne doit pas bloquer le changement


def creer(champs):
    mdp = champs.pop("password")
    user = Utilisateur(**champs)
    user.set_password(mdp)
    user.save()
    return user


def modifier(acteur, cible, champs):
    """Applique les changements ; le docteur ne peut pas changer son propre rôle."""
    if cible.pk == acteur.pk and champs["role"] != (cible.role or ""):
        if not acteur.is_superuser:
            return "Vous ne pouvez pas modifier votre propre rôle."
    for cle in ("first_name", "last_name", "telephone", "role"):
        setattr(cible, cle, champs[cle])
    cible.save(update_fields=["first_name", "last_name", "telephone", "role"])
    return None


def basculer_actif(acteur, cible):
    if cible.pk == acteur.pk:
        return "Vous ne pouvez pas désactiver votre propre compte."
    cible.is_active = not cible.is_active
    cible.save(update_fields=["is_active"])
    return None


def en_dict(u):
    return {
        "id": u.id,
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "nom_complet": u.get_full_name() or u.username,
        "telephone": getattr(u, "telephone", "") or "",
        "role": u.role or "",
        "role_libelle": u.libelle_role,
        "is_active": u.is_active,
        "is_superuser": u.is_superuser,
        "derniere_connexion": u.last_login.isoformat() if u.last_login else None,
        "mdp_change_le": u.mdp_change_le.isoformat() if u.mdp_change_le else None,
        "mdp_change_par": _auteur_mdp(u),
    }


def _auteur_mdp(u):
    """« lui-même », le nom de l'auteur, ou None si jamais changé."""
    if not u.mdp_change_le:
        return None
    if u.mdp_change_par_id == u.pk:
        return "lui-même"
    if u.mdp_change_par is None:
        return "—"
    return u.mdp_change_par.get_full_name() or u.mdp_change_par.username
