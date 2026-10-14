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
    return render(request, "animaux/liste_animaux.html", {
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
    """
    Dossier d'un animal : identité, propriétaire, évolution du poids,
    prochain rendez-vous et historique unique (consultations avec leur
    ordonnance, rendez-vous), du plus récent au plus ancien.
    """
    from django.utils import timezone

    from clients.views import _depuis, _fcfa, _jour_complet, _mois_annee, _numero_whatsapp
    from ventes.models import Vente

    animal = get_object_or_404(Animal.objects.select_related("client"), id=animal_id)
    maintenant = timezone.now()

    consultations = list(
        Consultation.objects.filter(animal=animal)
        .select_related("ordonnance")
        .prefetch_related("ordonnance__lignes__medicament__catalogue")
        .order_by("-date")
    )
    rendezvous = list(RendezVous.objects.filter(animal=animal).order_by("-date_rdv"))

    montants = {}
    for v in Vente.objects.filter(ordonnance__consultation__animal=animal).only("ordonnance_id", "total"):
        montants[v.ordonnance_id] = montants.get(v.ordonnance_id, 0) + (v.total or 0)

    def _nom_med(ligne):
        med = ligne.medicament
        return med.catalogue.nom if med and getattr(med, "catalogue", None) else str(med)

    evenements = []
    for c in consultations:
        ordonnance = c.ordonnance if hasattr(c, "ordonnance") else None
        lignes = list(ordonnance.lignes.all()) if ordonnance else []
        montant = montants.get(ordonnance.id) if ordonnance else None
        evenements.append({
            "type": "consultation", "date": c.date, "objet": c, "ordonnance": ordonnance,
            "medicaments": [{"nom": _nom_med(l), "qte": l.quantite, "posologie": l.posologie} for l in lignes],
            "montant_txt": _fcfa(montant) if montant else "",
        })
    for r in rendezvous:
        evenements.append({
            "type": "rdv", "date": r.date_rdv, "objet": r,
            "a_venir": r.date_rdv >= maintenant and r.statut in ("EN_ATTENTE", "CONFIRME"),
        })
    evenements.sort(key=lambda e: e["date"], reverse=True)
    for e in evenements:
        e["mois"] = _mois_annee(e["date"])

    # Évolution du poids (pesées des consultations, de la plus ancienne à la plus récente)
    pesees = [(c.date, c.poids) for c in reversed(consultations) if c.poids]
    poids_actuel = pesees[-1][1] if pesees else animal.poids
    ecart_poids = round(pesees[-1][1] - pesees[-2][1], 1) if len(pesees) >= 2 else None
    courbe = None
    if len(pesees) >= 2:
        valeurs = [p for _, p in pesees][-12:]
        mini, maxi = min(valeurs), max(valeurs)
        etendue = (maxi - mini) or 1
        largeur, hauteur = 260, 70
        pas = largeur / (len(valeurs) - 1)
        points = [(round(i * pas, 1), round(hauteur - (v - mini) * hauteur / etendue, 1)) for i, v in enumerate(valeurs)]
        courbe = {
            "points": " ".join(f"{x},{y + 8}" for x, y in points),
            "dernier": {"x": points[-1][0], "y": points[-1][1] + 8},
            "mini": mini, "maxi": maxi,
            "debut": timezone.localtime(pesees[-len(valeurs)][0]).strftime("%d/%m/%Y"),
        }

    prochain_rdv = min(
        (r for r in rendezvous if r.date_rdv >= maintenant and r.statut in ("EN_ATTENTE", "CONFIRME")),
        key=lambda r: r.date_rdv, default=None,
    )
    total = sum(montants.values())
    client = animal.client

    return render(request, "animaux/historique_animal.html", {
        "animal": animal,
        "client": client,
        "evenements": evenements,
        "nb_consultations": len(consultations),
        "nb_rdv": len(rendezvous),
        "nb_ordonnances": sum(1 for e in evenements if e.get("ordonnance")),
        "derniere_visite": consultations[0].date if consultations else None,
        "derniere_visite_depuis": _depuis(consultations[0].date) if consultations else "",
        "poids_actuel": poids_actuel,
        "ecart_poids": ecart_poids,
        "courbe": courbe,
        "prochain_rdv": prochain_rdv,
        "prochain_rdv_libelle": _jour_complet(prochain_rdv.date_rdv) if prochain_rdv else "",
        "total_soins": _fcfa(total) if total else "",
        "telephone_wa": _numero_whatsapp(client.telephone if client else ""),
        "active_page": "animaux",
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