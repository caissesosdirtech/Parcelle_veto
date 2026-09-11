import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets

from clients.models import Client
from .models import Animal
from .serializers import AnimalSerializer
from consultations.models import RendezVous, Ordonnance, Consultation


# ==========================================
# REST FRAMEWORK VIEWSETS
# ==========================================

class AnimalViewSet(viewsets.ModelViewSet):
    queryset = Animal.objects.all().order_by('-id')
    serializer_class = AnimalSerializer


# ==========================================
# VUES WEB (INTERFACE DJANGO)
# ==========================================

def animaux_list(request):
    """Affiche la liste des animaux dans l'interface HTML."""
    animaux = Animal.objects.all().select_related("client").order_by('-id')
    return render(request, "animaux/list.html", {
        "animaux": animaux,
        "active_page": "animaux",
    })


@require_POST
def ajouter_animal(request):
    """Ajoute un animal via un formulaire web HTML standard."""
    client_id = request.POST.get("client_id")
    nom = request.POST.get("nom")
    espece = request.POST.get("espece")

    try:
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
    except Client.DoesNotExist:
        return JsonResponse({"error": "Client introuvable"}, status=404)


def historique_animal(request, animal_id):
    """Affiche l'historique complet (consultations, RDV, ordonnances) d'un animal."""
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


# ==========================================
# ENDPOINTS API (POUR APPLICATION FLUTTER)
# ==========================================

@csrf_exempt
def api_liste_animaux(request):
    """GET /animaux/api/liste/ — Liste complète des animaux avec possibilité de filtrer par client_id."""
    qs = Animal.objects.select_related("client").order_by("-id")

    client_id = request.GET.get("client_id")
    if client_id:
        qs = qs.filter(client_id=client_id)

    data = [
        {
            "id": a.id,
            "nom": a.nom,
            "espece": a.espece or "",
            "race": a.race or "",
            "sexe": a.sexe or "",
            "poids": a.poids or 0,
            "client": a.client.nom if a.client else "",
            "client_id": a.client_id,
        }
        for a in qs
    ]
    return JsonResponse(data, safe=False, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def api_ajouter_animal(request):
    """POST /animaux/api/ajouter/ — Création d'un animal."""
    try:
        data = json.loads(request.body)
        client = Client.objects.get(pk=data.get("client_id"))
        
        animal = Animal.objects.create(
            client=client,
            nom=data.get("nom", "").strip(),
            espece=data.get("espece", "").strip(),
            race=data.get("race", "").strip(),
            sexe=data.get("sexe", "").strip(),
            poids=data.get("poids") or None,
        )
        return JsonResponse({
            "id": animal.id,
            "nom": animal.nom,
            "espece": animal.espece,
            "client_id": animal.client_id,
        }, status=201)

    except Client.DoesNotExist:
        return JsonResponse({"error": "Client introuvable."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Format JSON invalide."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def api_modifier_animal(request, animal_id):
    """PUT/PATCH /animaux/api/<id>/modifier/ — Mise à jour d'un animal."""
    try:
        animal = Animal.objects.get(pk=animal_id)
        data = json.loads(request.body)

        animal.nom = data.get("nom", animal.nom)
        animal.espece = data.get("espece", animal.espece)
        animal.race = data.get("race", animal.race)
        animal.sexe = data.get("sexe", animal.sexe)
        
        if "poids" in data:
            animal.poids = data.get("poids") or None

        if data.get("client_id"):
            animal.client = Client.objects.get(pk=data["client_id"])

        animal.save()
        return JsonResponse({
            "id": animal.id,
            "nom": animal.nom,
            "espece": animal.espece,
            "race": animal.race or "",
            "sexe": animal.sexe or "",
            "poids": animal.poids,
            "client_id": animal.client_id,
        }, status=200)

    except Animal.DoesNotExist:
        return JsonResponse({"error": "Animal introuvable."}, status=404)
    except Client.DoesNotExist:
        return JsonResponse({"error": "Nouveau client introuvable."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Format JSON invalide."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_supprimer_animal(request, animal_id):
    """DELETE /animaux/api/<id>/supprimer/ — Suppression d'un animal."""
    try:
        animal = Animal.objects.get(pk=animal_id)
        
        # Vérification si l'animal a un historique médical
        if Consultation.objects.filter(animal=animal).exists() or RendezVous.objects.filter(animal=animal).exists():
            return JsonResponse({
                "error": "Impossible de supprimer cet animal car des consultations ou rendez-vous y sont rattachés."
            }, status=409)

        animal.delete()
        return JsonResponse({"success": True, "message": f"Animal {animal_id} supprimé."}, status=200)

    except Animal.DoesNotExist:
        return JsonResponse({"error": "Animal introuvable."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)