from django.shortcuts import render
from rest_framework import viewsets
from .models import Animal
from .serializers import AnimalSerializer
from consultations.models import RendezVous, Ordonnance, Consultation
from django.shortcuts import render, get_object_or_404
from .models import Animal
from consultations.models import Consultation
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods




# ===== API =====
class AnimalViewSet(viewsets.ModelViewSet):
    queryset = Animal.objects.all().order_by('-id')
    serializer_class = AnimalSerializer


# ===== PAGE HTML =====
def animaux_list(request):
    animaux = Animal.objects.all().order_by('-id')

    return render(request, "animaux/list.html", {
        "animaux": animaux,
        "active_page": "animaux",
    })


@require_POST
def ajouter_animal(request):
    client_id = request.POST.get("client_id")
    nom = request.POST.get("nom")
    espece = request.POST.get("espece")

    client = Client.objects.get(pk=client_id)

    animal = Animal.objects.create(
        client=client,
        nom=nom,
        espece=espece,
    )

    return JsonResponse({
        "success": True,
        "id": animal.id,
        "nom": animal.nom,
    })

def historique_animal(request, animal_id):
    animal = get_object_or_404(Animal, id=animal_id)

    consultations = Consultation.objects.filter(animal=animal).order_by("-date")
    rendezvous = RendezVous.objects.filter(animal=animal).order_by("-date_rdv")

    ordonnances = Ordonnance.objects.filter(
        consultation__animal=animal
    ).select_related("consultation").order_by("-date_creation")

    return render(request, "animaux/historique_animal.html", {
        "animal": animal,
        "consultations": consultations,
        "rendezvous": rendezvous,
        "ordonnances": ordonnances,
    })

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def api_animaux_list(request):
    animaux = Animal.objects.select_related('client').all().order_by('-id')
    data = [{
        "id": a.id,
        "nom": a.nom,
        "espece": a.espece,
        "race": a.race or "",
        "sexe": a.sexe or "",
        "poids": a.poids or 0,
        "client": a.client.nom,
    } for a in animaux]
    return JsonResponse(data, safe=False)

# ── À ajouter à la fin de animaux/views.py ───────────────────────────────────
# Ces 4 endpoints remplacent le dialog "sans API" de l'AnimauxScreen Flutter.

import json
from clients.models import Client

def api_liste_animaux(request):
    """GET /animaux/api/liste/ — liste complète avec nom du client."""
    qs = Animal.objects.select_related("client").order_by("-id")

    # Filtre optionnel par client
    client_id = request.GET.get("client_id")
    if client_id:
        qs = qs.filter(client_id=client_id)

    data = []
    for a in qs:
        data.append({
            "id": a.id,
            "nom": a.nom,
            "espece": a.espece or "",
            "race": a.race or "",
            "sexe": a.sexe or "",
            "poids": a.poids or 0,
            "client": a.client.nom if a.client else "",
            "client_id": a.client_id,
        })
    return JsonResponse(data, safe=False)


@require_http_methods(["POST"])
def api_ajouter_animal(request):
    """POST /animaux/api/ajouter/"""
    try:
        data = json.loads(request.body)
        client = Client.objects.get(pk=data.get("client_id"))
        animal = Animal.objects.create(
            client=client,
            nom=data.get("nom", ""),
            espece=data.get("espece", ""),
            race=data.get("race", ""),
            sexe=data.get("sexe", ""),
            poids=data.get("poids") or None,
        )
        return JsonResponse({
            "id": animal.id,
            "nom": animal.nom,
            "espece": animal.espece,
        }, status=201)
    except Client.DoesNotExist:
        return JsonResponse({"error": "Client introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@require_http_methods(["PUT"])
def api_modifier_animal(request, animal_id):
    """PUT /animaux/api/<id>/modifier/"""
    try:
        animal = Animal.objects.get(pk=animal_id)
        data = json.loads(request.body)
        animal.nom = data.get("nom", animal.nom)
        animal.espece = data.get("espece", animal.espece)
        animal.race = data.get("race", animal.race)
        animal.sexe = data.get("sexe", animal.sexe)
        animal.poids = data.get("poids") or animal.poids
        if data.get("client_id"):
            animal.client = Client.objects.get(pk=data["client_id"])
        animal.save()
        return JsonResponse({"id": animal.id, "nom": animal.nom})
    except Animal.DoesNotExist:
        return JsonResponse({"error": "Animal introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@require_http_methods(["DELETE"])
def api_supprimer_animal(request, animal_id):
    """DELETE /animaux/api/<id>/supprimer/"""
    try:
        animal = Animal.objects.get(pk=animal_id)
        animal.delete()
        return JsonResponse({"success": True})
    except Animal.DoesNotExist:
        return JsonResponse({"error": "Animal introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)