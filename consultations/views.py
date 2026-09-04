from django.shortcuts import render, redirect
from .models import Consultation
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from rest_framework import viewsets
from ventes.models import Vente, LigneVente
from .models import Consultation, RendezVous, Ordonnance, LigneOrdonnance
from pharmacie.models import Medicament
from .models import RendezVousManuel
from datetime import datetime
from .serializers import (
    ConsultationSerializer,
    RendezVousSerializer,
    OrdonnanceSerializer,
    LigneOrdonnanceSerializer
)
from clients.models import Client
from animaux.models import Animal
import json
import traceback

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

# ===== API VIEWSETS =====
class ConsultationViewSet(viewsets.ModelViewSet):
    queryset = Consultation.objects.all().order_by('-date')
    serializer_class = ConsultationSerializer

class RendezVousViewSet(viewsets.ModelViewSet):
    queryset = RendezVous.objects.all().order_by('-date_rdv')
    serializer_class = RendezVousSerializer

class OrdonnanceViewSet(viewsets.ModelViewSet):
    queryset = Ordonnance.objects.all()
    serializer_class = OrdonnanceSerializer

class LigneOrdonnanceViewSet(viewsets.ModelViewSet):
    queryset = LigneOrdonnance.objects.all()
    serializer_class = LigneOrdonnanceSerializer


# ===== PAGES HTML =====

from django.db.models import Q
from django.utils import timezone

def liste_consultations(request):
    consultations = Consultation.objects.select_related(
        "animal", "animal__client"
    ).order_by("-date")

    search = request.GET.get("search", "").strip()

    if search:
        consultations = consultations.filter(
            Q(animal__client__nom__icontains=search) |
            Q(animal__nom__icontains=search) |
            Q(animal__espece__icontains=search) |
            Q(motif__icontains=search)
        )

    total = consultations.count()
    en_cours = consultations.filter(statut="en_cours").count()
    terminees = consultations.filter(statut="terminee").count()

    consultations_jour = consultations.filter(
        date__date=timezone.localdate()
    ).count()

    return render(request, "consultations/liste_consultation.html", {
        "consultations": consultations,
        "total": total,
        "en_cours": en_cours,
        "terminees": terminees,
        "consultations_jour": consultations_jour,
        "search": search,
    })

from django.db import models
from types import SimpleNamespace
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST


from types import SimpleNamespace

from types import SimpleNamespace

class RDVManuelAdapter:
    def __init__(self, rdv_manuel):
        self.id = rdv_manuel.id
        self.date_rdv = rdv_manuel.date_rdv
        self.motif = rdv_manuel.motif
        self.type_rdv = "CABINET" if rdv_manuel.lieu == "cabinet" else "DOMICILE"
        self.statut = rdv_manuel.statut
        self.source = "manuel"

        self.animal = SimpleNamespace(
            nom=rdv_manuel.nom_animal or "—",
            espece=rdv_manuel.espece,
            race=rdv_manuel.race,
            client=SimpleNamespace(
                nom=rdv_manuel.nom_client,
                telephone=rdv_manuel.telephone or "—",
            )
        )
from django.shortcuts import render
from django.db import models
from django.utils import timezone

def rendez_vous_list(request):
    # Date du jour
    today = timezone.localdate()

    # ============================
    # Rendez-vous classiques
    # ============================
    rendezvous_qs = (
        RendezVous.objects
        .select_related("animal", "animal__client")
        .order_by("-date_rdv")
    )

    search = request.GET.get("search")
    statut = request.GET.get("statut")
    date = request.GET.get("date")

    if search:
        rendezvous_qs = rendezvous_qs.filter(
            models.Q(animal__client__nom__icontains=search) |
            models.Q(animal__nom__icontains=search)
        )

    if statut:
        rendezvous_qs = rendezvous_qs.filter(statut=statut)

    if date:
        rendezvous_qs = rendezvous_qs.filter(date_rdv__date=date)

    # ============================
    # Rendez-vous manuels
    # ============================
    manuels_qs = RendezVousManuel.objects.all().order_by("-date_rdv")

    if search:
        manuels_qs = manuels_qs.filter(
            models.Q(nom_client__icontains=search) |
            models.Q(nom_animal__icontains=search)
        )

    if statut:
        manuels_qs = manuels_qs.filter(statut=statut)

    if date:
        manuels_qs = manuels_qs.filter(date_rdv__date=date)

    # ============================
    # Statistiques
    # ============================
    tous_rdv = RendezVous.objects.all()
    tous_manuels = RendezVousManuel.objects.all()

    nb_attente = (
        tous_rdv.filter(statut="EN_ATTENTE").count()
        + tous_manuels.filter(statut="EN_ATTENTE").count()
    )

    nb_confirme = (
        tous_rdv.filter(statut="CONFIRME").count()
        + tous_manuels.filter(statut="CONFIRME").count()
    )

    nb_annule = (
        tous_rdv.filter(statut="ANNULE").count()
        + tous_manuels.filter(statut="ANNULE").count()
    )

    # ============================
    # Fusion des listes
    # ============================
    rendezvous_combines = (
        list(rendezvous_qs)
        + [RDVManuelAdapter(rdv) for rdv in manuels_qs]
    )

    # ============================
    # Tri : rendez-vous du jour en premier,
    # puis les autres par date décroissante
    # ============================
    rendezvous_combines.sort(
        key=lambda rdv: (
            rdv.date_rdv.date() != today,
            -rdv.date_rdv.timestamp()
        )
    )

    # ============================
    # Affichage
    # ============================
    return render(
        request,
        "consultations/rendez_vous_list.html",
        {
            "rendezvous": rendezvous_combines,
            "nb_attente": nb_attente,
            "nb_confirme": nb_confirme,
            "nb_annule": nb_annule,
            "active_page": "rendez_vous",
            "today": today,
        },
    )


@require_POST
def changer_statut_rdv(request, type_rdv, rdv_id):
    """
    type_rdv: 'classique' (RendezVous) ou 'manuel' (RendezVousManuel)
    """
    nouveau_statut = request.POST.get("statut")
    valides = ["EN_ATTENTE", "CONFIRME", "ANNULE", "TERMINE"]
    if nouveau_statut not in valides:
        messages.error(request, "Statut invalide.")
        return redirect("rendez_vous_list")

    if type_rdv == "manuel":
        rdv = get_object_or_404(RendezVousManuel, id=rdv_id)
    else:
        rdv = get_object_or_404(RendezVous, id=rdv_id)

    rdv.statut = nouveau_statut
    rdv.save()
    messages.success(request, "Statut mis à jour.")
    return redirect("rendez_vous_list")


@require_POST
def supprimer_rdv(request, type_rdv, rdv_id):
    if type_rdv == "manuel":
        rdv = get_object_or_404(RendezVousManuel, id=rdv_id)
    else:
        rdv = get_object_or_404(RendezVous, id=rdv_id)

    rdv.delete()
    messages.success(request, "Rendez-vous supprimé.")
    return redirect("rendez_vous_list")

@require_POST
def enregistrer_rendez_vous(request, ordonnance_id):
    ordonnance = get_object_or_404(Ordonnance, id=ordonnance_id)

    date = request.POST.get("date_rdv")
    heure = request.POST.get("heure_rdv")
    motif = request.POST.get("motif")

    if date and heure:
        rdv = RendezVous.objects.create(
            animal=ordonnance.consultation.animal,
            date_rdv=datetime.strptime(
                f"{date} {heure}",
                "%Y-%m-%d %H:%M"
            ),
            motif=motif,
            type_rdv="CABINET",
            statut="EN_ATTENTE",
        )

        ordonnance.rendez_vous = rdv
        ordonnance.save()

    return redirect("ordonnance_detail", ordonnance.id)

import json
from django.shortcuts import render, redirect
from django.contrib import messages

# Idéalement déplacé dans un fichier constants.py partagé si utilisé ailleurs
RACES = {
    "Chien":   ["Chien local","Berger allemand", "Berger belge Malinois", "Labrador","Rottweiler","Husky","Caniche","Autre"],
    "Chat":    ["Siamois","Persan","Maine Coon","Bengal","Autre"],
    "Bovin":   ["Gobra","Maure", "Djiakoré", "N'dama", "Zébu","Holstein","Autre"],
    "Caprin":  ["Checre du Sahel", "Chevre naine d'Afrique de l'Ouest", "Chevre rousse de Maradi", "Boer","Alpine","Autre"],
    "Ovin":    ["Ladoum", "Mouton Peul-Peul", "Touabir", "Mérinos","Suffolk","Autre"],
    "Volaille":["Poulet local","poulet de chair (Broiler)","Pondeuse", "Oie", "Dinde", "Canard", "Pintade","Autre"],
    "Cheval":  ["M'bayar", "Cheval du fleuve", "Barbe", "Pur-sang arabe","Autre"],
    "Poisson": ["Tilapia","Silure","Autre"],
    "Autre":   ["Autre"],
}


def nouveau_rendez_vous(request):
    if request.method == "POST":
        RendezVousManuel.objects.create(
            nom_client=request.POST.get("nom_client"),
            telephone=request.POST.get("telephone"),
            nom_animal = request.POST.get("nom_animal", "").strip() or "Non précisé",
            espece=request.POST.get("espece"),
            race=request.POST.get("race", ""),
            date_rdv=f"{request.POST.get('date')} {request.POST.get('heure')}",
            motif=request.POST.get("motif"),
            lieu=request.POST.get("lieu"),
            adresse=request.POST.get("adresse"),
        )
        messages.success(request, "Rendez-vous enregistré avec succès.")
        return redirect("rendez_vous_list")

    return render(request, "consultations/nouveau_rdv.html", {
        "races_json": json.dumps(RACES, ensure_ascii=False),
    })

def nouvelle_consultation(request):
    clients = Client.objects.all()

    clients_data = [
        {
            "id": c.id,
            "nom": c.nom,
            "telephone": c.telephone,
            "adresse": c.adresse
        }
        for c in clients
    ]

    return render(request, "consultations/nouvelle_consultation.html", {
    "clients": clients,
    "clients_data": clients_data,
    "active_menu": "consultations",
    "active_page": "nouvelle_consultation",
})


# ===== API CUSTOM =====

@csrf_exempt
@require_POST
def create_consultation(request):
    try:
        data = json.loads(request.body)
        print("=== DATA REÇUE ===", data)

        mode = data.get("mode")

        client_nouveau = False

        if mode == "existing":
            # Client ET animal déjà existants
            animal = Animal.objects.get(id=int(data["animal_id"]))
            client = Client.objects.get(id=int(data["client_id"]))

        elif mode == "existing_new_animal":
            # Client existant, nouvel animal à créer pour lui
            client = Client.objects.get(id=int(data["client_id"]))

            animal_nom = data.get("animal_nom", "").strip() or "Non renseigné"

            animal_poids = (
                float(data["animal_poids"])
                if data.get("animal_poids")
                else 0
            )

            animal = Animal.objects.create(
                client=client,
                nom=animal_nom,
                espece=data["animal_espece"],
                race=data.get("animal_race", ""),
                sexe=data.get("animal_sexe", "M"),
                poids=animal_poids,
            )

        elif mode == "new":
            # Nouveau client ET nouvel animal
            client = Client.objects.create(
                nom=data["client_nom"],
                telephone=data.get("client_phone", ""),
                adresse=data.get("client_adresse", "")
            )

            client_nouveau = True

            animal_nom = data.get("animal_nom", "").strip() or "Non renseigné"

            animal_poids = (
                float(data["animal_poids"])
                if data.get("animal_poids")
                else 0
            )

            animal = Animal.objects.create(
                client=client,
                nom=animal_nom,
                espece=data["animal_espece"],
                race=data.get("animal_race", ""),
                sexe=data.get("animal_sexe", "M"),
                poids=animal_poids,
            )

        else:
            return JsonResponse(
                {"error": "Mode de création de consultation invalide."},
                status=400
            )

        # Création de la consultation (commun aux trois modes)
        consultation = Consultation.objects.create(
            client=client,
            animal=animal,
            veterinaire="Dr Ibrahima Pierre GUISSE",
            motif=data["motif"],
            observations=data.get("observations", ""),
            lieu=data.get("lieu", "cabinet"),
            poids=(
                float(data["animal_poids"])
                if data.get("animal_poids")
                else None
            ),
            statut="en_cours",
            client_nouveau=client_nouveau,
        )

        return JsonResponse({
            "message": "OK",
            "id": consultation.id,
            "client_adresse": client.adresse,
        })

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )
        
def consultation_detail(request, consultation_id):
    consultation = Consultation.objects.get(id=consultation_id)

    all_consultations = Consultation.objects.select_related("animal", "animal__client").order_by("-date")

    return render(request, "consultations/detail_consultation.html", {
        "consultation": consultation,
        "all_consultations": all_consultations
    })   


def terminer_consultation(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)

    # 1. éviter double traitement
    if consultation.statut == "terminee":
        return redirect("consultation_detail", consultation_id=consultation.id)

    # 2. récupérer ordonnance
    ordonnance = Ordonnance.objects.filter(consultation=consultation).first()

    if not ordonnance:
        return redirect("ordonnance_create", consultation_id=consultation.id)

    if not ordonnance.lignes.exists():
        messages.warning(
            request,
           "Impossible de terminer la consultation : "
           "l'ordonnance doit contenir au moins un médicament."
        )
        return redirect("ordonnance_detail", ordonnance_id=ordonnance.id)
    with transaction.atomic():

        # 3. créer vente
        vente = Vente.objects.create(
            ordonnance=ordonnance,
            total=0
        )

        total = 0

        # 4. lignes de vente
        for ligne in ordonnance.lignes.all():

            montant = ligne.quantite * ligne.medicament.prix

            LigneVente.objects.create(
                vente=vente,
                medicament=ligne.medicament,
                quantite=ligne.quantite,
                prix_unitaire=ligne.medicament.prix,
                montant_total=montant
            )

            total += montant

        # 5. update total vente
        vente.total = total
        vente.save()

        # 6. update stock (SI PAS déjà dans save)
        for ligne in ordonnance.lignes.all():
            med = ligne.medicament
            med.stock -= ligne.quantite
            med.save()

        # 7. terminer consultation
        consultation.statut = "terminee"
        consultation.save()

    # 8. redirection vers vente ou PDF
    return redirect("vente_detail", vente.id)


def edit_consultation(request, id):
    consultation = get_object_or_404(
        Consultation.objects.select_related("client", "animal"),
        id=id
    )

    # Une consultation terminée est définitivement verrouillée.
    if consultation.statut == "terminee":
        messages.warning(
            request,
            "Cette consultation est terminée et ne peut plus être modifiée."
        )
        return redirect("consultation_detail", consultation_id=consultation.id)

    client = consultation.client
    animal = consultation.animal

    if request.method == "POST":
        # ---------------------------------------------------------
        # CLIENT : modifiable uniquement s'il était nouveau
        # lors de la création de cette consultation.
        # ---------------------------------------------------------
        if consultation.client_nouveau:
            client_nom = request.POST.get("client_nom", "").strip()
            telephone = request.POST.get("telephone", "").strip()
            adresse = request.POST.get("adresse", "").strip()

            if not client_nom:
                messages.error(request, "Le nom du client est obligatoire.")
                return redirect("edit_consultation", id=consultation.id)

            # Le téléphone doit rester unique, sauf pour le client actuel.
            if telephone and Client.objects.filter(
                telephone=telephone
            ).exclude(id=client.id).exists():
                messages.error(
                    request,
                    "Ce numéro de téléphone est déjà utilisé par un autre client."
                )
                return redirect("edit_consultation", id=consultation.id)
        else:
            # Pour un client existant, les valeurs POST du formulaire sont
            # volontairement ignorées : le client reste verrouillé.
            client_nom = client.nom
            telephone = client.telephone or ""
            adresse = client.adresse or ""

        # ---------------------------------------------------------
        # ANIMAL
        # ---------------------------------------------------------
        animal_nom = request.POST.get("animal_nom", "").strip()
        espece = request.POST.get("espece", "").strip()
        race = request.POST.get("race", "").strip()
        sexe = request.POST.get("sexe", "").strip()
        animal_poids_raw = request.POST.get("animal_poids", "").strip()

        if not animal_nom:
            messages.error(request, "Le nom de l'animal est obligatoire.")
            return redirect("edit_consultation", id=consultation.id)

        if not espece:
            messages.error(request, "L'espèce de l'animal est obligatoire.")
            return redirect("edit_consultation", id=consultation.id)

        if sexe and sexe not in ["M", "F"]:
            messages.error(request, "Le sexe de l'animal est invalide.")
            return redirect("edit_consultation", id=consultation.id)

        # ---------------------------------------------------------
        # CONSULTATION
        # ---------------------------------------------------------
        motif = request.POST.get("motif", "").strip()
        observations = request.POST.get("observations", "").strip()
        lieu = request.POST.get("lieu", "").strip()
        consultation_poids_raw = request.POST.get("poids", "").strip()
        veterinaire = request.POST.get("veterinaire", "").strip()
        statut = request.POST.get("statut", "").strip()

        if not motif:
            messages.error(request, "Le motif de consultation est obligatoire.")
            return redirect("edit_consultation", id=consultation.id)

        if lieu not in ["cabinet", "domicile"]:
            messages.error(request, "Le lieu de consultation est invalide.")
            return redirect("edit_consultation", id=consultation.id)

        if statut not in ["en_cours", "annulee"]:
            # La terminaison passe par terminer_consultation(), qui gère
            # également l'ordonnance et le stock.
            messages.warning(
                request,
                "Pour terminer une consultation, utilisez le bouton « Terminer la consultation »."
            )
            return redirect("edit_consultation", id=consultation.id)

        def parse_weight(value, field_name):
            if value == "":
                return None
            try:
                result = float(value.replace(",", "."))
            except (ValueError, AttributeError):
                raise ValueError(f"Le {field_name} est invalide.")
            if result < 0:
                raise ValueError(f"Le {field_name} ne peut pas être négatif.")
            return result

        try:
            animal_poids = parse_weight(animal_poids_raw, "poids de l'animal")
            consultation_poids = parse_weight(
                consultation_poids_raw,
                "poids de la consultation"
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("edit_consultation", id=consultation.id)

        try:
            with transaction.atomic():
                # Client : seulement si nouveau lors de la consultation.
                if consultation.client_nouveau:
                    client.nom = client_nom
                    client.telephone = telephone or None
                    client.adresse = adresse or None
                    client.save()

                # Animal : toujours modifiable tant que la consultation est en cours.
                animal.client = client
                animal.nom = animal_nom
                animal.espece = espece
                animal.race = race or None
                animal.sexe = sexe or None
                animal.poids = animal_poids
                animal.save()

                # Consultation : tous les champs métier modifiables.
                consultation.client = client
                consultation.animal = animal
                consultation.motif = motif
                consultation.observations = observations
                consultation.lieu = lieu
                consultation.poids = consultation_poids
                consultation.veterinaire = veterinaire
                consultation.statut = statut
                consultation.save()

        except Exception as exc:
            messages.error(
                request,
                f"Erreur lors de la modification : {exc}"
            )
            return redirect("edit_consultation", id=consultation.id)

        messages.success(
            request,
            "La consultation a été modifiée avec succès."
        )
        return redirect("consultation_detail", consultation_id=consultation.id)

    return render(request, "consultations/edit_consultation.html", {
        "consultation": consultation,
        "client": client,
        "animal": animal,
    })

def ordonnance_detail (request, ordonnance_id):
    ordonnance = get_object_or_404(Ordonnance, id=ordonnance_id)

    medicaments = Medicament.objects.filter(
        stock__gt=0
    ).select_related(
        "catalogue",
        "catalogue__famille"
    ).order_by(
        "catalogue__nom"
    )

    return render(
        request,
        "consultations/ordonnance_detail.html",
        {
            "ordonnance": ordonnance,
            "medicaments": medicaments,
            "rendez_vous": ordonnance.rendez_vous,
        }
    )

@csrf_exempt
@require_POST
# ── Remplace ajouter_ligne_ordonnance et supprimer_ligne_ordonnance ─────────
# dans consultations/views.py
# ✅ Empêche toute modification une fois la consultation terminée
#    (sécurité côté serveur, en plus du verrouillage Flutter)

def ajouter_ligne_ordonnance(request, ordonnance_id):
    ordonnance = get_object_or_404(Ordonnance, id=ordonnance_id)

    if ordonnance.consultation.statut == "terminee":
        return JsonResponse(
            {"error": "Consultation terminée — ordonnance verrouillée."},
            status=403,
        )

    data = json.loads(request.body)
    from pharmacie.models import Medicament
    med = get_object_or_404(Medicament, id=data['medicament_id'])
    ligne = LigneOrdonnance.objects.create(
        ordonnance=ordonnance,
        medicament=med,
        quantite=int(data['quantite']),
        posologie=data['posologie']
    )
    return JsonResponse({"id": ligne.id})

@csrf_exempt
@require_http_methods(["POST", "PUT"])
def modifier_ligne_ordonnance(request, ligne_id):
    ligne = get_object_or_404(
        LigneOrdonnance.objects.select_related(
            "ordonnance__consultation",
            "medicament"
        ),
        id=ligne_id
    )

    # Consultation terminée = ordonnance verrouillée
    if ligne.ordonnance.consultation.statut == "terminee":
        return JsonResponse(
            {
                "error": "Consultation terminée — ordonnance verrouillée."
            },
            status=403
        )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {"error": "Données JSON invalides."},
            status=400
        )

    quantite = data.get("quantite")
    posologie = data.get("posologie", "").strip()

    if not quantite:
        return JsonResponse(
            {"error": "La quantité est obligatoire."},
            status=400
        )

    try:
        quantite = int(quantite)
    except (ValueError, TypeError):
        return JsonResponse(
            {"error": "La quantité doit être un nombre entier."},
            status=400
        )

    if quantite <= 0:
        return JsonResponse(
            {"error": "La quantité doit être supérieure à zéro."},
            status=400
        )

    if not posologie:
        return JsonResponse(
            {"error": "La posologie est obligatoire."},
            status=400
        )

    # Si un nouveau médicament est envoyé
    medicament_id = data.get("medicament_id")

    if medicament_id:
        from pharmacie.models import Medicament

        medicament = get_object_or_404(
            Medicament,
            id=medicament_id
        )

        ligne.medicament = medicament

    ligne.quantite = quantite
    ligne.posologie = posologie
    ligne.save()

    return JsonResponse({
        "ok": True,
        "id": ligne.id,
        "medicament_id": ligne.medicament.id,
        "medicament": str(ligne.medicament),
        "quantite": ligne.quantite,
        "posologie": ligne.posologie,
    })

@csrf_exempt
@require_POST
def supprimer_ligne_ordonnance(request, ligne_id):
    ligne = get_object_or_404(LigneOrdonnance, id=ligne_id)

    if ligne.ordonnance.consultation.statut == "terminee":
        return JsonResponse(
            {"error": "Consultation terminée — ordonnance verrouillée."},
            status=403,
        )

    ligne.delete()
    return JsonResponse({"ok": True})


def ordonnance_create(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)

    ordonnance, created = Ordonnance.objects.get_or_create(
        consultation=consultation
    )

    if not created:
        return redirect("ordonnance_detail", ordonnance.id)

    return redirect("ordonnance_detail", ordonnance.id)


def ordonnance_pdf(request, ordonnance_id):
    ordonnance = get_object_or_404(Ordonnance, id=ordonnance_id)
    consultation = ordonnance.consultation
    client = consultation.client
    animal = consultation.animal

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="ordonnance_{ordonnance.id}.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # ==========================
    # EN-TÊTE (gauche: cabinet / droite: date)
    # ==========================
    gauche = Paragraph(
        """
        <b><font size="16">PARCELLES VETO</font></b><br/>
        Cabinet de soins Vétérinaires<br/>
        Thies Parcelles Assainies U2<br/>
        En Face Cimetière Keur Dago<br/>
        Tél : 77 538 57 29 / 76 833 16 23<br/>
        Email : parcelles-veto@gmail.com
        """,
        styles["Normal"],
    )

    droite_style = ParagraphStyle(
        "DateStyle", parent=styles["Normal"], alignment=TA_RIGHT
    )
    droite = Paragraph(
        f"""
        <b>Date :</b><br/>
        {ordonnance.date_creation.strftime("%d/%m/%Y")}
        """,
        droite_style,
    )

    header = Table([[gauche, droite]], colWidths=[12 * cm, 6 * cm])
    header.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    elements.append(header)
    elements.append(Spacer(1, 0.6 * cm))

    # ==========================
    # TITRE ORDONNANCE (souligné)
    # ==========================
    titre_style = ParagraphStyle(
        "TitreOrdonnance",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=16,
    )
    elements.append(Paragraph("<u><b>ORDONNANCE</b></u>", titre_style))
    elements.append(Spacer(1, 0.8 * cm))

    # ==========================
    # INFOS CLIENT / ANIMAL (au milieu)
    # ==========================
    info_style = styles["Normal"]
    elements.append(Paragraph(
        f"""
        <b>Client :</b> {client.nom}<br/>
        <b>Téléphone :</b> {client.telephone or "—"}<br/>
        <b>Animal :</b> {animal.nom} ({animal.espece})<br/>
        <b>Motif :</b> {consultation.motif or "—"}
        """,
        info_style,
    ))
    elements.append(Spacer(1, 1 * cm))

    # ==========================
    # MÉDICAMENTS PRESCRITS
    # ==========================
    lignes = ordonnance.lignes.select_related(
        "medicament", "medicament__catalogue"
    ).all()

    if lignes:
        data = [["#", "Médicament", "Quantité", "Posologie"]]
        for i, ligne in enumerate(lignes, start=1):
            data.append([
                str(i),
                ligne.medicament.catalogue.nom,
                str(ligne.quantite),
                ligne.posologie,
            ])

        table = Table(
            data,
            colWidths=[1 * cm, 5 * cm, 3 * cm, 8 * cm],
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (1, -1), "CENTER"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph(
            "<i>Aucun médicament prescrit.</i>", styles["Normal"]
        ))

    elements.append(Spacer(1, 3 * cm))

    # ==========================
    # PIED DE PAGE
    # ==========================
    elements.append(HRFlowable(width="100%", color=colors.grey, thickness=0.5))
    elements.append(Spacer(1, 0.3 * cm))
    pied_style = ParagraphStyle(
        "Pied", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9
    )
    elements.append(Paragraph(
        "Veuillez rapporter l'ordonnance à la prochaine consultation",
        pied_style,
    ))

    doc.build(elements)
    return response

def animaux_client(request, client_id):
    animaux = Animal.objects.filter(client_id=client_id)
    data = [
        {
            "id":     a.id,
            "nom":    a.nom,
            "espece": a.espece,
            "race":   a.race,
            "sexe":   a.sexe,
            "poids":  str(a.poids),
        }
        for a in animaux
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def api_consultations(request):
    consultations = Consultation.objects.select_related(
        'animal', 'animal__client'
    ).order_by('-date')[:50]
    
    data = [{
        "id": c.id,
        "animal": c.animal.nom,
        "espece": c.animal.espece,
        "client": c.animal.client.nom,
        "motif": c.motif,
        "statut": c.statut,
        "lieu": c.lieu,
        "date": c.date.strftime("%d/%m/%Y %H:%M"),
    } for c in consultations]
    
    return JsonResponse(data, safe=False)


@csrf_exempt
def api_rendezvous(request):
    rdvs = RendezVous.objects.select_related(
        'animal', 'animal__client'
    ).order_by('-date_rdv')[:50]
    
    data = [{
        "id": r.id,
        "animal": r.animal.nom,
        "espece": r.animal.espece,
        "client": r.animal.client.nom,
        "motif": r.motif,
        "statut": r.statut,
        "type_rdv": r.type_rdv,
        "date_rdv": r.date_rdv.strftime("%d/%m/%Y %H:%M"),
    } for r in rdvs]
    
    return JsonResponse(data, safe=False)

# ── À ajouter à la fin de consultations/views.py ────────────────────────────
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


def api_consultations_liste(request):
    """GET /consultations/api/liste/ — liste consultations pour Flutter."""
    qs = Consultation.objects.select_related(
        "client", "animal"
    ).order_by("-date")

    statut = request.GET.get("statut")
    if statut:
        qs = qs.filter(statut=statut)

    data = []
    for c in qs:
        data.append({
            "id": c.id,
            "client": c.client.nom if c.client else "",
            "animal": c.animal.nom if c.animal else "",
            "espece": c.animal.espece if c.animal else "",
            "motif": c.motif or "",
            "observations": c.observations or "",
            "statut": c.statut,
            "lieu": c.lieu,
            "veterinaire": c.veterinaire or "",
            "poids": c.poids or 0,
            "date": c.date.strftime("%d/%m/%Y %H:%M"),
        })
    return JsonResponse(data, safe=False)


def api_rdv_liste(request):
    """GET /consultations/api/rdv/ — liste tous les RDV (standard + manuel)."""
    rdvs = RendezVous.objects.select_related(
        "animal__client"
    ).order_by("-date_rdv")

    rdvs_manuels = RendezVousManuel.objects.all().order_by("-date_rdv")

    data = []

    for r in rdvs:
        data.append({
            "id": r.id,
            "type": "standard",
            "client": r.animal.client.nom if r.animal and r.animal.client else "",
            "animal": r.animal.nom if r.animal else "",
            "espece": r.animal.espece if r.animal else "",
            "motif": r.motif or "",
            "date_rdv": r.date_rdv.strftime("%d/%m/%Y %H:%M"),
            "type_rdv": r.type_rdv,
            "statut": r.statut,
            "lieu": r.type_rdv,
            "telephone": "",
        })

    for r in rdvs_manuels:
        data.append({
            "id": r.id,
            "type": "manuel",
            "client": r.nom_client or "",
            "animal": r.nom_animal or "",
            "espece": r.espece or "",
            "motif": r.motif or "",
            "date_rdv": r.date_rdv.strftime("%d/%m/%Y %H:%M"),
            "type_rdv": r.lieu,
            "statut": r.statut,
            "lieu": r.adresse or "",
            "telephone": r.telephone or "",
        })

    # Trier par date décroissante
    data.sort(key=lambda x: x["date_rdv"], reverse=True)
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def api_ajouter_consultation(request):
    """POST /consultations/api/ajouter/"""
    try:
        data = json.loads(request.body)
        animal = Animal.objects.get(pk=data["animal_id"])
        consultation = Consultation.objects.create(
            client=animal.client,
            animal=animal,
            motif=data.get("motif", ""),
            observations=data.get("observations", ""),
            poids=data.get("poids") or None,
            lieu=data.get("lieu", "cabinet"),
            veterinaire=data.get("veterinaire", ""),
            statut="en_cours",
            client_nouveau=False,
        )
        return JsonResponse({"id": consultation.id}, status=201)
    except Animal.DoesNotExist:
        return JsonResponse({"error": "Animal introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
def api_modifier_statut_consultation(request, consultation_id):
    """PUT /consultations/api/<id>/statut/"""

    try:
        consultation = Consultation.objects.get(pk=consultation_id)
        data = json.loads(request.body)

        statut = data.get("statut")

        if statut not in ["en_cours", "annulee"]:
            return JsonResponse({
                "error": (
                    "Le statut 'terminee' doit être effectué "
                    "via l'endpoint de terminaison de consultation."
                ),
                "code": "USE_TERMINER_CONSULTATION"
            }, status=400)

        consultation.statut = statut
        consultation.save()

        return JsonResponse({
            "id": consultation.id,
            "statut": consultation.statut
        })

    except Consultation.DoesNotExist:
        return JsonResponse(
            {"error": "Consultation introuvable"},
            status=404
        )

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=400
        )


@csrf_exempt
@require_http_methods(["POST"])
def api_ajouter_rdv_manuel(request):
    """POST /consultations/api/rdv/ajouter/ — RDV manuel depuis Flutter."""
    try:
        data = json.loads(request.body)
        rdv = RendezVousManuel.objects.create(
            nom_client=data.get("nom_client", ""),
            nom_animal=data.get("nom_animal", ""),
            espece=data.get("espece", ""),
            race=data.get("race", ""),
            date_rdv=data.get("date_rdv"),
            motif=data.get("motif", ""),
            lieu=data.get("lieu", "cabinet"),
            adresse=data.get("adresse", ""),
            telephone=data.get("telephone", ""),
            statut="EN_ATTENTE",
        )
        return JsonResponse({"id": rdv.id}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
def api_modifier_statut_rdv(request, rdv_id):
    """PUT /consultations/api/rdv/<id>/statut/"""
    try:
        data = json.loads(request.body)
        type_rdv = data.get("type", "standard")
        statut = data.get("statut", "EN_ATTENTE")

        if type_rdv == "manuel":
            rdv = RendezVousManuel.objects.get(pk=rdv_id)
        else:
            rdv = RendezVous.objects.get(pk=rdv_id)

        rdv.statut = statut
        rdv.save()
        return JsonResponse({"id": rdv.id, "statut": rdv.statut})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

# ── À ajouter à la fin de consultations/views.py ────────────────────────────

# ── Remplace api_ordonnance_detail dans consultations/views.py ──────────────

def api_ordonnance_detail(request, consultation_id):
    """
    GET /consultations/api/<id>/ordonnance/
    Crée l'ordonnance si elle n'existe pas, retourne ses détails + lignes.
    ✅ Inclut maintenant le statut de la consultation pour verrouiller
       l'écran côté Flutter une fois la consultation terminée.
    """
    try:
        consultation = Consultation.objects.select_related(
            "client", "animal"
        ).get(pk=consultation_id)

        ordonnance, _ = Ordonnance.objects.get_or_create(
            consultation=consultation
        )

        lignes = []
        for ligne in ordonnance.lignes.select_related(
            "medicament__catalogue__famille"
        ).all():
            lignes.append({
                "id": ligne.id,
                "medicament_id": ligne.medicament.id,
                "medicament_nom": ligne.medicament.catalogue.nom
                    if ligne.medicament.catalogue else str(ligne.medicament),
                "famille": ligne.medicament.catalogue.famille.nom
                    if ligne.medicament.catalogue and ligne.medicament.catalogue.famille else "",
                "quantite": ligne.quantite,
                "posologie": ligne.posologie,
                "stock": ligne.medicament.stock,
            })

        medicaments_qs = Medicament.objects.filter(
            stock__gt=0
        ).select_related("catalogue__famille").order_by(
            "catalogue__famille__nom", "catalogue__nom"
        )

        medicaments = []
        for m in medicaments_qs:
            medicaments.append({
                "id": m.id,
                "nom": m.catalogue.nom if m.catalogue else str(m),
                "famille": m.catalogue.famille.nom
                    if m.catalogue and m.catalogue.famille else "Autre",
                "stock": m.stock,
                "prix": float(m.prix or 0),
            })

        return JsonResponse({
            "ordonnance_id": ordonnance.id,
            "consultation": {
                "id": consultation.id,
                "client": consultation.client.nom,
                "animal": consultation.animal.nom,
                "espece": consultation.animal.espece,
                "motif": consultation.motif,
                "date": consultation.date.strftime("%d/%m/%Y"),
                "statut": consultation.statut,  # ✅ ajouté
            },
            "lignes": lignes,
            "medicaments_disponibles": medicaments,
        })

    except Consultation.DoesNotExist:
        return JsonResponse({"error": "Consultation introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

# ── À ajouter à la fin de consultations/views.py ────────────────────────────
# Remplace/complète api_modifier_statut_consultation pour le cas "terminee"
# en répliquant EXACTEMENT la logique de terminer_consultation (vente + stock).

from django.db import transaction


@csrf_exempt
@require_http_methods(["POST"])
def api_terminer_consultation(request, consultation_id):
    """
    POST /consultations/api/<id>/terminer/
    Termine la consultation : crée la vente, déduit le stock, lie l'ordonnance.
    Reproduit exactement la logique de terminer_consultation (vue web).
    """
    try:
        consultation = Consultation.objects.get(pk=consultation_id)

        if consultation.statut == "terminee":
            return JsonResponse({"error": "Consultation déjà terminée"}, status=400)

        ordonnance = Ordonnance.objects.filter(consultation=consultation).first()

        if not ordonnance:
            return JsonResponse({
                "error": "Aucune ordonnance trouvée. Créez d'abord une ordonnance.",
                "code": "NO_ORDONNANCE",
            }, status=400)

        if not ordonnance.lignes.exists():
            return JsonResponse({
                "error": "L'ordonnance ne contient aucun médicament.",
                "code": "EMPTY_ORDONNANCE",
            }, status=400)

        with transaction.atomic():
            # Créer la vente
            vente = Vente.objects.create(ordonnance=ordonnance, total=0)
            total = 0

            for ligne in ordonnance.lignes.all():
                montant = ligne.quantite * ligne.medicament.prix
                LigneVente.objects.create(
                    vente=vente,
                    medicament=ligne.medicament,
                    quantite=ligne.quantite,
                    prix_unitaire=ligne.medicament.prix,
                    montant_total=montant,
                )
                total += montant

            vente.total = total
            vente.save()

            # Déduire le stock
            for ligne in ordonnance.lignes.all():
                med = ligne.medicament
                med.stock -= ligne.quantite
                med.save()

            # Terminer la consultation
            consultation.statut = "terminee"
            consultation.save()

        return JsonResponse({
            "id": consultation.id,
            "statut": consultation.statut,
            "vente_id": vente.id,
            "total_vente": float(total),
        })

    except Consultation.DoesNotExist:
        return JsonResponse({"error": "Consultation introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)        
