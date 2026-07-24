from django.shortcuts import render, redirect
from .models import Fournisseur
from .serializers import FournisseurSerializer
from rest_framework import viewsets
from pharmacie.models import Medicament
from django.shortcuts import render, redirect, get_object_or_404


class FournisseurViewSet(viewsets.ModelViewSet):
    queryset = Fournisseur.objects.all()
    serializer_class = FournisseurSerializer


def fournisseurs_list(request):
    fournisseurs = Fournisseur.objects.all().order_by("nom")

    return render(request, "fournisseurs/liste_fournisseur.html", {
        "fournisseurs": fournisseurs,
        "active_page": "fournisseurs",
    })

def fournisseur_update(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)

    if request.method == "POST":
        fournisseur.nom = request.POST.get("nom")
        fournisseur.telephone = request.POST.get("telephone")
        fournisseur.email = request.POST.get("email")
        fournisseur.adresse = request.POST.get("adresse")
        fournisseur.save()

        return redirect("fournisseurs_list")

    return render(request, "fournisseurs/liste_fournisseur.html", {
        "fournisseur": fournisseur
    })

# ── À ajouter à la fin de fournisseurs/views.py ──────────────────────────────
from django.http import JsonResponse
from .models import Fournisseur

def api_liste_fournisseurs(request):
    """Liste des fournisseurs pour le dashboard Flutter."""
    fournisseurs = Fournisseur.objects.all().order_by("nom")
    data = []
    for f in fournisseurs:
        data.append({
            "id": f.id,
            "nom": f.nom,
            "contact": getattr(f, 'telephone', '') or getattr(f, 'contact', ''),
            "email": getattr(f, 'email', ''),
            "adresse": getattr(f, 'adresse', ''),
        })
    return JsonResponse(data, safe=False)

# ── À ajouter à la fin de fournisseurs/views.py ──────────────────────────────
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


def api_liste_fournisseurs(request):
    """GET /fournisseurs/api/liste/"""
    fournisseurs = Fournisseur.objects.all().order_by("nom")
    data = []
    for f in fournisseurs:
        nb_medicaments = Medicament.objects.filter(fournisseur=f).count()
        data.append({
            "id": f.id,
            "nom": f.nom,
            "telephone": f.telephone or "",
            "email": f.email or "",
            "adresse": f.adresse or "",
            "nb_medicaments": nb_medicaments,
        })
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def api_ajouter_fournisseur(request):
    """POST /fournisseurs/api/ajouter/"""
    try:
        data = json.loads(request.body)
        if not data.get("nom"):
            return JsonResponse({"error": "Le nom est obligatoire"}, status=400)

        fournisseur = Fournisseur.objects.create(
            nom=data.get("nom", ""),
            telephone=data.get("telephone", ""),
            email=data.get("email", ""),
            adresse=data.get("adresse", ""),
        )
        return JsonResponse({"id": fournisseur.id, "nom": fournisseur.nom}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
def api_modifier_fournisseur(request, fournisseur_id):
    """PUT /fournisseurs/api/<id>/modifier/"""
    try:
        fournisseur = Fournisseur.objects.get(pk=fournisseur_id)
        data = json.loads(request.body)
        fournisseur.nom = data.get("nom", fournisseur.nom)
        fournisseur.telephone = data.get("telephone", fournisseur.telephone)
        fournisseur.email = data.get("email", fournisseur.email)
        fournisseur.adresse = data.get("adresse", fournisseur.adresse)
        fournisseur.save()
        return JsonResponse({"id": fournisseur.id, "nom": fournisseur.nom})
    except Fournisseur.DoesNotExist:
        return JsonResponse({"error": "Fournisseur introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_supprimer_fournisseur(request, fournisseur_id):
    """DELETE /fournisseurs/api/<id>/supprimer/"""
    try:
        fournisseur = Fournisseur.objects.get(pk=fournisseur_id)
        fournisseur.delete()
        return JsonResponse({"success": True})
    except Fournisseur.DoesNotExist:
        return JsonResponse({"error": "Fournisseur introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)