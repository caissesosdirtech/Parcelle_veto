import json
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count, F
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from rest_framework import viewsets
from reportlab.pdfgen import canvas
from openpyxl import Workbook

# Modèles des différentes applications
from .models import Client
from .serializers import ClientSerializer
from animaux.models import Animal
from consultations.models import Consultation, RendezVous, Ordonnance


# ── REST FRAMEWORK VIEWSET ───────────────────────────────────────────────────

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer


# ── FONCTIONS UTILITAIRES POUR TELEPHONE ──────────────────────────────────────

def _normaliser_telephone(value):
    """Normalise un numéro pour détecter les doublons malgré espaces/tirets/préfixes."""
    if not value:
        return ""
    value = str(value).strip()
    digits = "".join(ch for ch in value if ch.isdigit())
    if digits.startswith("00221"):
        digits = digits[5:]
    elif digits.startswith("221") and len(digits) == 12:
        digits = digits[3:]
    return digits


def _verifier_telephone_unique(telephone, client_id=None):
    """Retourne un message d'erreur si le téléphone appartient déjà à un autre client."""
    normalized = _normaliser_telephone(telephone)
    if not normalized:
        return None  # Pas de numéro ou vide, on laisse passer (ou adapter selon besoin)

    qs = Client.objects.exclude(telephone__isnull=True).exclude(telephone="")
    if client_id:
        qs = qs.exclude(id=client_id)

    for autre in qs:
        if _normaliser_telephone(autre.telephone) == normalized:
            return (
                f"Ce numéro de téléphone est déjà utilisé par le client "
                f'"{autre.nom}" (ID {autre.id}).'
            )
    return None


# ── VUES WEB (TEMPLATES HTML) ─────────────────────────────────────────────────

def clients_list(request):
    """Affiche la liste paginée des clients sur l'interface Web."""
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


_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
         "août", "septembre", "octobre", "novembre", "décembre"]
_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _mois_annee(d):
    d = timezone.localtime(d)
    return f"{_MOIS[d.month - 1]} {d.year}"


def _jour_complet(d):
    """« samedi 17 octobre à 14:06 »"""
    d = timezone.localtime(d)
    return f"{_JOURS[d.weekday()]} {d.day} {_MOIS[d.month - 1]} à {d:%H:%M}"


def _depuis(d):
    """« aujourd'hui », « il y a 3 jours », « il y a 2 mois »…"""
    jours = (timezone.localdate() - timezone.localtime(d).date()).days
    if jours <= 0:
        return "aujourd'hui"
    if jours == 1:
        return "hier"
    if jours < 31:
        return f"il y a {jours} jours"
    if jours < 365:
        return f"il y a {jours // 30} mois"
    ans = jours // 365
    return f"il y a {ans} an{'s' if ans > 1 else ''}"


def _fcfa(montant):
    """10500 → « 10 500 »"""
    return f"{int(round(float(montant or 0))):,}".replace(",", "\u202f")


def _numero_whatsapp(telephone):
    """77 123 45 67 → 221771234567 (numéros sénégalais à 9 chiffres)."""
    chiffres = "".join(ch for ch in (telephone or "") if ch.isdigit())
    if len(chiffres) == 9:
        chiffres = "221" + chiffres
    return chiffres


def historique_client(request, client_id):
    """
    Dossier d'un client : ses animaux, son prochain rendez-vous et un
    historique unique (consultations avec leur ordonnance, rendez-vous,
    achats en pharmacie) du plus récent au plus ancien.
    """
    from ventes.models import Vente

    client = get_object_or_404(Client, id=client_id)
    maintenant = timezone.now()

    animaux = list(
        Animal.objects.filter(client=client)
        .annotate(nb_consultations=Count("consultation", distinct=True))
        .order_by("nom")
    )
    consultations = list(
        Consultation.objects.filter(client=client)
        .select_related("animal", "ordonnance")
        .prefetch_related("ordonnance__lignes__medicament__catalogue")
        .order_by("-date")
    )
    rendezvous = list(
        RendezVous.objects.filter(animal__client=client)
        .select_related("animal")
        .order_by("-date_rdv")
    )
    ventes = list(
        Vente.objects.filter(Q(client=client) | Q(ordonnance__consultation__client=client))
        .select_related("ordonnance")
        .prefetch_related("lignes__medicament__catalogue")
        .distinct()
    )

    # Montant payé pour chaque ordonnance (affiché sur la consultation)
    montant_par_ordonnance = {}
    for v in ventes:
        if v.ordonnance_id:
            montant_par_ordonnance[v.ordonnance_id] = montant_par_ordonnance.get(v.ordonnance_id, 0) + (v.total or 0)

    def _nom_med(ligne):
        med = ligne.medicament
        return med.catalogue.nom if med and getattr(med, "catalogue", None) else str(med)

    evenements = []
    for c in consultations:
        ordonnance = c.ordonnance if hasattr(c, "ordonnance") else None
        lignes = list(ordonnance.lignes.all()) if ordonnance else []
        evenements.append({
            "type": "consultation",
            "date": c.date,
            "objet": c,
            "animal": c.animal,
            "ordonnance": ordonnance,
            "medicaments": [f"{_nom_med(l)} ×{l.quantite}" for l in lignes],
            "montant": montant_par_ordonnance.get(ordonnance.id) if ordonnance else None,
        })
    for r in rendezvous:
        evenements.append({
            "type": "rdv",
            "date": r.date_rdv,
            "objet": r,
            "animal": r.animal,
            "a_venir": r.date_rdv >= maintenant and r.statut in ("EN_ATTENTE", "CONFIRME"),
        })
    for v in ventes:
        if v.ordonnance_id:
            continue  # déjà affichée avec sa consultation
        evenements.append({
            "type": "vente",
            "date": v.date,
            "objet": v,
            "medicaments": [f"{_nom_med(l)} ×{l.quantite}" for l in v.lignes.all()],
            "montant": v.total,
        })
    evenements.sort(key=lambda e: e["date"], reverse=True)
    for e in evenements:
        e["mois"] = _mois_annee(e["date"])
        if e.get("montant"):
            e["montant_txt"] = _fcfa(e["montant"])

    prochain_rdv = min(
        (r for r in rendezvous if r.date_rdv >= maintenant and r.statut in ("EN_ATTENTE", "CONFIRME")),
        key=lambda r: r.date_rdv, default=None,
    )
    total_depense = sum((v.total or 0) for v in ventes)

    return render(request, "clients/historique_client.html", {
        "client": client,
        "animaux": animaux,
        "evenements": evenements,
        "prochain_rdv": prochain_rdv,
        "derniere_visite": consultations[0].date if consultations else None,
        "derniere_visite_depuis": _depuis(consultations[0].date) if consultations else "",
        "prochain_rdv_libelle": _jour_complet(prochain_rdv.date_rdv) if prochain_rdv else "",
        "nb_consultations": len(consultations),
        "nb_rdv": len(rendezvous),
        "nb_achats": sum(1 for e in evenements if e["type"] == "vente"),
        "total_depense": _fcfa(total_depense),
        "telephone_wa": _numero_whatsapp(client.telephone),
        "active_page": "clients",
    })


def export_excel(request):
    """Exporte la liste des clients et leurs animaux sous format Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Clients"

    ws.append(["Client", "Téléphone", "Adresse", "Animal", "Espèce", "Race"])

    for c in Client.objects.prefetch_related("animaux").all():
        for a in c.animaux.all():
            ws.append([
                c.nom,
                c.telephone or "",
                c.adresse or "",
                a.nom,
                a.espece or "",
                a.race or ""
            ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="clients.xlsx"'

    wb.save(response)
    return response


def export_pdf(request):
    """Génère un export PDF simple de la liste des clients."""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="clients.pdf"'

    p = canvas.Canvas(response)
    y = 800

    for c in Client.objects.prefetch_related("animaux").all():
        if y < 50:
            p.showPage()
            y = 800

        p.drawString(50, y, f"{c.nom} - {c.telephone or 'N/A'} - {c.adresse or 'N/A'}")
        y -= 20

        for a in c.animaux.all():
            if y < 50:
                p.showPage()
                y = 800
            p.drawString(70, y, f"🐾 {a.nom} ({a.espece or 'Inconnu'})")
            y -= 15

        y -= 10

    p.save()
    return response


# ── ENDPOINTS API (FLUTTER / MOBILE) ──────────────────────────────────────────

def api_clients_list(request):
    """Retourne la liste paginée et filtrée des clients pour l'application Flutter."""
    search = request.GET.get("search", "")
    espece = request.GET.get("espece", "")
    page = int(request.GET.get("page", 1))

    from django.db.models import Max

    qs = Client.objects.prefetch_related("animaux").annotate(
        nb_animaux=Count("animaux", distinct=True),
        nb_consultations=Count("consultation", distinct=True),
        derniere_visite=Max("consultation__date"),
    )
    # Tri : derniers ajoutés (par défaut), ordre alphabétique ou dernière visite
    tri = request.GET.get("tri", "")
    if tri == "nom":
        qs = qs.order_by("nom", "id")
    elif tri == "visite":
        qs = qs.order_by(F("derniere_visite").desc(nulls_last=True), "-id")
    else:
        qs = qs.order_by('-id')  # 🔑 Tri par ID décroissant pour voir les derniers ajoutés en premier

    if search:
        qs = qs.filter(
            Q(nom__icontains=search) |
            Q(telephone__icontains=search) |
            Q(adresse__icontains=search) |
            Q(animaux__nom__icontains=search) |
            Q(animaux__espece__icontains=search)
        ).distinct()

    if espece:
        qs = qs.filter(animaux__espece__iexact=espece).distinct()

    paginator = Paginator(qs, 20) # Augmenté à 20 pour éviter de rater des elements sur mobile
    page_obj = paginator.get_page(page)

    data = []
    total_animaux_page = 0

    for c in page_obj:
        animaux = list(c.animaux.all())
        total_animaux_page += len(animaux)

        data.append({
            "id": c.id,
            "nom": c.nom,
            "telephone": c.telephone or "",
            "adresse": c.adresse or "",
            "nb_animaux": len(animaux),
            "nb_consultations": c.nb_consultations,
            "derniere_visite": c.derniere_visite.isoformat() if c.derniere_visite else None,
            "derniere_visite_depuis": _depuis(c.derniere_visite) if c.derniere_visite else "",
            "telephone_wa": _numero_whatsapp(c.telephone),
            "animaux": [
                {
                    "id": a.id,
                    "nom": a.nom,
                    "espece": a.espece or "",
                    "race": a.race or "",
                    "sexe": a.sexe or "",
                    "poids": a.poids or 0,
                }
                for a in animaux
            ]
        })

    return JsonResponse({
        "results": data,
        "page": page_obj.number,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "num_pages": paginator.num_pages,
        "count": paginator.count,
        "total_clients": Client.objects.count(),
        "total_animaux": Animal.objects.count(),
        "total_animaux_page": total_animaux_page,
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_creer_client(request):
    """Créer un nouveau client."""
    try:
        data = json.loads(request.body or "{}")
        nom = str(data.get('nom', '')).strip()
        telephone = str(data.get('telephone', '')).strip()
        adresse = str(data.get('adresse', '')).strip()

        if not nom:
            return JsonResponse({'error': 'Le nom du client est obligatoire.'}, status=400)

        erreur_tel = _verifier_telephone_unique(telephone)
        if erreur_tel:
            return JsonResponse({'error': erreur_tel}, status=409)

        client = Client.objects.create(
            nom=nom,
            telephone=telephone or None,
            adresse=adresse or None,
        )
        return JsonResponse({'id': client.id, 'nom': client.nom}, status=201)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def api_modifier_client(request, client_id):
    """Modifier un client et synchroniser ses animaux."""
    try:
        client = Client.objects.get(id=client_id)
        data = json.loads(request.body or "{}")

        nom = str(data.get('nom', client.nom)).strip()
        telephone = str(data.get('telephone', '')).strip() if 'telephone' in data else (client.telephone or '')
        adresse = str(data.get('adresse', '')).strip() if 'adresse' in data else (client.adresse or '')

        if not nom:
            return JsonResponse({'error': 'Le nom du client est obligatoire.'}, status=400)

        erreur_tel = _verifier_telephone_unique(telephone, client.id)
        if erreur_tel:
            return JsonResponse({'error': erreur_tel}, status=409)

        animaux_data = data.get('animaux', None)
        supprimer_ids = data.get('supprimer_animaux', []) or []

        if animaux_data is not None and not isinstance(animaux_data, list):
            return JsonResponse({'error': 'Le champ animaux doit être une liste.'}, status=400)

        if not isinstance(supprimer_ids, list):
            return JsonResponse({'error': "Le champ supprimer_animaux doit être une liste d'identifiants."}, status=400)

        for animal_data in animaux_data or []:
            animal_id = animal_data.get('id')
            if animal_id and not Animal.objects.filter(id=animal_id, client=client).exists():
                return JsonResponse({'error': f"Animal {animal_id} introuvable pour ce client."}, status=400)

        for animal_id in supprimer_ids:
            if not Animal.objects.filter(id=animal_id, client=client).exists():
                return JsonResponse({'error': f"Animal {animal_id} introuvable pour ce client."}, status=400)

        if supprimer_ids:
            historique_count = (
                Consultation.objects.filter(animal_id__in=supprimer_ids).count() +
                RendezVous.objects.filter(animal_id__in=supprimer_ids).count()
            )
            if historique_count:
                return JsonResponse({
                    'error': (
                        "Impossible de supprimer cet animal car il possède "
                        "des consultations ou rendez-vous. Modifiez ses informations "
                        "à la place afin de conserver son historique."
                    )
                }, status=409)

        with transaction.atomic():
            client.nom = nom
            client.telephone = telephone or None
            client.adresse = adresse or None
            client.save()

            Animal.objects.filter(client=client, id__in=supprimer_ids).delete()

            animaux_result = []
            for animal_data in animaux_data or []:
                animal_id = animal_data.get('id')
                if animal_id:
                    animal = Animal.objects.get(id=animal_id, client=client)
                    animal.nom = str(animal_data.get('nom', animal.nom)).strip()
                    animal.espece = str(animal_data.get('espece', animal.espece)).strip()
                    animal.race = str(animal_data.get('race', animal.race or '')).strip() or None
                    animal.sexe = str(animal_data.get('sexe', animal.sexe or '')).strip() or None
                    if 'poids' in animal_data:
                        animal.poids = animal_data.get('poids') or None
                    animal.save()
                else:
                    animal = Animal.objects.create(
                        client=client,
                        nom=str(animal_data.get('nom', '')).strip(),
                        espece=str(animal_data.get('espece', '')).strip(),
                        race=str(animal_data.get('race', '')).strip() or None,
                        sexe=str(animal_data.get('sexe', '')).strip() or None,
                        poids=animal_data.get('poids') or None,
                    )

                animaux_result.append({
                    'id': animal.id,
                    'nom': animal.nom,
                    'espece': animal.espece,
                    'race': animal.race or '',
                    'sexe': animal.sexe or '',
                    'poids': animal.poids or 0,
                })

        return JsonResponse({
            'success': True,
            'id': client.id,
            'nom': client.nom,
            'telephone': client.telephone or '',
            'adresse': client.adresse or '',
            'animaux': animaux_result,
        })
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Client introuvable'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide.'}, status=400)
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
    """Statistiques globales des clients et animaux."""
    return JsonResponse({
        "total_clients": Client.objects.count(),
        "total_animaux": Animal.objects.count(),
    })


def api_dossier_client(request, client_id):
    """Dossier médical complet d'un client et de ses animaux pour l'application Flutter."""
    client = get_object_or_404(Client, id=client_id)
    animaux = Animal.objects.filter(client=client).order_by("nom")

    animaux_data = []
    for animal in animaux:
        consultations = Consultation.objects.filter(animal=animal).order_by("-date")

        consultations_data = []
        for c in consultations:
            ordonnance = Ordonnance.objects.filter(consultation=c).first()
            lignes_data = []
            if ordonnance:
                for ligne in ordonnance.lignes.select_related("medicament__catalogue").all():
                    nom_med = (
                        ligne.medicament.catalogue.nom
                        if hasattr(ligne.medicament, 'catalogue') and ligne.medicament.catalogue
                        else str(ligne.medicament)
                    )
                    lignes_data.append({
                        "medicament": nom_med,
                        "quantite": ligne.quantite,
                        "posologie": ligne.posologie,
                    })

            consultations_data.append({
                "id": c.id,
                "date": c.date.strftime("%d/%m/%Y %H:%M") if c.date else "",
                "motif": c.motif or "",
                "observations": c.observations or "",
                "statut": getattr(c, 'statut', ''),
                "lieu": getattr(c, 'lieu', ''),
                "veterinaire": getattr(c, 'veterinaire', '') or "",
                "poids": getattr(c, 'poids', 0) or 0,
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

    rdvs = (
        RendezVous.objects
        .filter(animal__client=client, date_rdv__gte=timezone.now())
        .order_by("date_rdv")
    )
    rdvs_data = [{
        "id": r.id,
        "animal": r.animal.nom,
        "date_rdv": r.date_rdv.strftime("%d/%m/%Y %H:%M") if r.date_rdv else "",
        "motif": r.motif or "",
        "statut": getattr(r, 'statut', ''),
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