"""
Rubrique Paramètres : Utilisateurs, Clinique et Mon compte.

Pages web (session) et API JSON pour l'app mobile (jeton JWT).
La gestion des comptes est réservée au docteur ; « Mon compte » est
ouvert à tout utilisateur connecté.
"""

import json
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from . import clinique as reglages_clinique
from . import services
from .models import ReglagesClinique

Utilisateur = get_user_model()


# ═══════════════════════════════ PAGES WEB ═══════════════════════════════

def docteur_requis(vue):
    @wraps(vue)
    @login_required
    def enveloppe(request, *args, **kwargs):
        if not services.est_docteur(request.user):
            messages.error(request, "Cette rubrique est réservée au docteur.")
            return redirect("mon_compte")
        return vue(request, *args, **kwargs)
    return enveloppe


@docteur_requis
def utilisateurs_liste(request):
    utilisateurs = Utilisateur.objects.order_by("-is_active", "role", "first_name", "username")
    if not request.user.is_superuser:
        utilisateurs = utilisateurs.filter(is_superuser=False) | Utilisateur.objects.filter(pk=request.user.pk)
    utilisateurs = utilisateurs.distinct().order_by("-is_active", "role", "first_name", "username")
    return render(request, "parametres/utilisateurs.html", {
        "utilisateurs": utilisateurs,
        "nb_actifs": sum(1 for u in utilisateurs if u.is_active),
        "active_page": "parametres",
        "onglet": "utilisateurs",
        "longueur_min": services.LONGUEUR_MIN_MDP,
    })


@docteur_requis
def utilisateur_formulaire(request, user_id=None):
    cible = get_object_or_404(Utilisateur, pk=user_id) if user_id else None
    if cible and not services.peut_gerer(request.user, cible):
        messages.error(request, "Ce compte ne peut pas être modifié ici.")
        return redirect("utilisateurs_liste")

    valeurs = request.POST if request.method == "POST" else None
    if request.method == "POST":
        champs, erreur = services.nettoyer(request.POST, creation=cible is None, cible=cible)
        if not erreur and request.POST.get("password") and cible is None:
            erreur = services.verifier_mot_de_passe(
                request.POST.get("password"), request.POST.get("password2", "")
            )
        if not erreur:
            if cible is None:
                nouveau = services.creer(champs)
                messages.success(request, f"Compte de {nouveau.get_full_name() or nouveau.username} créé.")
                return redirect("utilisateurs_liste")
            erreur = services.modifier(request.user, cible, champs)
            if not erreur:
                messages.success(request, f"Compte de {cible.get_full_name() or cible.username} mis à jour.")
                return redirect("utilisateurs_liste")
        messages.error(request, erreur)

    return render(request, "parametres/utilisateur_form.html", {
        "cible": cible,
        "valeurs": valeurs,
        "role_courant": (valeurs.get("role") if valeurs else None) or (cible.role if cible else ""),
        "roles": Utilisateur.ROLE_CHOICES,
        "est_moi": bool(cible and cible.pk == request.user.pk),
        "active_page": "parametres",
        "onglet": "utilisateurs",
        "longueur_min": services.LONGUEUR_MIN_MDP,
    })


@docteur_requis
@require_POST
def utilisateur_mot_de_passe(request, user_id):
    cible = get_object_or_404(Utilisateur, pk=user_id)
    if not services.peut_gerer(request.user, cible):
        messages.error(request, "Ce compte ne peut pas être modifié ici.")
        return redirect("utilisateurs_liste")
    mdp = request.POST.get("password", "")
    erreur = services.verifier_mot_de_passe(mdp, request.POST.get("password2", ""))
    if erreur:
        messages.error(request, erreur)
    else:
        cible.set_password(mdp)
        cible.save(update_fields=["password"])
        if cible.pk == request.user.pk:
            update_session_auth_hash(request, cible)
        messages.success(
            request,
            f"Nouveau mot de passe enregistré pour {cible.get_full_name() or cible.username}. "
            "Communiquez-le-lui : il pourra le changer dans « Mon compte ».",
        )
    return redirect("utilisateurs_liste")


@docteur_requis
@require_POST
def utilisateur_activer(request, user_id):
    cible = get_object_or_404(Utilisateur, pk=user_id)
    if not services.peut_gerer(request.user, cible):
        messages.error(request, "Ce compte ne peut pas être modifié ici.")
        return redirect("utilisateurs_liste")
    erreur = services.basculer_actif(request.user, cible)
    if erreur:
        messages.error(request, erreur)
    else:
        etat = "réactivé" if cible.is_active else "désactivé"
        messages.success(request, f"Compte de {cible.get_full_name() or cible.username} {etat}.")
    return redirect("utilisateurs_liste")


@docteur_requis
def clinique(request):
    reglages = ReglagesClinique.charger()
    if request.method == "POST":
        action = request.POST.get("action", "infos")
        if action == "logo":
            fichier = request.FILES.get("logo")
            if not fichier:
                messages.error(request, "Choisissez d'abord une image.")
            else:
                octets, erreur = reglages_clinique.preparer_logo(fichier)
                if erreur:
                    messages.error(request, erreur)
                else:
                    reglages_clinique.enregistrer_logo(reglages, octets)
                    messages.success(request, "Logo mis à jour.")
            return redirect("clinique")
        if action == "retirer_logo":
            reglages_clinique.retirer_logo(reglages)
            messages.success(request, "Logo retiré.")
            return redirect("clinique")

        erreur = reglages_clinique.appliquer(reglages, request.POST.dict(), cases_a_cocher=True)
        if erreur:
            messages.error(request, erreur)
        else:
            message = "Réglages de la clinique enregistrés."
            if request.POST.get("appliquer_seuil_a_tous"):
                from pharmacie.models import Medicament
                nb = Medicament.objects.update(seuil_alerte=reglages.seuil_alerte_defaut)
                message += f" Seuil appliqué à {nb} médicament(s)."
            messages.success(request, message)
            return redirect("clinique")

    return render(request, "parametres/clinique.html", {
        "reglages": reglages,
        "champs_notif": [
            (champ, libelle, getattr(reglages, champ))
            for champ, libelle in reglages_clinique.CHAMPS_NOTIF
        ],
        "active_page": "parametres",
        "onglet": "clinique",
    })


def clinique_logo(request):
    """Logo de la clinique (public : il s'affiche aussi sur la page de connexion)."""
    reglages = ReglagesClinique.charger(avec_logo=True)
    if not reglages.logo:
        return HttpResponse(status=404)
    reponse = HttpResponse(bytes(reglages.logo), content_type="image/png")
    reponse["Cache-Control"] = "public, max-age=86400"
    return reponse


@login_required
def mon_compte(request):
    user = request.user
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "profil":
            user.first_name = request.POST.get("first_name", "").strip()
            user.last_name = request.POST.get("last_name", "").strip()
            user.telephone = request.POST.get("telephone", "").strip()
            user.save(update_fields=["first_name", "last_name", "telephone"])
            messages.success(request, "Vos informations ont été mises à jour.")
        elif action == "mot_de_passe":
            if not user.check_password(request.POST.get("ancien", "")):
                messages.error(request, "Le mot de passe actuel est incorrect.")
            else:
                erreur = services.verifier_mot_de_passe(
                    request.POST.get("password", ""), request.POST.get("password2", "")
                )
                if erreur:
                    messages.error(request, erreur)
                else:
                    user.set_password(request.POST["password"])
                    user.save(update_fields=["password"])
                    update_session_auth_hash(request, user)  # reste connecté
                    messages.success(request, "Votre mot de passe a été changé.")
        return redirect("mon_compte")

    return render(request, "parametres/mon_compte.html", {
        "active_page": "mon_compte",
        "onglet": "mon_compte",
        "longueur_min": services.LONGUEUR_MIN_MDP,
    })


# ═══════════════════════════════ API MOBILE ═══════════════════════════════
# Réservée aux appels portant un jeton JWT : un en-tête Authorization ne
# peut pas être ajouté par un site tiers, ce qui protège ces vues CSRF-exempt.

def _api(docteur=False):
    def decorateur(vue):
        @wraps(vue)
        @csrf_exempt
        def enveloppe(request, *args, **kwargs):
            if not request.headers.get("Authorization", "").startswith("Bearer ") \
                    or not request.user.is_authenticated:
                return JsonResponse({"error": "Authentification requise."}, status=401)
            if docteur and not services.est_docteur(request.user):
                return JsonResponse({"error": "Réservé au docteur."}, status=403)
            request.donnees = {}
            if request.method == "POST":
                if "application/json" in (request.content_type or ""):
                    try:
                        request.donnees = json.loads(request.body or b"{}")
                    except json.JSONDecodeError:
                        return JsonResponse({"error": "Données invalides."}, status=400)
                else:
                    request.donnees = request.POST.dict()
            return vue(request, *args, **kwargs)
        return enveloppe
    return decorateur


@_api(docteur=True)
@require_http_methods(["GET", "POST"])
def api_utilisateurs(request):
    if request.method == "GET":
        qs = Utilisateur.objects.order_by("-is_active", "role", "first_name", "username")
        if not request.user.is_superuser:
            qs = qs.exclude(is_superuser=True) | Utilisateur.objects.filter(pk=request.user.pk)
        return JsonResponse({
            "moi": request.user.pk,
            "roles": [{"code": c, "libelle": l} for c, l in Utilisateur.ROLE_CHOICES],
            "utilisateurs": [services.en_dict(u) for u in qs.distinct().order_by("-is_active", "role", "first_name")],
        })
    champs, erreur = services.nettoyer(request.donnees, creation=True)
    if erreur:
        return JsonResponse({"error": erreur}, status=400)
    user = services.creer(champs)
    return JsonResponse({"message": "Compte créé.", "utilisateur": services.en_dict(user)}, status=201)


def _cible(request, user_id):
    cible = Utilisateur.objects.filter(pk=user_id).first()
    if cible is None:
        return None, JsonResponse({"error": "Utilisateur introuvable."}, status=404)
    if not services.peut_gerer(request.user, cible):
        return None, JsonResponse({"error": "Ce compte ne peut pas être modifié."}, status=403)
    return cible, None


@_api(docteur=True)
@require_POST
def api_utilisateur_modifier(request, user_id):
    cible, refus = _cible(request, user_id)
    if refus:
        return refus
    champs, erreur = services.nettoyer(request.donnees)
    erreur = erreur or services.modifier(request.user, cible, champs)
    if erreur:
        return JsonResponse({"error": erreur}, status=400)
    return JsonResponse({"message": "Compte mis à jour.", "utilisateur": services.en_dict(cible)})


@_api(docteur=True)
@require_POST
def api_utilisateur_mot_de_passe(request, user_id):
    cible, refus = _cible(request, user_id)
    if refus:
        return refus
    mdp = str(request.donnees.get("password", ""))
    erreur = services.verifier_mot_de_passe(mdp)
    if erreur:
        return JsonResponse({"error": erreur}, status=400)
    cible.set_password(mdp)
    cible.save(update_fields=["password"])
    return JsonResponse({"message": "Mot de passe réinitialisé."})


@_api(docteur=True)
@require_POST
def api_utilisateur_activer(request, user_id):
    cible, refus = _cible(request, user_id)
    if refus:
        return refus
    erreur = services.basculer_actif(request.user, cible)
    if erreur:
        return JsonResponse({"error": erreur}, status=400)
    return JsonResponse({
        "message": "Compte réactivé." if cible.is_active else "Compte désactivé.",
        "utilisateur": services.en_dict(cible),
    })


@_api()
@require_http_methods(["GET", "POST"])
def api_mon_compte(request):
    user = request.user
    if request.method == "POST":
        d = request.donnees
        user.first_name = str(d.get("first_name", user.first_name)).strip()
        user.last_name = str(d.get("last_name", user.last_name)).strip()
        user.telephone = str(d.get("telephone", user.telephone)).strip()
        user.save(update_fields=["first_name", "last_name", "telephone"])
    return JsonResponse({"utilisateur": services.en_dict(user)})


@_api()
@require_POST
def api_mon_mot_de_passe(request):
    user = request.user
    if not user.check_password(str(request.donnees.get("ancien", ""))):
        return JsonResponse({"error": "Le mot de passe actuel est incorrect."}, status=400)
    mdp = str(request.donnees.get("password", ""))
    erreur = services.verifier_mot_de_passe(mdp)
    if erreur:
        return JsonResponse({"error": erreur}, status=400)
    user.set_password(mdp)
    user.save(update_fields=["password"])
    return JsonResponse({"message": "Votre mot de passe a été changé."})


@_api()
@require_http_methods(["GET", "POST"])
def api_clinique(request):
    """
    GET : réglages de la clinique (lecture ouverte à tout le personnel,
    l'app s'en sert pour ses en-têtes).
    POST : modification, réservée au docteur. Seules les clés envoyées
    changent. Un fichier « logo » (multipart) remplace le logo ;
    « retirer_logo » = true le supprime.
    """
    reglages = ReglagesClinique.charger()
    if request.method == "POST":
        if not services.est_docteur(request.user):
            return JsonResponse({"error": "Réservé au docteur."}, status=403)
        d = request.donnees
        if request.FILES.get("logo"):
            octets, erreur = reglages_clinique.preparer_logo(request.FILES["logo"])
            if erreur:
                return JsonResponse({"error": erreur}, status=400)
            reglages_clinique.enregistrer_logo(reglages, octets)
        elif reglages_clinique._vrai(d.get("retirer_logo", False)):
            reglages_clinique.retirer_logo(reglages)

        notifs = d.get("notifications")
        if isinstance(notifs, dict):  # forme {"notif_rdv": false, ...}
            d = {**d, **notifs}
        erreur = reglages_clinique.appliquer(reglages, d, cases_a_cocher=False)
        if erreur:
            return JsonResponse({"error": erreur}, status=400)
        nb = None
        if reglages_clinique._vrai(d.get("appliquer_seuil_a_tous", False)):
            from pharmacie.models import Medicament
            nb = Medicament.objects.update(seuil_alerte=reglages.seuil_alerte_defaut)
        reponse = {"clinique": reglages_clinique.en_dict(reglages, request),
                   "message": "Réglages enregistrés."}
        if nb is not None:
            reponse["message"] += f" Seuil appliqué à {nb} médicament(s)."
        return JsonResponse(reponse)
    return JsonResponse({
        "clinique": reglages_clinique.en_dict(reglages, request),
        "modifiable": services.est_docteur(request.user),
    })
