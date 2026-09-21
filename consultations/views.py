import json
import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST, require_GET

from rest_framework import permissions, viewsets

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
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

# =============================================================================
# ===== API VIEWSETS (REST Framework) =====
# =============================================================================

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


# =============================================================================
# ===== PAGES HTML & CONTRÔLEURS WEB =====
# =============================================================================

@login_required
def liste_consultations(request):
    consultations = Consultation.objects.select_related(
        "animal", "animal__client"
    ).order_by("-date")

    search = request.GET.get("search", "").strip()
    statut_filter = request.GET.get("statut", "").strip()

    if search:
        consultations = consultations.filter(
            Q(animal__client__nom__icontains=search) |
            Q(animal__nom__icontains=search) |
            Q(animal__espece__icontains=search) |
            Q(motif__icontains=search)
        )

    if statut_filter:
        consultations = consultations.filter(statut__iexact=statut_filter)

    total = consultations.count()
    en_cours = Consultation.objects.filter(statut__iexact="en_cours").count()
    terminees = Consultation.objects.filter(statut__iexact="terminee").count()
    annulees = Consultation.objects.filter(statut__iexact="annulee").count()

    return render(request, "consultations/liste_consultation.html", {
        "consultations": consultations,
        "total": total,
        "en_cours": en_cours,
        "terminees": terminees,
        "annulees": annulees,
        "search": search,
        "current_statut": statut_filter,
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

    nb_attente = tous_rdv.filter(statut="EN_ATTENTE").count() + tous_manuels.filter(statut="EN_ATTENTE").count()
    nb_confirme = tous_rdv.filter(statut="CONFIRME").count() + tous_manuels.filter(statut="CONFIRME").count()
    nb_annule = tous_rdv.filter(statut="ANNULE").count() + tous_manuels.filter(statut="ANNULE").count()

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
        return JsonResponse({
            'status': 'OK',
            'message': 'Consultation déjà terminée.',
            'redirect_url': reverse("consultation_detail", kwargs={'consultation_id': consultation.id})
        })

    ordonnance = Ordonnance.objects.filter(consultation=consultation).first()

    if not ordonnance:
        return JsonResponse({
            'error': "Aucune ordonnance n'a été trouvée pour cette consultation.",
            'redirect_url': reverse("ordonnance_create", kwargs={'consultation_id': consultation.id})
        }, status=400)

    if not ordonnance.lignes.exists():
        return JsonResponse({
            'error': "Impossible de terminer la consultation : l'ordonnance doit contenir au moins un médicament."
        }, status=400)

    try:
        with transaction.atomic():
            for ligne in ordonnance.lignes.select_related("medicament").select_for_update():
                if ligne.medicament.stock < ligne.quantite:
                    nom_med = ligne.medicament.catalogue.nom if hasattr(ligne.medicament, 'catalogue') and ligne.medicament.catalogue else str(ligne.medicament)
                    return JsonResponse({
                        'error': f"Stock insuffisant pour {nom_med}. Stock actuel : {ligne.medicament.stock}"
                    }, status=400)

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

                med = ligne.medicament
                med.stock -= ligne.quantite
                med.save()

            vente.total = total
            vente.save()

            consultation.statut = "terminee"
            consultation.save()

        return JsonResponse({
            'status': 'OK',
            'message': 'Consultation terminée avec succès.',
            'redirect_url': reverse("vente_detail", kwargs={'vente_id': vente.id})
        })

    except Exception as exc:
        logger.error(f"Erreur terminer_consultation: {exc}")
        return JsonResponse({
            'error': "Une erreur est survenue lors de la validation de la consultation."
        }, status=500)


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
        if getattr(consultation, 'client_nouveau', False):
            client_nom = request.POST.get("client_nom", "").strip()
            telephone = request.POST.get("telephone", "").strip()
            adresse = request.POST.get("adresse", "").strip()

            if not client_nom:
                messages.error(request, "Le nom du client est obligatoire.")
                return redirect("edit_consultation", id=consultation.id)

            if telephone and Client.objects.filter(telephone=telephone).exclude(id=client.id).exists():
                messages.error(
                    request,
                    "Ce numéro de téléphone est déjà utilisé par un autre client."
                )
                return redirect("edit_consultation", id=consultation.id)
        else:
            client_nom = client.nom if client else ""
            telephone = client.telephone or "" if client else ""
            adresse = client.adresse or "" if client else ""

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
            consultation_poids = parse_weight(consultation_poids_raw, "poids de la consultation")
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("edit_consultation", id=consultation.id)

        try:
            with transaction.atomic():
                if client and getattr(consultation, 'client_nouveau', False):
                    client.nom = client_nom
                    client.telephone = telephone or None
                    client.adresse = adresse or None
                    client.save()

                if animal:
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

        messages.success(request, "La consultation a été modifiée avec succès.")
        return redirect("consultation_detail", consultation_id=consultation.id)

    return render(request, "consultations/edit_consultation.html", {
        "consultation": consultation,
        "client": client,
        "animal": animal,
    })


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


@csrf_exempt
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

        return JsonResponse({
            "id": ligne.id,
            "message": "Médicament ajouté avec succès à l'ordonnance."
        }, status=201)

    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Format JSON ou requête invalide."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


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


# =============================================================================
# ===== ENDPOINTS API FLUTTER (MOBILE) =====
# =============================================================================

@csrf_exempt
@require_POST
def api_creer_consultation(request):
    try:
        data = json.loads(request.body)
        
        nom_client = data.get("nom_client", "")
        telephone = data.get("telephone", "")
        adresse = data.get("adresse", "")
        
        nom_animal = data.get("nom_animal", "")
        espece = data.get("espece", "")
        
        motif = data.get("motif", "")
        observations = data.get("observations", "")
        lieu = data.get("lieu", "cabinet")

        # 1. Récupération / Création du client
        client, _ = Client.objects.get_or_create(
            telephone=telephone,
            defaults={"nom": nom_client, "adresse": adresse}
        )

        # 2. Récupération / Création de l'animal
        animal, _ = Animal.objects.get_or_create(
            client=client,
            nom=nom_animal,
            defaults={"espece": espece}
        )

        # 3. Création de la consultation
        consultation = Consultation.objects.create(
            client=client,
            animal=animal,
            motif=motif,
            observations=observations,
            lieu=lieu,
            statut="en_cours"
        )

        return JsonResponse({
            "status": "success",
            "message": "Consultation créée avec succès",
            "consultation_id": consultation.id
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Format JSON invalide"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def api_consultations_liste(request):
    consultations = Consultation.objects.select_related('client', 'animal').all()
    data = []
    for c in consultations:
        data.append({
            'id': c.id,
            'statut': c.statut,
            'motif': c.motif,
            'client_nom': str(c.client) if c.client else "Non renseigné",
            'animal_nom': str(c.animal) if c.animal else "Non renseigné",
        })
    return JsonResponse(data, safe=False)


def api_ordonnance_detail(request, consultation_id):
    try:
        consultation = get_object_or_404(Consultation, id=consultation_id)
        ordonnance, _ = Ordonnance.objects.get_or_create(consultation=consultation)

        date_str = "—"
        if hasattr(consultation, 'date') and consultation.date:
            date_str = consultation.date.strftime("%d/%m/%Y")
        elif hasattr(consultation, 'created_at') and consultation.created_at:
            date_str = consultation.created_at.strftime("%d/%m/%Y")

        consultation_data = {
            "id": consultation.id,
            "statut": consultation.statut,
            "animal": consultation.animal.nom if consultation.animal else "—",
            "espece": getattr(consultation.animal, 'espece', '') if consultation.animal else "",
            "client": consultation.client.nom if consultation.client else "—",
            "motif": consultation.motif or "—",
            "date": date_str,
        }

        lignes = LigneOrdonnance.objects.filter(ordonnance=ordonnance).select_related('medicament')
        lignes_data = []
        for l in lignes:
            nom_med = l.medicament.catalogue.nom if hasattr(l.medicament, 'catalogue') and l.medicament.catalogue else str(l.medicament)
            lignes_data.append({
                'id': l.id,
                'medicament_id': l.medicament.id,
                'medicament_nom': nom_med,
                'posologie': l.posologie or "",
                'quantite': getattr(l, 'quantite', 1),
            })

        meds_dispo = Medicament.objects.filter(stock__gt=0).select_related('catalogue')
        medicaments_disponibles = []
        for m in meds_dispo:
            nom_med_dispo = m.catalogue.nom if hasattr(m, 'catalogue') and m.catalogue else str(m)
            medicaments_disponibles.append({
                'id': m.id,
                'nom': nom_med_dispo,
                'stock': m.stock,
                'prix': float(m.prix) if hasattr(m, 'prix') and m.prix else 0.0
            })

        data = {
            'ordonnance_id': ordonnance.id,
            'consultation': consultation_data,
            'lignes': lignes_data,
            'medicaments_disponibles': medicaments_disponibles,
        }
        return JsonResponse(data)

    except Consultation.DoesNotExist:
        return JsonResponse({'error': 'Consultation introuvable'}, status=404)
    except Exception as e:
        logger.error(f"Erreur api_ordonnance_detail: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def api_sauvegarder_ordonnance(request):
    """
    Endpoint POST utilisé par Flutter pour sauvegarder l'ordonnance complète.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        consultation_id = data.get('consultation_id')
        medicaments = data.get('medicaments', [])

        consultation = get_object_or_404(Consultation, id=consultation_id)
        ordonnance, _ = Ordonnance.objects.get_or_create(consultation=consultation)

        with transaction.atomic():
            # Remplacement des lignes d'ordonnance actuelles
            ordonnance.lignes.all().delete()
            for item in medicaments:
                med_id = item.get('medicament_id') or item.get('id')
                quantite = item.get('quantite', 1)
                posologie = item.get('posologie', '')

                if med_id:
                    med = get_object_or_404(Medicament, id=med_id)
                    LigneOrdonnance.objects.create(
                        ordonnance=ordonnance,
                        medicament=med,
                        quantite=quantite,
                        posologie=posologie
                    )

        return JsonResponse({'status': 'success', 'message': 'Ordonnance enregistrée avec succès.'})
    except Exception as e:
        logger.error(f"Erreur api_sauvegarder_ordonnance: {e}")
        return JsonResponse({'error': str(e)}, status=500)



import json
import logging
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Remplacez par vos imports de modèles
from .models import Client, Animal, Consultation, Ordonnance

logger = logging.getLogger(__name__)


@csrf_exempt  # 👈 Indispensable pour éviter l'erreur 403 depuis Flutter / API
@require_http_methods(["POST"])
def api_ajouter_consultation(request):
    """
    Création d'une consultation compatible Web & Mobile.
    Modes pris en compte:
      - mode == 'nouveau' : Nouveau client + Nouvel animal
      - mode == 'existant' : Client existant avec animal existant OU 'NEW_ANIMAL'
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        mode = data.get("mode") or data.get("mode_creation")

        client = None
        animal = None
        client_nouveau = False

        with transaction.atomic():
            # CAS 1 : NOUVEAU CLIENT
            if mode == "nouveau":
                client_nouveau = True
                nom_client = str(data.get("nom_client") or data.get("client_nom") or "").strip()
                tel_client = str(data.get("telephone") or data.get("client_tel") or "").strip()
                adresse_client = str(data.get("adresse") or data.get("client_adresse") or "").strip()

                if not nom_client:
                    return JsonResponse({"error": "Le nom du client est obligatoire."}, status=400)

                client = Client.objects.create(
                    nom=nom_client,
                    telephone=tel_client,
                    adresse=adresse_client
                )

                nom_animal = str(data.get("nom_animal") or data.get("animal_nom") or "").strip()
                if not nom_animal:
                    return JsonResponse({"error": "Le nom de l'animal est obligatoire."}, status=400)

                animal = Animal.objects.create(
                    client=client,
                    nom=nom_animal,
                    espece=data.get("espece") or data.get("animal_espece") or "Chien",
                    race=data.get("race") or data.get("animal_race") or "",
                    sexe=data.get("sexe") or data.get("animal_sexe") or "M"
                )

            # CAS 2 : CLIENT EXISTANT
            elif mode == "existant":
                client_id = data.get("client_id")
                animal_id = data.get("animal_id")

                if not client_id:
                    return JsonResponse({"error": "L'identifiant du client est requis."}, status=400)

                client = get_object_or_404(Client, id=client_id)

                # Option : Création d'un NOUVEL animal pour ce client existant
                if str(animal_id) in ["NEW_ANIMAL", "", "None"] or not animal_id:
                    nom_animal = str(data.get("nom_animal") or data.get("animal_nom") or "").strip()
                    if not nom_animal:
                        return JsonResponse({"error": "Le nom du nouvel animal est requis."}, status=400)

                    animal = Animal.objects.create(
                        client=client,
                        nom=nom_animal,
                        espece=data.get("espece") or data.get("animal_espece") or "Chien",
                        race=data.get("race") or data.get("animal_race") or "",
                        sexe=data.get("sexe") or data.get("animal_sexe") or "M"
                    )
                # Option : Sélection d'un animal EXISTANT dans la liste du client
                else:
                    animal = get_object_or_404(Animal, id=animal_id, client=client)

            else:
                return JsonResponse({"error": "Mode de création non spécifié ou invalide (attendu: 'nouveau' ou 'existant')."}, status=400)

            # Traitement du poids
            poids_raw = data.get("poids") or data.get("animal_poids")
            poids_val = None
            if poids_raw is not None and str(poids_raw).strip() != "":
                try:
                    poids_val = float(poids_raw)
                except (ValueError, TypeError):
                    poids_val = None

            # Création de la consultation
            consultation = Consultation.objects.create(
                client=client,
                animal=animal,
                veterinaire=data.get("veterinaire", "Dr Ibrahima Pierre GUISSE"),
                motif=str(data.get("motif", "")).strip(),
                observations=str(data.get("observations", "")).strip(),
                lieu=data.get("lieu", "cabinet"),
                poids=poids_val,
                statut="en_cours",
                client_nouveau=client_nouveau,
            )

            # Création de l'ordonnance rattachée
            ordonnance = Ordonnance.objects.create(consultation=consultation)

        return JsonResponse({
            "status": "success",
            "message": "Consultation créée avec succès.",
            "consultation_id": consultation.id,
            "ordonnance_id": ordonnance.id,
            "client_id": client.id,
            "client_nom": client.nom,
            "animal_id": animal.id,
            "animal_nom": animal.nom
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Format JSON invalide."}, status=400)
    except Exception as exc:
        logger.exception("Erreur lors de la création de la consultation")
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_animaux_client(request, client_id):
    """
    API pour récupérer la liste des animaux d'un client existant
    afin de charger le menu déroulant côté Web/Mobile.
    """
    client = get_object_or_404(Client, id=client_id)
    animaux = list(client.animaux.values("id", "nom", "espece", "race"))
    
    # Ajout automatique de l'option 'Créer un nouvel animal'
    animaux.append({
        "id": "NEW_ANIMAL",
        "nom": "➕ Ajouter un nouvel animal",
        "espece": "",
        "race": ""
    })
    
    return JsonResponse({"animaux": animaux}, status=200)

@csrf_exempt
@require_http_methods(["POST", "PUT"])
def api_modifier_statut_consultation(request, consultation_id):
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


def api_clients_liste(request):
    clients = Client.objects.all()
    data = [{'id': c.id, 'nom': c.nom, 'telephone': c.telephone} for c in clients]
    return JsonResponse(data, safe=False)


def animaux_client(request, client_id):
    animaux = Animal.objects.filter(client_id=client_id)
    data = [{'id': a.id, 'nom': a.nom, 'espece': getattr(a, 'espece', '')} for a in animaux]
    return JsonResponse(data, safe=False)


def api_rdv_liste(request):
    rdvs = RendezVous.objects.select_related('animal', 'animal__client').all()
    data = []
    for r in rdvs:
        data.append({
            'id': r.id,
            'date_rdv': r.date_rdv.strftime("%Y-%m-%d %H:%M"),
            'motif': r.motif,
            'statut': r.statut,
            'client': str(r.animal.client) if r.animal and r.animal.client else "—",
            'animal': str(r.animal) if r.animal else "—"
        })
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_POST
def api_ajouter_rdv(request):
    try:
        data = json.loads(request.body)
        return JsonResponse({"message": "Rendez-vous ajouté"}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_POST
def api_ajouter_rdv_manuel(request):
    try:
        data = json.loads(request.body)
        return JsonResponse({"message": "Rendez-vous manuel ajouté"}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST", "PUT"])
def api_modifier_statut_rdv(request, rdv_id):
    try:
        rdv = RendezVous.objects.get(pk=rdv_id)
        data = json.loads(request.body)
        rdv.statut = data.get("statut", rdv.statut)
        rdv.save()
        return JsonResponse({"id": rdv.id, "statut": rdv.statut})
    except RendezVous.DoesNotExist:
        return JsonResponse({"error": "RDV introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# =============================================================================
# ===== GÉNÉRATION PDF (REPORTLAB COMPLÈTE) =====
# =============================================================================

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
    response["Content-Disposition"] = f'inline; filename="ordonnance_{ordonnance.id}.pdf"'

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

    # En-tête du cabinet
    gauche = Paragraph(
        """
        <b><font size="16" color="#1a365d">PARCELLES VETO</font></b><br/>
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
    date_creation = getattr(ordonnance, 'date_creation', timezone.now())
    droite = Paragraph(
        f"""
        <b>Date :</b><br/>
        {date_creation.strftime("%d/%m/%Y")}
        """,
        droite_style,
    )

    header = Table([[gauche, droite]], colWidths=[12 * cm, 6 * cm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(header)
    elements.append(Spacer(1, 0.6 * cm))

    # Titre
    titre_style = ParagraphStyle(
        "TitreOrdonnance",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=16,
    )
    elements.append(Paragraph("<u><b>ORDONNANCE VÉTÉRINAIRE</b></u>", titre_style))
    elements.append(Spacer(1, 0.8 * cm))

    # Bloc informations Client / Animal
    info_text = f"""
    <b>Propriétaire :</b> {client.nom if client else 'Non renseigné'}<br/>
    <b>Téléphone :</b> {client.telephone if client and client.telephone else '—'}<br/>
    <b>Nom de l'animal :</b> {animal.nom if animal else 'Non renseigné'}<br/>
    <b>Espèce / Race :</b> {getattr(animal, 'espece', '—')} / {getattr(animal, 'race', '—')}<br/>
    """
    elements.append(Paragraph(info_text, styles["Normal"]))
    elements.append(Spacer(1, 0.8 * cm))

    # Tableau des prescriptions
    table_data = [["Médicament", "Quantité", "Posologie / Recommandations"]]
    for ligne in ordonnance.lignes.select_related("medicament").all():
        nom_med = ligne.medicament.catalogue.nom if hasattr(ligne.medicament, 'catalogue') and ligne.medicament.catalogue else str(ligne.medicament)
        table_data.append([
            Paragraph(nom_med, styles["Normal"]),
            str(ligne.quantite),
            Paragraph(ligne.posologie or "—", styles["Normal"])
        ])

    table = Table(table_data, colWidths=[6 * cm, 2.5 * cm, 9.5 * cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a365d")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 1.5 * cm))

    # Cachet et Signature
    sig_style = ParagraphStyle("SigStyle", parent=styles["Normal"], alignment=TA_RIGHT)
    elements.append(Paragraph("<b>Le Vétérinaire (Cachet & Signature)</b>", sig_style))

    doc.build(elements)
    return response