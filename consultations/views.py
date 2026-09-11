import json
import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from rest_framework import permissions, viewsets

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from animaux.models import Animal
from clients.models import Client
from pharmacie.models import Medicament
from ventes.models import LigneVente, Vente

from .models import Consultation, LigneOrdonnance, Ordonnance, RendezVous, RendezVousManuel
from .serializers import (
    ConsultationSerializer,
    LigneOrdonnanceSerializer,
    OrdonnanceSerializer,
    RendezVousSerializer,
)

logger = logging.getLogger(__name__)

# ===== API VIEWSETS (REST Framework) =====

class ConsultationViewSet(viewsets.ModelViewSet):
    queryset = Consultation.objects.all().order_by('-date')
    serializer_class = ConsultationSerializer
    permission_classes = [permissions.IsAuthenticated]

class RendezVousViewSet(viewsets.ModelViewSet):
    queryset = RendezVous.objects.all().order_by('-date_rdv')
    serializer_class = RendezVousSerializer
    permission_classes = [permissions.IsAuthenticated]

class OrdonnanceViewSet(viewsets.ModelViewSet):
    queryset = Ordonnance.objects.all()
    serializer_class = OrdonnanceSerializer
    permission_classes = [permissions.IsAuthenticated]

class LigneOrdonnanceViewSet(viewsets.ModelViewSet):
    queryset = LigneOrdonnance.objects.all()
    serializer_class = LigneOrdonnanceSerializer
    permission_classes = [permissions.IsAuthenticated]


# ===== PAGES HTML & CONTRÔLEURS =====

@login_required
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


class RDVManuelAdapter:
    def __init__(self, rdv_manuel):
        self.id = rdv_manuel.id
        self.date_rdv = rdv_manuel.date_rdv
        self.motif = rdv_manuel.motif
        self.type_rdv = "CABINET" if rdv_manuel.lieu == "cabinet" else "DOMICILE"
        self.statut = rdv_manuel.statut
        self.source = "manuel"

        self.animal = type('AnimalAdapter', (), {
            'nom': rdv_manuel.nom_animal or "—",
            'espece': rdv_manuel.espece,
            'race': rdv_manuel.race,
            'client': type('ClientAdapter', (), {
                'nom': rdv_manuel.nom_client,
                'telephone': rdv_manuel.telephone or "—",
            })()
        })()


@login_required
def rendez_vous_list(request):
    today = timezone.localdate()

    rendezvous_qs = (
        RendezVous.objects
        .select_related("animal", "animal__client")
        .order_by("-date_rdv")
    )

    search = request.GET.get("search", "").strip()
    statut = request.GET.get("statut", "").strip()
    date = request.GET.get("date", "").strip()

    if search:
        rendezvous_qs = rendezvous_qs.filter(
            models.Q(animal__client__nom__icontains=search) |
            models.Q(animal__nom__icontains=search)
        )

    if statut:
        rendezvous_qs = rendezvous_qs.filter(statut=statut)

    if date:
        rendezvous_qs = rendezvous_qs.filter(date_rdv__date=date)

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

    tous_rdv = RendezVous.objects.all()
    tous_manuels = RendezVousManuel.objects.all()

    nb_attente = (
        tous_rdv.filter(statut="EN_ATTENTE").count() +
        tous_manuels.filter(statut="EN_ATTENTE").count()
    )
    nb_confirme = (
        tous_rdv.filter(statut="CONFIRME").count() +
        tous_manuels.filter(statut="CONFIRME").count()
    )
    nb_annule = (
        tous_rdv.filter(statut="ANNULE").count() +
        tous_manuels.filter(statut="ANNULE").count()
    )

    rendezvous_combines = list(rendezvous_qs) + [RDVManuelAdapter(rdv) for rdv in manuels_qs]

    rendezvous_combines.sort(
        key=lambda rdv: (
            rdv.date_rdv.date() != today,
            -rdv.date_rdv.timestamp()
        )
    )

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


@login_required
@require_POST
def changer_statut_rdv(request, type_rdv, rdv_id):
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


@login_required
@require_POST
def supprimer_rdv(request, type_rdv, rdv_id):
    if type_rdv == "manuel":
        rdv = get_object_or_404(RendezVousManuel, id=rdv_id)
    else:
        rdv = get_object_or_404(RendezVous, id=rdv_id)

    rdv.delete()
    messages.success(request, "Rendez-vous supprimé.")
    return redirect("rendez_vous_list")


@login_required
@require_POST
def enregistrer_rendez_vous(request, ordonnance_id):
    ordonnance = get_object_or_404(Ordonnance, id=ordonnance_id)

    date = request.POST.get("date_rdv")
    heure = request.POST.get("heure_rdv")
    motif = request.POST.get("motif", "").strip()

    if date and heure:
        try:
            date_rdv_dt = datetime.strptime(f"{date} {heure}", "%Y-%m-%d %H:%M")
            rdv = RendezVous.objects.create(
                animal=ordonnance.consultation.animal,
                date_rdv=date_rdv_dt,
                motif=motif,
                type_rdv="CABINET",
                statut="EN_ATTENTE",
            )
            ordonnance.rendez_vous = rdv
            ordonnance.save()
            messages.success(request, "Rendez-vous enregistré.")
        except ValueError:
            messages.error(request, "Format de date ou heure invalide.")

    return redirect("ordonnance_detail", ordonnance_id=ordonnance.id)


RACES = {
    "Chien": ["Chien local", "Berger allemand", "Berger belge Malinois", "Labrador", "Rottweiler", "Husky", "Caniche", "Autre"],
    "Chat": ["Siamois", "Persan", "Maine Coon", "Bengal", "Autre"],
    "Bovin": ["Gobra", "Maure", "Djiakoré", "N'dama", "Zébu", "Holstein", "Autre"],
    "Caprin": ["Chevre du Sahel", "Chevre naine d'Afrique de l'Ouest", "Chevre rousse de Maradi", "Boer", "Alpine", "Autre"],
    "Ovin": ["Ladoum", "Mouton Peul-Peul", "Touabir", "Mérinos", "Suffolk", "Autre"],
    "Volaille": ["Poulet local", "Poulet de chair (Broiler)", "Pondeuse", "Oie", "Dinde", "Canard", "Pintade", "Autre"],
    "Cheval": ["M'bayar", "Cheval du fleuve", "Barbe", "Pur-sang arabe", "Autre"],
    "Poisson": ["Tilapia", "Silure", "Autre"],
    "Autre": ["Autre"],
}


@login_required
def nouveau_rendez_vous(request):
    if request.method == "POST":
        try:
            date_str = request.POST.get('date')
            heure_str = request.POST.get('heure')
            dt = datetime.strptime(f"{date_str} {heure_str}", "%Y-%m-%d %H:%M")

            RendezVousManuel.objects.create(
                nom_client=request.POST.get("nom_client", "").strip(),
                telephone=request.POST.get("telephone", "").strip(),
                nom_animal=request.POST.get("nom_animal", "").strip() or "Non précisé",
                espece=request.POST.get("espece", "").strip(),
                race=request.POST.get("race", "").strip(),
                date_rdv=dt,
                motif=request.POST.get("motif", "").strip(),
                lieu=request.POST.get("lieu", "cabinet"),
                adresse=request.POST.get("adresse", "").strip(),
            )
            messages.success(request, "Rendez-vous enregistré avec succès.")
            return redirect("rendez_vous_list")
        except (ValueError, TypeError):
            messages.error(request, "Veuillez vérifier les informations et le format de la date.")

    return render(request, "consultations/nouveau_rdv.html", {
        "races_json": json.dumps(RACES, ensure_ascii=False),
    })


@login_required
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


@login_required
@require_POST
def create_consultation(request):
    try:
        data = json.loads(request.body)
        mode = data.get("mode")
        client_nouveau = False

        with transaction.atomic():
            if mode == "existing":
                animal = get_object_or_404(Animal, id=int(data.get("animal_id")))
                client = get_object_or_404(Client, id=int(data.get("client_id")))

            elif mode == "existing_new_animal":
                client = get_object_or_404(Client, id=int(data.get("client_id")))
                animal_nom = data.get("animal_nom", "").strip() or "Non renseigné"
                animal_poids = float(data.get("animal_poids", 0) or 0)

                animal = Animal.objects.create(
                    client=client,
                    nom=animal_nom,
                    espece=data.get("animal_espece", ""),
                    race=data.get("animal_race", ""),
                    sexe=data.get("animal_sexe", "M"),
                    poids=animal_poids,
                )

            elif mode == "new":
                client = Client.objects.create(
                    nom=data.get("client_nom", "").strip(),
                    telephone=data.get("client_phone", "").strip(),
                    adresse=data.get("client_adresse", "").strip()
                )
                client_nouveau = True
                animal_nom = data.get("animal_nom", "").strip() or "Non renseigné"
                animal_poids = float(data.get("animal_poids", 0) or 0)

                animal = Animal.objects.create(
                    client=client,
                    nom=animal_nom,
                    espece=data.get("animal_espece", ""),
                    race=data.get("animal_race", ""),
                    sexe=data.get("animal_sexe", "M"),
                    poids=animal_poids,
                )
            else:
                return JsonResponse({"error": "Mode de création invalide."}, status=400)

            poids_val = float(data["animal_poids"]) if data.get("animal_poids") else None

            consultation = Consultation.objects.create(
                client=client,
                animal=animal,
                veterinaire="Dr Ibrahima Pierre GUISSE",
                motif=data.get("motif", "").strip(),
                observations=data.get("observations", "").strip(),
                lieu=data.get("lieu", "cabinet"),
                poids=poids_val,
                statut="en_cours",
                client_nouveau=client_nouveau,
            )

        return JsonResponse({
            "message": "OK",
            "id": consultation.id,
            "client_adresse": client.adresse,
        })

    except (KeyError, ValueError) as exc:
        return JsonResponse({"error": "Données saisies invalides."}, status=400)
    except Exception as exc:
        logger.error(f"Erreur create_consultation: {exc}")
        return JsonResponse({"error": "Une erreur interne s'est produite."}, status=500)


@login_required
def consultation_detail(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    all_consultations = Consultation.objects.select_related("animal", "animal__client").order_by("-date")

    return render(request, "consultations/detail_consultation.html", {
        "consultation": consultation,
        "all_consultations": all_consultations
    })


@login_required
@require_POST
def terminer_consultation(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)

    if consultation.statut == "terminee":
        return redirect("consultation_detail", consultation_id=consultation.id)

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

    try:
        with transaction.atomic():
            # Vérification préalable des stocks
            for ligne in ordonnance.lignes.select_related("medicament").select_for_update():
                if ligne.medicament.stock < ligne.quantite:
                    messages.error(
                        request,
                        f"Stock insuffisant pour {ligne.medicament}. Stock actuel: {ligne.medicament.stock}"
                    )
                    return redirect("ordonnance_detail", ordonnance_id=ordonnance.id)

            vente = Vente.objects.create(
                ordonnance=ordonnance,
                total=0
            )

            total = 0
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

                # Déduction de stock sécurisée
                med = ligne.medicament
                med.stock -= ligne.quantite
                med.save()

            vente.total = total
            vente.save()

            consultation.statut = "terminee"
            consultation.save()

        return redirect("vente_detail", vente_id=vente.id)

    except Exception as exc:
        logger.error(f"Erreur terminer_consultation: {exc}")
        messages.error(request, "Une erreur est survenue lors de la validation de la consultation.")
        return redirect("consultation_detail", consultation_id=consultation.id)


@login_required
def edit_consultation(request, id):
    consultation = get_object_or_404(
        Consultation.objects.select_related("client", "animal"),
        id=id
    )

    if consultation.statut == "terminee":
        messages.warning(
            request,
            "Cette consultation est terminée et ne peut plus être modifiée."
        )
        return redirect("consultation_detail", consultation_id=consultation.id)

    client = consultation.client
    animal = consultation.animal

    if request.method == "POST":
        if consultation.client_nouveau:
            client_nom = request.POST.get("client_nom", "").strip()
            telephone = request.POST.get("telephone", "").strip()
            adresse = request.POST.get("adresse", "").strip()

            if not client_nom:
                messages.error(request, "Le nom du client est obligatoire.")
                return redirect("edit_consultation", id=consultation.id)

            if telephone and Client.objects.filter(
                telephone=telephone
            ).exclude(id=client.id).exists():
                messages.error(
                    request,
                    "Ce numéro de téléphone est déjà utilisé par un autre client."
                )
                return redirect("edit_consultation", id=consultation.id)
        else:
            client_nom = client.nom
            telephone = client.telephone or ""
            adresse = client.adresse or ""

        animal_nom = request.POST.get("animal_nom", "").strip()
        espece = request.POST.get("espece", "").strip()
        race = request.POST.get("race", "").strip()
        sexe = request.POST.get("sexe", "").strip()
        animal_poids_raw = request.POST.get("animal_poids", "").strip()

        if not animal_nom or not espece:
            messages.error(request, "Le nom et l'espèce de l'animal sont obligatoires.")
            return redirect("edit_consultation", id=consultation.id)

        if sexe and sexe not in ["M", "F"]:
            messages.error(request, "Le sexe de l'animal est invalide.")
            return redirect("edit_consultation", id=consultation.id)

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
                if consultation.client_nouveau:
                    client.nom = client_nom
                    client.telephone = telephone or None
                    client.adresse = adresse or None
                    client.save()

                animal.client = client
                animal.nom = animal_nom
                animal.espece = espece
                animal.race = race or None
                animal.sexe = sexe or None
                animal.poids = animal_poids
                animal.save()

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
            logger.error(f"Erreur edit_consultation: {exc}")
            messages.error(request, "Une erreur s'est produite lors de la modification.")
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

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Consultation  # Ajustez selon le nom exact de votre modèle

# ==========================================
# Endpoints API JSON pour Consultations
# ==========================================

def api_consultations_liste(request):
    """GET /consultations/api/liste/"""
    consultations = Consultation.objects.all().order_by("-id")
    data = []
    for c in consultations:
        data.append({
            "id": c.id,
            "statut": getattr(c, "statut", ""),
            "date": c.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(c, "created_at") and c.created_at else "",
            # Ajoutez ici les autres champs nécessaires à votre application Flutter
        })
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def api_ajouter_consultation(request):
    """POST /consultations/api/ajouter/"""
    try:
        data = json.loads(request.body)
        # Logique de création de consultation ici
        return JsonResponse({"message": "Consultation créée avec succès"}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST", "PUT"])
def api_modifier_statut_consultation(request, consultation_id):
    """POST/PUT /consultations/api/<id>/statut/"""
    try:
        consultation = Consultation.objects.get(pk=consultation_id)
        data = json.loads(request.body)
        consultation.statut = data.get("statut", consultation.statut)
        consultation.save()
        return JsonResponse({"id": consultation.id, "statut": consultation.statut})
    except Consultation.DoesNotExist:
        return JsonResponse({"error": "Consultation introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def ordonnance_detail(request, ordonnance_id):
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


@login_required
@require_POST
def ajouter_ligne_ordonnance(request, ordonnance_id):
    ordonnance = get_object_or_404(Ordonnance, id=ordonnance_id)

    if ordonnance.consultation.statut == "terminee":
        return JsonResponse(
            {"error": "Consultation terminée — ordonnance verrouillée."},
            status=403,
        )

    try:
        data = json.loads(request.body)
        med = get_object_or_404(Medicament, id=data.get('medicament_id'))
        
        quantite = int(data.get('quantite', 1))
        if quantite <= 0:
            return JsonResponse({"error": "Quantité invalide."}, status=400)

        ligne = LigneOrdonnance.objects.create(
            ordonnance=ordonnance,
            medicament=med,
            quantite=quantite,
            posologie=data.get('posologie', '').strip()
        )
        return JsonResponse({"id": ligne.id})
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Requête invalide."}, status=400)


@login_required
@require_http_methods(["POST", "PUT"])
def modifier_ligne_ordonnance(request, ligne_id):
    ligne = get_object_or_404(
        LigneOrdonnance.objects.select_related("ordonnance__consultation", "medicament"),
        id=ligne_id
    )

    if ligne.ordonnance.consultation.statut == "terminee":
        return JsonResponse(
            {"error": "Consultation terminée — ordonnance verrouillée."},
            status=403
        )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"error": "Données JSON invalides."}, status=400)

    quantite_raw = data.get("quantite")
    posologie = str(data.get("posologie", "")).strip()

    try:
        quantite = int(quantite_raw)
        if quantite <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return JsonResponse({"error": "La quantité doit être un entier positif."}, status=400)

    if not posologie:
        return JsonResponse({"error": "La posologie est obligatoire."}, status=400)

    medicament_id = data.get("medicament_id")
    if medicament_id:
        medicament = get_object_or_404(Medicament, id=medicament_id)
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


@login_required
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


@login_required
def ordonnance_create(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    ordonnance, _ = Ordonnance.objects.get_or_create(consultation=consultation)

    return redirect("ordonnance_detail", ordonnance_id=ordonnance.id)


@login_required
def ordonnance_pdf(request, ordonnance_id):
    ordonnance = get_object_or_404(
        Ordonnance.objects.select_related("consultation__client", "consultation__animal"),
        id=ordonnance_id
    )
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

    titre_style = ParagraphStyle(
        "TitreOrdonnance",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=16,
    )
    elements.append(Paragraph("<u><b>ORDONNANCE</b></u>", titre_style))
    elements.append(Spacer(1, 0.8 * cm))

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


@login_required
def animaux_client(request, client_id):
    animaux = Animal.objects.filter(client_id=client_id)
    data = [
        {
            "id": a.id,
            "nom": a.nom,
            "espece": a.espece,
        }
        for a in animaux
    ]
    return JsonResponse(data, safe=False)


import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Consultation, RendezVous, Ordonnance  # Ajustez selon vos modèles


# ==========================================
# Endpoints API — Consultations
# ==========================================

def api_consultations_liste(request):
    """GET /consultations/api/liste/"""
    consultations = Consultation.objects.all().order_by("-id")
    data = [
        {
            "id": c.id,
            "statut": getattr(c, "statut", ""),
            "motif": getattr(c, "motif", ""),
        }
        for c in consultations
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def api_ajouter_consultation(request):
    """POST /consultations/api/ajouter/"""
    try:
        data = json.loads(request.body)
        consultation = Consultation.objects.create(
            motif=data.get("motif", ""),
            # Ajoutez ici les autres champs requis par votre modèle Consultation
        )
        return JsonResponse({"id": consultation.id, "message": "Consultation créée avec succès"}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST", "PUT"])
def api_modifier_statut_consultation(request, consultation_id):
    """POST/PUT /consultations/api/<id>/statut/"""
    try:
        consultation = Consultation.objects.get(pk=consultation_id)
        data = json.loads(request.body)
        consultation.statut = data.get("statut", consultation.statut)
        consultation.save()
        return JsonResponse({"id": consultation.id, "statut": consultation.statut})
    except Consultation.DoesNotExist:
        return JsonResponse({"error": "Consultation introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_terminer_consultation(request, consultation_id):
    """POST /consultations/api/<id>/terminer/"""
    try:
        consultation = Consultation.objects.get(pk=consultation_id)
        # Logique pour terminer la consultation, créer la vente et déduire du stock
        setattr(consultation, "statut", "TERMINEE")
        consultation.save()
        return JsonResponse({"message": "Consultation terminée avec succès"})
    except Consultation.DoesNotExist:
        return JsonResponse({"error": "Consultation introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ==========================================
# Endpoints API — Rendez-vous (RDV)
# ==========================================

def api_rdv_liste(request):
    """GET /consultations/api/rdv/"""
    rdvs = RendezVous.objects.all().order_by("-id")
    data = [
        {
            "id": r.id,
            "statut": getattr(r, "statut", ""),
            "note": getattr(r, "note", ""),
        }
        for r in rdvs
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def api_ajouter_rdv_manuel(request):
    """POST /consultations/api/rdv/ajouter/"""
    try:
        data = json.loads(request.body)
        rdv = RendezVous.objects.create(
            note=data.get("note", ""),
            # Ajoutez ici les autres champs de votre modèle RendezVous
        )
        return JsonResponse({"id": rdv.id, "message": "Rendez-vous créé"}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST", "PUT"])
def api_modifier_statut_rdv(request, rdv_id):
    """POST/PUT /consultations/api/rdv/<id>/statut/"""
    try:
        rdv = RendezVous.objects.get(pk=rdv_id)
        data = json.loads(request.body)
        rdv.statut = data.get("statut", rdv.statut)
        rdv.save()
        return JsonResponse({"id": rdv.id, "statut": rdv.statut})
    except RendezVous.DoesNotExist:
        return JsonResponse({"error": "Rendez-vous introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ==========================================
# Endpoints API — Ordonnances
# ==========================================

def api_ordonnance_detail(request, consultation_id):
    """GET /consultations/api/<consultation_id>/ordonnance/"""
    try:
        ordonnance = Ordonnance.objects.get(consultation_id=consultation_id)
        data = {
            "id": ordonnance.id,
            "consultation_id": consultation_id,
            # Ajoutez la structure de votre ordonnance
        }
        return JsonResponse(data)
    except Ordonnance.DoesNotExist:
        return JsonResponse({"error": "Ordonnance introuvable pour cette consultation"}, status=404)