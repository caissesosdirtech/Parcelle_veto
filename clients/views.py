from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from .models import Client
from animaux.models import Animal
from reportlab.pdfgen import canvas
from openpyxl import Workbook
from .serializers import ClientSerializer
from rest_framework import viewsets
from consultations.models import Consultation, RendezVous
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from clients.models import Client
from consultations.models import Ordonnance


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

def api_clients_list(request):

    search = request.GET.get("search", "")
    espece = request.GET.get("espece", "")
    page = int(request.GET.get("page", 1))

    qs = Client.objects.prefetch_related("animaux").annotate(
        nb_animaux=Count("animaux")
    )

    # 🔎 RECHERCHE (nom, téléphone, adresse + animaux)
    if search:
        qs = qs.filter(
            Q(nom__icontains=search) |
            Q(telephone__icontains=search) |
            Q(adresse__icontains=search) |
            Q(animaux__nom__icontains=search) |
            Q(animaux__espece__icontains=search)
        ).distinct()

    # 🧠 FILTRE PAR ESPÈCE
    if espece:
        qs = qs.filter(
            animaux__espece=espece
        ).distinct()

    paginator = Paginator(qs, 5)
    page_obj = paginator.get_page(page)

    data = []
    total_animaux_page = 0

    for c in page_obj:
        animaux = list(c.animaux.all())
        total_animaux_page += len(animaux)

        data.append({
            "id": c.id,
            "nom": c.nom,
            "telephone": c.telephone,
            "adresse": c.adresse,
            "nb_animaux": len(animaux),
            "animaux": [
                {
                    "id": a.id,          # ✅ Ajout de l'identifiant de l'animal
                    "nom": a.nom,
                    "espece": a.espece,
                    "race": a.race,
                    "sexe": a.sexe,
                    "poids": a.poids,
                }
                for a in animaux
            ]
        })

    return JsonResponse({
        "results": data,
        "page": page_obj.number,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),

        # 📊 Statistiques globales
        "total_clients": Client.objects.count(),
        "total_animaux": Animal.objects.count(),

        # 📄 Nombre d'animaux affichés sur la page courante
        "total_animaux_page": total_animaux_page,
    })

from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q, Count

from .models import Client
from animaux.models import Animal   # ✅ IMPORTANT (corrige ton erreur)

def clients_list(request):

    search = request.GET.get("search", "")

    clients_qs = Client.objects.prefetch_related("animaux").annotate(
        nb_animaux=Count("animaux")
    )

    if search:
        clients_qs = clients_qs.filter(
            Q(nom__icontains=search) |
            Q(telephone__icontains=search) |
            Q(adresse__icontains=search) |
            Q(animaux__nom__icontains=search) |
            Q(animaux__espece__icontains=search)
        ).distinct()

    paginator = Paginator(clients_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "clients/liste_client.html", {
        "clients": page_obj,
        "page_obj": page_obj,
        "search": search,
        "active_page": "clients",
    })


def historique_client(request, client_id):

    client = get_object_or_404(Client, id=client_id)

    animaux = Animal.objects.filter(client=client)

    consultations = Consultation.objects.filter(client=client).order_by("-date")

    rendezvous = RendezVous.objects.filter(animal__client=client).order_by("-date_rdv")

    ordonnances = Ordonnance.objects.filter(
        consultation__client=client
    ).order_by("-date_creation")

    return render(request, "clients/historique_client.html", {
        "client": client,
        "animaux": animaux,
        "consultations": consultations,
        "rendezvous": rendezvous,
        "ordonnances": ordonnances,
    })

def export_excel(request):

    wb = Workbook()
    ws = wb.active
    ws.title = "Clients"

    # headers
    ws.append(["Client", "Téléphone", "Adresse", "Animal", "Espèce", "Race"])

    for c in Client.objects.all():
        for a in c.animaux.all():
            ws.append([
                c.nom,
                c.telephone,
                c.adresse,
                a.nom,
                a.espece,
                a.race
            ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="clients.xlsx"'

    wb.save(response)
    return response


def export_pdf(request):

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="clients.pdf"'

    p = canvas.Canvas(response)

    y = 800

    for c in Client.objects.all():
        p.drawString(50, y, f"{c.nom} - {c.telephone} - {c.adresse}")
        y -= 20

        for a in c.animaux.all():
            p.drawString(70, y, f"🐾 {a.nom} ({a.espece})")
            y -= 15

        y -= 10

    p.save()
    return response

# ── À ajouter dans clients/views.py ─────────────────────────────────────────
# Ces 3 endpoints sont appelés par la ClientsScreen Flutter.
# Ajoutez-les à la fin du fichier existant.

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@csrf_exempt
@require_http_methods(["POST"])
def api_creer_client(request):
    """Créer un client depuis Flutter."""
    try:
        data = json.loads(request.body)
        client = Client.objects.create(
            nom=data.get('nom', ''),
            telephone=data.get('telephone', ''),
            adresse=data.get('adresse', ''),
        )
        return JsonResponse({'id': client.id, 'nom': client.nom}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
def api_modifier_client(request, client_id):
    """Modifier un client depuis Flutter."""
    try:
        client = Client.objects.get(id=client_id)
        data = json.loads(request.body)
        client.nom = data.get('nom', client.nom)
        client.telephone = data.get('telephone', client.telephone)
        client.adresse = data.get('adresse', client.adresse)
        client.save()
        return JsonResponse({'id': client.id, 'nom': client.nom})
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Client introuvable'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_supprimer_client(request, client_id):
    """Supprimer un client depuis Flutter."""
    try:
        client = Client.objects.get(id=client_id)
        client.delete()
        return JsonResponse({'success': True})
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Client introuvable'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
def api_clients_stats(request):
    from django.db.models import Count
    return JsonResponse({
        "total_clients": Client.objects.count(),
        "total_animaux": Animal.objects.count(),
    })    


# Ajoutez aussi en haut du fichier si absent : from django.utils import timezone

# ── À ajouter à la fin de clients/views.py ───────────────────────────────────
# Imports à ajouter en haut si absents :
# from animaux.models import Animal
# from consultations.models import Consultation, RendezVous, Ordonnance


def api_dossier_client(request, client_id):
    """
    GET /clients/api/<id>/dossier/
    Dossier complet : client + ses animaux, chaque animal avec ses
    consultations, chaque consultation avec son ordonnance (si existante).
    """
    client = get_object_or_404(Client, id=client_id)

    animaux = Animal.objects.filter(client=client).order_by("nom")

    animaux_data = []
    for animal in animaux:
        consultations = (
            Consultation.objects
            .filter(animal=animal)
            .order_by("-date")
        )

        consultations_data = []
        for c in consultations:
            ordonnance = Ordonnance.objects.filter(consultation=c).first()
            lignes_data = []
            if ordonnance:
                for ligne in ordonnance.lignes.select_related(
                    "medicament__catalogue"
                ).all():
                    lignes_data.append({
                        "medicament": ligne.medicament.catalogue.nom
                            if ligne.medicament.catalogue else str(ligne.medicament),
                        "quantite": ligne.quantite,
                        "posologie": ligne.posologie,
                    })

            consultations_data.append({
                "id": c.id,
                "date": c.date.strftime("%d/%m/%Y %H:%M"),
                "motif": c.motif or "",
                "observations": c.observations or "",
                "statut": c.statut,
                "lieu": c.lieu,
                "veterinaire": c.veterinaire or "",
                "poids": c.poids or 0,
                "ordonnance_id": ordonnance.id if ordonnance else None,
                "lignes_ordonnance": lignes_data,
            })

        animaux_data.append({
            "id": animal.id,
            "nom": animal.nom,
            "espece": animal.espece or "",
            "race": animal.race or "",
            "sexe": animal.sexe or "",
            "poids": animal.poids or 0,
            "nb_consultations": len(consultations_data),
            "consultations": consultations_data,
        })

    # Prochains RDV du client (tous animaux confondus)
    rdvs = (
        RendezVous.objects
        .filter(animal__client=client, date_rdv__gte=timezone.now())
        .order_by("date_rdv")
    )
    rdvs_data = [{
        "id": r.id,
        "animal": r.animal.nom,
        "date_rdv": r.date_rdv.strftime("%d/%m/%Y %H:%M"),
        "motif": r.motif or "",
        "statut": r.statut,
    } for r in rdvs]

    return JsonResponse({
        "client": {
            "id": client.id,
            "nom": client.nom,
            "telephone": client.telephone or "",
            "adresse": client.adresse or "",
        },
        "animaux": animaux_data,
        "prochains_rdv": rdvs_data,
        "total_animaux": len(animaux_data),
        "total_consultations": sum(a["nb_consultations"] for a in animaux_data),
    })
