from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, F, Sum
from datetime import timedelta
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

# ===================== EXPORTS (Excel / PDF) =====================
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# ===================== MODELS IMPORTS =====================
from .models import Medicament, CatalogueMedicament, FamilleMedicament
from fournisseurs.models import Fournisseur
from ventes.models import Vente
from consultations.models import Consultation, RendezVous 
from clients.models import Client
from animaux.models import Animal

# ===================== DRF =====================
from rest_framework import viewsets
from .serializers import MedicamentSerializer, FamilleMedicamentSerializer

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated



# ===================== DRF VIEWSETS =====================
class FamilleMedicamentViewSet(viewsets.ModelViewSet):
    queryset = FamilleMedicament.objects.all()
    serializer_class = FamilleMedicamentSerializer


class MedicamentViewSet(viewsets.ModelViewSet):
    queryset = Medicament.objects.select_related('catalogue__famille').all()
    serializer_class = MedicamentSerializer


# ===================== API VIEWS =====================
def api_medicaments(request):
    search = request.GET.get("search", "")
    famille = request.GET.get("famille", "")

    qs = Medicament.objects.select_related(
        "catalogue__famille",
        "fournisseur"
    ).all()

    if search:
        qs = qs.filter(
            Q(catalogue__nom__icontains=search) |
            Q(catalogue__famille__nom__icontains=search) |
            Q(fournisseur__nom__icontains=search)
        )

    if famille:
        qs = qs.filter(catalogue__famille__nom=famille)

    data = []

    for m in qs:
        data.append({
            "id": m.id,
            "nom": m.catalogue.nom,
            "famille": m.catalogue.famille.nom if m.catalogue.famille else "",
            "fournisseur": m.fournisseur.nom if m.fournisseur else "",
            "stock": m.stock,
            "prix": float(m.prix),
            "seuil_alerte": m.seuil_alerte,
            "statut": (
                "Rupture"
                if m.stock == 0
                else "Alerte"
                if m.stock <= m.seuil_alerte
                else "OK"
            )
        })

    return JsonResponse({
        "count": len(data),
        "results": data
    })


# ===================== DJANGO VIEWS =====================
def pharmacie_dashboard(request):
    today = timezone.localdate()

    prochains_rdv = (
        RendezVous.objects
        .select_related("animal", "animal__client")
        .filter(date_rdv__date__gte=today)
        .order_by("date_rdv")
    )

    prochains_rdv = sorted(
        prochains_rdv,
        key=lambda rdv: (
            rdv.date_rdv.date() != today,
            rdv.date_rdv.date(),
            rdv.date_rdv.time()
        )
    )

    total_consultations = Consultation.objects.count()
    total_rdv = RendezVous.objects.count()

    total_ventes = Vente.objects.filter(
        date__date=today
    ).aggregate(total=Sum("total"))["total"] or 0

    stock_critique = Medicament.objects.filter(stock__lte=5)

    jours_mois = []
    ventes_mois = []
    consultations_mois = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        jours_mois.append(day.strftime("%d/%m"))

        ventes_jour = Vente.objects.filter(date__date=day).aggregate(
            total=Sum("total")
        )["total"] or 0

        consult_jour = Consultation.objects.filter(date__date=day).count()

        ventes_mois.append(ventes_jour)
        consultations_mois.append(consult_jour)

    context = {
        "today": today,
        "prochains_rdv": prochains_rdv,
        "total_consultations": total_consultations,
        "total_rdv": total_rdv,
        "total_ventes": total_ventes,
        "stock_critique": stock_critique,
        "jours_mois": jours_mois,
        "ventes_mois": ventes_mois,
        "consultations_mois": consultations_mois,
    }

    return render(request, "pharmacie/dashboard.html", context)


def medicaments_list(request):
    search = request.GET.get("search", "")

    medicaments = Medicament.objects.select_related(
        'catalogue__famille', 'fournisseur'
    ).all()

    if search:
        medicaments = medicaments.filter(
            Q(catalogue__nom__icontains=search) |
            Q(catalogue__famille__nom__icontains=search) |
            Q(fournisseur__nom__icontains=search)
        )

    context = {
        "medicaments": medicaments,
        "familles": FamilleMedicament.objects.all(),
        "medicaments_ok": medicaments.filter(stock__gt=F('seuil_alerte')).count(),
        "medicaments_critiques": medicaments.filter(stock__lte=F('seuil_alerte')).count(),
        "valeur_totale": sum(m.stock * m.prix for m in medicaments),
        "search": search,
    }

    return render(request, "pharmacie/medicaments_list.html", context)


def medicament_create(request):
    if request.method == "POST":
        catalogue_id = request.POST.get("catalogue")
        stock = int(request.POST.get("stock", 0))
        prix = request.POST.get("prix")
        seuil = request.POST.get("seuil_alerte", 5)

        fournisseur_nom = request.POST.get("fournisseur_nom")
        fournisseur_contact = request.POST.get("fournisseur_contact")
        fournisseur_email = request.POST.get("fournisseur_email")
        fournisseur_adresse = request.POST.get("fournisseur_adresse")

        catalogue = get_object_or_404(CatalogueMedicament, id=catalogue_id)

        fournisseur = None
        if fournisseur_nom:
            fournisseur, created = Fournisseur.objects.get_or_create(
                nom=fournisseur_nom,
                defaults={
                    "telephone": fournisseur_contact,
                    "email": fournisseur_email,
                    "adresse": fournisseur_adresse,
                }
            )
            if not created:
                fournisseur.telephone = fournisseur_contact
                fournisseur.email = fournisseur_email
                fournisseur.adresse = fournisseur_adresse
                fournisseur.save()

        medicament, created = Medicament.objects.get_or_create(
            catalogue=catalogue,
            defaults={
                "stock": stock,
                "prix": prix,
                "seuil_alerte": seuil,
                "fournisseur": fournisseur
            }
        )
        if not created:
            medicament.stock += stock
            medicament.prix = prix
            medicament.seuil_alerte = seuil
            medicament.fournisseur = fournisseur
            medicament.save()

        return redirect("medicaments_list")

    catalogues = CatalogueMedicament.objects.all()
    familles = FamilleMedicament.objects.all()

    return render(request, "pharmacie/medicament_form.html", {
        "catalogues": catalogues,
        "familles": familles,
    })


@csrf_exempt
def dashboard_stats(request):
    today = timezone.localdate()
    data = {
        "clients": Client.objects.count(),
        "animaux": Animal.objects.count(),
        "consultations": Consultation.objects.count(),
        "rendezvous": RendezVous.objects.count(),
        "medicaments": Medicament.objects.count(),
        "stock_alertes": Medicament.objects.filter(
            stock__lte=F("seuil_alerte")
        ).count(),
        "ventes_jour": float(
            Vente.objects.filter(date__date=today)
            .aggregate(total=Sum("total"))["total"] or 0
        ),
    }
    return JsonResponse(data)


@require_GET
def api_stock_alertes(request):
    alertes = Medicament.objects.filter(
        stock__lte=F("seuil_alerte")
    ).select_related("catalogue", "fournisseur")

    data = [{
        "medicament": m.catalogue.nom,
        "stock": m.stock,
        "seuil": m.seuil_alerte,
        "fournisseur": m.fournisseur.nom if m.fournisseur else "",
    } for m in alertes]

    return JsonResponse(data, safe=False)


@require_GET
def api_fournisseurs(request):
    fournisseurs = Fournisseur.objects.all()

    data = [{
        "id": f.id,
        "nom": f.nom,
        "contact": f.telephone or "",
        "email": f.email or "",
        "adresse": f.adresse or "",
    } for f in fournisseurs]

    return JsonResponse(data, safe=False)


def api_alertes(request):
    """Alertes stock pour le dashboard Flutter."""
    alertes = (
        Medicament.objects
        .select_related("catalogue", "fournisseur")
        .filter(stock__lte=F("seuil_alerte"))
        .order_by("stock")
    )
    data = []
    for m in alertes:
        data.append({
            "medicament": m.catalogue.nom if m.catalogue else str(m),
            "stock": m.stock,
            "seuil": m.seuil_alerte,
            "fournisseur": m.fournisseur.nom if m.fournisseur else "",
        })
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def api_ajouter_medicament(request):
    """POST /pharmacie/api/ajouter/"""
    try:
        data = json.loads(request.body)

        famille_nom = data.get("famille", "Général")
        famille, _ = FamilleMedicament.objects.get_or_create(nom=famille_nom)

        catalogue_nom = data.get("nom", "")
        if not catalogue_nom:
            return JsonResponse({"error": "Nom obligatoire"}, status=400)

        catalogue, _ = CatalogueMedicament.objects.get_or_create(
            nom=catalogue_nom,
            defaults={"famille": famille}
        )

        fournisseur = None
        fournisseur_id = data.get("fournisseur_id")
        if fournisseur_id:
            try:
                fournisseur = Fournisseur.objects.get(pk=fournisseur_id)
            except Exception:
                pass

        medicament = Medicament.objects.create(
            catalogue=catalogue,
            stock=int(data.get("stock", 0)),
            prix=float(data.get("prix", 0)),
            seuil_alerte=int(data.get("seuil_alerte", 5)),
            fournisseur=fournisseur,
        )

        return JsonResponse({
            "id": medicament.id,
            "nom": medicament.catalogue.nom,
            "stock": medicament.stock,
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
def api_modifier_medicament(request, medicament_id):
    """PUT /pharmacie/api/<id>/modifier/"""
    try:
        medicament = Medicament.objects.select_related(
            "catalogue__famille", "fournisseur"
        ).get(pk=medicament_id)

        data = json.loads(request.body)

        if "stock" in data:
            medicament.stock = int(data["stock"])
        if "prix" in data:
            medicament.prix = float(data["prix"])
        if "seuil_alerte" in data:
            medicament.seuil_alerte = int(data["seuil_alerte"])

        fournisseur_id = data.get("fournisseur_id")
        if fournisseur_id:
            try:
                medicament.fournisseur = Fournisseur.objects.get(pk=fournisseur_id)
            except Exception:
                pass

        if "nom" in data and data["nom"]:
            medicament.catalogue.nom = data["nom"]
            medicament.catalogue.save()

        if "famille" in data and data["famille"]:
            famille, _ = FamilleMedicament.objects.get_or_create(nom=data["famille"])
            medicament.catalogue.famille = famille
            medicament.catalogue.save()

        medicament.save()

        return JsonResponse({
            "id": medicament.id,
            "nom": medicament.catalogue.nom,
            "stock": medicament.stock,
        })

    except Medicament.DoesNotExist:
        return JsonResponse({"error": "Médicament introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_supprimer_medicament(request, medicament_id):
    """DELETE /pharmacie/api/<id>/supprimer/"""
    try:
        medicament = Medicament.objects.get(pk=medicament_id)
        medicament.delete()
        return JsonResponse({"success": True})
    except Medicament.DoesNotExist:
        return JsonResponse({"error": "Médicament introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@require_http_methods(["GET"])
def api_medicaments_liste(request):
    """
    GET /pharmacie/api/liste/
    Version enrichie de api_medicaments — renvoie l'id pour le CRUD Flutter.
    """
    qs = Medicament.objects.select_related(
        "catalogue__famille", "fournisseur"
    ).all().order_by("catalogue__nom")

    search = request.GET.get("search", "")
    if search:
        qs = qs.filter(
            Q(catalogue__nom__icontains=search) |
            Q(catalogue__famille__nom__icontains=search)
        )

    data = []
    for m in qs:
        data.append({
            "id": m.id,
            "nom": m.catalogue.nom if m.catalogue else "",
            "famille": m.catalogue.famille.nom if m.catalogue and m.catalogue.famille else "",
            "fournisseur": m.fournisseur.nom if m.fournisseur else "",
            "fournisseur_id": m.fournisseur.id if m.fournisseur else None,
            "stock": m.stock,
            "prix": float(m.prix or 0),
            "seuil_alerte": m.seuil_alerte,
            "statut": (
                "Rupture" if m.stock == 0
                else "Alerte" if m.stock <= m.seuil_alerte
                else "OK"
            ),
        })

    return JsonResponse(data, safe=False)


# ===================== EXPORTS EXCEL / PDF =====================

def export_pharmacie_excel(request):
    """GET /pharmacie/export/excel/"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Pharmacie"

    headers = ["Médicament", "Famille", "Stock", "Seuil alerte", "Prix (FCFA)", "Statut", "Fournisseur"]
    ws.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2E7D4F", end_color="2E7D4F", fill_type="solid")
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    medicaments = Medicament.objects.select_related("catalogue__famille", "fournisseur").order_by("catalogue__nom")

    for m in medicaments:
        statut = "Rupture" if m.stock == 0 else "Alerte" if m.stock <= m.seuil_alerte else "OK"
        ws.append([
            m.catalogue.nom if m.catalogue else "",
            m.catalogue.famille.nom if m.catalogue and m.catalogue.famille else "",
            m.stock,
            m.seuil_alerte,
            float(m.prix or 0),
            statut,
            m.fournisseur.nom if m.fournisseur else "",
        ])

    for col_letter in ["A", "B", "C", "D", "E", "F", "G"]:
        ws.column_dimensions[col_letter].width = 20

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="pharmacie.xlsx"'
    wb.save(response)
    return response


def export_pharmacie_pdf(request):
    """GET /pharmacie/export/pdf/"""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="pharmacie.pdf"'

    doc = SimpleDocTemplate(
        response, pagesize=landscape(A4),
        rightMargin=1.2 * cm, leftMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
    )

    styles = getSampleStyleSheet()
    elements = []

    titre_style = styles["Heading2"]
    titre_style.alignment = TA_CENTER
    elements.append(Paragraph("<b>ÉTAT DU STOCK - PHARMACIE PARCELLES VÉTO</b>", titre_style))
    elements.append(Paragraph(
        f"<para alignment='center'><font size='9'>Édité le {timezone.now().strftime('%d/%m/%Y %H:%M')}</font></para>",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 0.5 * cm))

    data = [["Médicament", "Famille", "Stock", "Seuil", "Prix (FCFA)", "Statut", "Fournisseur"]]
    medicaments = Medicament.objects.select_related("catalogue__famille", "fournisseur").order_by("catalogue__nom")

    for m in medicaments:
        statut = "Rupture" if m.stock == 0 else "Alerte" if m.stock <= m.seuil_alerte else "OK"
        data.append([
            m.catalogue.nom if m.catalogue else "",
            m.catalogue.famille.nom if m.catalogue and m.catalogue.famille else "",
            str(m.stock),
            str(m.seuil_alerte),
            f"{m.prix:,.0f}",
            statut,
            m.fournisseur.nom if m.fournisseur else "-",
        ])

    table = Table(data, colWidths=[4*cm, 3*cm, 2*cm, 2*cm, 3*cm, 2.5*cm, 4*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D4F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
    ]))
    elements.append(table)

    doc.build(elements)
    return response

@login_required
@require_POST
def ajouter_famille_ajax(request):
    nom = request.POST.get("nom", "").strip()
    if not nom:
        return JsonResponse({"success": False, "error": "Le nom de la famille est obligatoire."}, status=400)
    
    famille, created = FamilleMedicament.objects.get_or_create(nom=nom)
    return JsonResponse({
        "success": True,
        "id": famille.id,
        "nom": famille.nom,
        "created": created
    })