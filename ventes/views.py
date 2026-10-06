from notifications.firebase_utils import notify_all_docteurs
from rest_framework import viewsets
from django.shortcuts import render, redirect, get_object_or_404

from .models import Vente, LigneVente
from .medicaments_vendus import recap_medicaments, texte_medicaments
from .serializers import VenteSerializer

from django.http import HttpResponse, JsonResponse
from reportlab.pdfgen import canvas

from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.timezone import now

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from pharmacie.models import Medicament
from clients.models import Client
from consultations.models import Consultation

from django.db import transaction
import json

# ===================== EXPORTS (Excel / PDF) =====================
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


# ===================== DRF =====================

class VenteViewSet(viewsets.ModelViewSet):
    queryset = Vente.objects.all().order_by('-id')
    serializer_class = VenteSerializer


# ===================== VUES WEB (HTML) =====================

def ventes_list(request):
    today = now()
    ventes = Vente.objects.all().order_by('-date')

    search = request.GET.get('search', '').strip()
    type_filtre = request.GET.get('type', '').strip()
    date_filtre = request.GET.get('date', '').strip()

    if search:
        ventes = ventes.filter(
            Q(client__nom__icontains=search) |
            Q(ordonnance__consultation__client__nom__icontains=search) |
            Q(ordonnance__consultation__animal__nom__icontains=search) |
            Q(id__icontains=search)
        ).distinct()

    if type_filtre == 'ordonnance':
        ventes = ventes.filter(ordonnance__isnull=False)
    elif type_filtre == 'direct':
        ventes = ventes.filter(ordonnance__isnull=True)

    if date_filtre:
        ventes = ventes.filter(date__date=date_filtre)

    total_ventes = ventes.aggregate(Sum('total'))['total__sum'] or 0

    ventes_aujourdhui = Vente.objects.filter(
        date__year=today.year,
        date__month=today.month,
        date__day=today.day
    ).aggregate(Sum('total'))['total__sum'] or 0

    nb_ventes = ventes.count()
    ticket_moyen = round(total_ventes / nb_ventes, 0) if nb_ventes > 0 else 0

    consultations_jour = Consultation.objects.filter(
        date__year=today.year,
        date__month=today.month,
        date__day=today.day
    ).count()

    return render(request, "ventes/liste_ventes.html", {
        "ventes": ventes,
        "total_ventes": total_ventes,
        "ventes_aujourdhui": ventes_aujourdhui,
        "nb_ventes": nb_ventes,
        "ticket_moyen": ticket_moyen,
        "consultations_jour": consultations_jour,
    })


def vente_pdf(request, id):
    vente = Vente.objects.get(id=id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="vente.pdf"'

    p = canvas.Canvas(response)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(120, 800, "CABINET VÉTÉRINAIRE PARCELLE VETO")

    p.setFont("Helvetica", 11)
    p.drawString(50, 770, f"Client : {vente.ordonnance.consultation.client.nom}")
    p.drawString(50, 750, f"Animal : {vente.ordonnance.consultation.animal.nom}")
    p.drawString(50, 730, f"Date : {vente.date}")

    y = 690
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Médicaments :")

    y -= 20

    p.setFont("Helvetica", 10)

    for ligne in vente.lignes.all():
        p.drawString(
            60,
            y,
            f"{ligne.medicament.nom} | Qté:{ligne.quantite} | PU:{ligne.prix_unitaire} | Total:{ligne.montant_total}"
        )
        y -= 20

        if y < 100:
            p.showPage()
            y = 800

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y - 30, f"TOTAL : {vente.total} FCFA")

    p.setFont("Helvetica", 9)
    p.drawString(150, 40, "Merci pour votre confiance - Parcelle Veto")

    p.save()
    return response


def vente_detail(request, vente_id):
    vente = get_object_or_404(
        Vente.objects.prefetch_related("lignes__medicament__catalogue"),
        id=vente_id
    )
    return render(
        request,
        "ventes/vente_detail.html",
        {
            "vente": vente,
        },
    )


def vente_create(request):
    if request.method == "POST":
        vente = Vente.objects.create()
        return redirect("vente_detail", vente.id)

    medicaments = Medicament.objects.select_related('catalogue').filter(stock__gt=0)
    clients = Client.objects.all()

    return render(request, "ventes/vente_form.html", {
        "medicaments": medicaments,
        "clients": clients,
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_vente_directe_creer(request):
    """
    POST /ventes/api/directe/creer/ (ou /ventes/api/nouvelle/)

    Payload attendu :
    {
        "client_id":  ou null,   // null = vente anonyme
        "lignes": [
            {"medicament_id": , "quantite": },
            ...
        ]
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Format JSON invalide."}, status=400)

    lignes_payload = data.get("lignes", [])
    if not lignes_payload:
        return JsonResponse({"error": "Le panier est vide."}, status=400)

    client_id = data.get("client_id")
    client = None
    if client_id:
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return JsonResponse({"error": f"Client introuvable (ID: {client_id})."}, status=404)

    alertes_stock = []

    try:
        with transaction.atomic():
            vente = Vente.objects.create(ordonnance=None, client=client, total=0)

            total = 0
            for item in lignes_payload:
                med_id = item.get("medicament_id")
                quantite = int(item.get("quantite", 1))

                if quantite <= 0:
                    transaction.set_rollback(True)
                    return JsonResponse({"error": "Quantité invalide."}, status=400)

                try:
                    med = Medicament.objects.select_for_update().get(id=med_id)
                except Medicament.DoesNotExist:
                    transaction.set_rollback(True)
                    return JsonResponse({"error": f"Médicament introuvable (ID: {med_id})."}, status=404)

                if med.stock < quantite:
                    transaction.set_rollback(True)
                    nom = med.catalogue.nom if hasattr(med, 'catalogue') and med.catalogue else str(med)
                    return JsonResponse({
                        "error": f"Stock insuffisant pour {nom}. Stock actuel : {med.stock}"
                    }, status=400)

                montant = quantite * med.prix
                LigneVente.objects.create(
                    vente=vente,
                    medicament=med,
                    quantite=quantite,
                    prix_unitaire=med.prix,
                    montant_total=montant
                )

                med.stock -= quantite
                med.save()

                if med.stock <= med.seuil_alerte:
                    nom_med = med.catalogue.nom if med.catalogue else "Médicament"
                    alertes_stock.append((nom_med, med.stock, med.id))

                total += montant

            vente.total = total
            vente.save()

        # Notification push de la vente.
        # - UNE SEULE notification par vente (alertes de stock incluses).
        # - AUCUN montant dans le texte : le filtre anti-harcèlement des
        #   téléphones TECNO / Infinix / itel classe les notifications
        #   contenant un montant comme publicité et les rend silencieuses.
        #   Le montant reste consultable dans l'application.
        # Texte validé par test sur TECNO : le mot « vente » déclenche le
        # filtre anti-harcèlement, « opération en pharmacie » passe.
        corps = "Une nouvelle opération vient d'être enregistrée."
        if alertes_stock:
            noms = ", ".join(nom_med for nom_med, _, _ in alertes_stock)
            corps += f"\n⚠️ Stock bas : {noms}"
        notify_all_docteurs(
            title="📋 Nouvelle opération en pharmacie",
            body=corps,
            data={"type": "vente", "id": str(vente.id)}
        )

        return JsonResponse({
            "success": True,
            "message": "Vente enregistrée avec succès.",
            "id": vente.id,
            "vente_id": vente.id,
            "total": float(total),
        }, status=201)

    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(f"Erreur api_vente_directe_creer: {exc}")
        return JsonResponse({
            "error": f"Une erreur est survenue lors de l'enregistrement de la vente : {exc}"
        }, status=500)


# Gardé pour rétrocompatibilité si utilisé ailleurs
vente_directe_save = api_vente_directe_creer


# ===================== API FLUTTER =====================

def _serialize_ligne(l):
    return {
        "medicament": l.medicament.catalogue.nom if l.medicament and l.medicament.catalogue else str(l.medicament),
        "quantite": l.quantite,
        "prix_unitaire": float(l.prix_unitaire or 0),
        "montant_total": float(l.montant_total or 0),
    }


def _serialize_vente(v):
    try:
        if v.ordonnance and v.ordonnance.consultation:
            client = v.ordonnance.consultation.client.nom
        else:
            client = v.client.nom if v.client else "—"
    except Exception:
        client = "—"

    return {
        "id": v.id,
        "date": v.date.strftime("%d/%m/%Y %H:%M"),
        "client": client,
        "total": float(v.total or 0),
        "nb_lignes": v.lignes.count(),
        "lignes": [_serialize_ligne(l) for l in v.lignes.select_related("medicament__catalogue").all()],
    }


def api_ventes_liste(request):
    """GET /ventes/api/liste/ — 50 dernières ventes."""
    ventes = (
        Vente.objects
        .select_related("client", "ordonnance__consultation__client")
        .prefetch_related("lignes__medicament__catalogue")
        .order_by("-date")[:50]
    )
    data = [_serialize_vente(v) for v in ventes]
    return JsonResponse(data, safe=False)


def api_vente_detail(request, vente_id):
    """GET /ventes/api/<id>/ — détail d'une vente (ouverture depuis une notification)."""
    vente = (
        Vente.objects
        .select_related("client", "ordonnance__consultation__client")
        .prefetch_related("lignes__medicament__catalogue")
        .filter(pk=vente_id)
        .first()
    )
    if vente is None:
        return JsonResponse({"error": "Vente introuvable"}, status=404)
    return JsonResponse(_serialize_vente(vente))


def api_ventes_stats(request):
    """GET /ventes/api/stats/"""
    today = now()
    ventes = Vente.objects.all()

    total_general = ventes.aggregate(Sum("total"))["total__sum"] or 0
    total_jour = ventes.filter(
        date__year=today.year, date__month=today.month, date__day=today.day,
    ).aggregate(Sum("total"))["total__sum"] or 0
    nb_ventes = ventes.count()
    ticket_moyen = round(total_general / nb_ventes, 0) if nb_ventes > 0 else 0

    return JsonResponse({
        "total_general": float(total_general),
        "total_jour": float(total_jour),
        "nb_ventes": nb_ventes,
        "ticket_moyen": float(ticket_moyen),
    })


def api_vente_jour(request):
    """
    GET /ventes/api/vente-jour/?date=YYYY-MM-DD
    Détail complet des ventes d'une journée (par défaut aujourd'hui).
    """
    date_str = request.GET.get("date")
    if date_str:
        jour = date_str
        ventes = Vente.objects.filter(date__date=jour)
    else:
        today = now()
        jour = today.strftime("%Y-%m-%d")
        ventes = Vente.objects.filter(
            date__year=today.year, date__month=today.month, date__day=today.day,
        )

    ventes = (
        ventes
        .select_related("client", "ordonnance__consultation__client")
        .prefetch_related("lignes__medicament__catalogue")
        .order_by("-date")
    )

    total = ventes.aggregate(Sum("total"))["total__sum"] or 0
    nb_ventes = ventes.count()

    produits = {}
    for v in ventes:
        for l in v.lignes.all():
            nom = l.medicament.catalogue.nom if l.medicament and l.medicament.catalogue else "Inconnu"
            if nom not in produits:
                produits[nom] = {"nom": nom, "quantite": 0, "montant": 0.0}
            produits[nom]["quantite"] += l.quantite
            produits[nom]["montant"] += float(l.montant_total or 0)

    top_produits = sorted(produits.values(), key=lambda p: p["montant"], reverse=True)

    return JsonResponse({
        "date": jour,
        "total": float(total),
        "nb_ventes": nb_ventes,
        "ticket_moyen": float(round(total / nb_ventes, 0)) if nb_ventes > 0 else 0,
        "ventes": [_serialize_vente(v) for v in ventes],
        "top_produits": top_produits,
    })


# ===================== EXPORTS VENTE DU JOUR =====================

def _ventes_du_jour(request):
    """Ventes de la date demandée (?date=YYYY-MM-DD) ou du jour, + libellé."""
    date_str = request.GET.get("date")
    if date_str:
        ventes = Vente.objects.filter(date__date=date_str)
        libelle = date_str
    else:
        today = now()
        ventes = Vente.objects.filter(
            date__year=today.year, date__month=today.month, date__day=today.day,
        )
        libelle = today.strftime("%Y-%m-%d")
    ventes = (
        ventes
        .select_related("client", "ordonnance__consultation__client")
        .prefetch_related("lignes__medicament__catalogue")
        .order_by("-date")
    )
    return list(ventes), libelle


def _client_de_la_vente(v):
    try:
        if v.ordonnance and v.ordonnance.consultation:
            return v.ordonnance.consultation.client.nom
        return v.client.nom if v.client else "Anonyme"
    except Exception:
        return "Anonyme"


def export_vente_jour_excel(request):
    """GET /ventes/export/jour/excel/?date=YYYY-MM-DD"""
    ventes, jour_label = _ventes_du_jour(request)

    wb = Workbook()
    ws = wb.active
    ws.title = "Vente du jour"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2E7D4F", end_color="2E7D4F", fill_type="solid")

    def entete(feuille, titres):
        feuille.append(titres)
        for col in range(1, len(titres) + 1):
            cell = feuille.cell(row=feuille.max_row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

    entete(ws, ["N°", "Heure", "Client", "Médicaments vendus", "Montant (FCFA)"])

    total = 0
    for v in ventes:
        total += v.total or 0
        ws.append([
            v.id, v.date.strftime("%H:%M"), _client_de_la_vente(v),
            texte_medicaments(v), float(v.total or 0),
        ])
        ws.cell(row=ws.max_row, column=4).alignment = Alignment(wrap_text=True, vertical="top")

    ws.append(["", "", "", "TOTAL", float(total)])
    for col in range(1, 6):
        ws.cell(row=ws.max_row, column=col).font = Font(bold=True)

    for col_letter, largeur in zip("ABCDE", [8, 10, 24, 50, 18]):
        ws.column_dimensions[col_letter].width = largeur

    # Récapitulatif par médicament
    ws2 = wb.create_sheet("Médicaments vendus")
    entete(ws2, ["Médicament", "Quantité vendue", "Montant (FCFA)"])
    for nom, qte, montant in recap_medicaments(ventes):
        ws2.append([nom, qte, montant])
    for col_letter, largeur in zip("ABC", [36, 18, 18]):
        ws2.column_dimensions[col_letter].width = largeur

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="vente_du_jour_{jour_label}.xlsx"'
    wb.save(response)
    return response


def export_vente_jour_pdf(request):
    """GET /ventes/export/jour/pdf/?date=YYYY-MM-DD"""
    ventes, jour_label = _ventes_du_jour(request)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="vente_du_jour.pdf"'

    doc = SimpleDocTemplate(
        response, pagesize=A4,
        rightMargin=1.2 * cm, leftMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
    )

    styles = getSampleStyleSheet()
    cellule = ParagraphStyle("cellule", parent=styles["Normal"], fontSize=8.5, leading=10.5)
    elements = []

    titre_style = styles["Heading2"]
    titre_style.alignment = TA_CENTER
    elements.append(Paragraph("<b>VENTE DU JOUR — PARCELLES VÉTO</b>", titre_style))
    elements.append(Paragraph(jour_label, ParagraphStyle("sous", parent=styles["Normal"], alignment=TA_CENTER)))
    elements.append(Spacer(1, 0.5 * cm))

    data = [["N°", "Heure", "Client", "Médicaments vendus", "Montant (FCFA)"]]
    total = 0
    for v in ventes:
        total += v.total or 0
        data.append([
            str(v.id), v.date.strftime("%H:%M"),
            Paragraph(_client_de_la_vente(v), cellule),
            Paragraph(texte_medicaments(v), cellule),
            f"{v.total:,.0f}",
        ])
    data.append(["", "", "", "TOTAL", f"{total:,.0f} FCFA"])

    table = Table(data, colWidths=[1.4*cm, 1.8*cm, 4.2*cm, 7.6*cm, 3.6*cm], repeatRows=1)
    table.setStyle(TableStyle(_STYLE_TABLEAU_EXPORT))
    elements.append(table)
    elements.append(Spacer(1, 0.6 * cm))

    _ajouter_recap_pdf(elements, styles, recap_medicaments(ventes))

    resume_style = ParagraphStyle("resume", parent=styles["Normal"], alignment=TA_RIGHT)
    elements.append(Paragraph(f"<b>Nombre de ventes : {len(ventes)}</b>", resume_style))

    doc.build(elements)
    return response


_STYLE_TABLEAU_EXPORT = [
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D4F")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 9.5),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("ALIGN", (2, 1), (3, -2), "LEFT"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
    ("BACKGROUND", (0, 1), (-1, -2), colors.whitesmoke),
    ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
    ("FONTSIZE", (0, 1), (-1, -2), 8.5),
    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8F5E9")),
    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ("TEXTCOLOR", (0, -1), (-1, -1), colors.darkgreen),
]


def _ajouter_recap_pdf(elements, styles, recap):
    """Tableau « Médicaments vendus » : quantité totale par médicament."""
    if not recap:
        return
    sous_titre = ParagraphStyle("recap", parent=styles["Heading3"], spaceBefore=4, spaceAfter=6)
    elements.append(Paragraph("Récapitulatif des médicaments vendus", sous_titre))
    cellule = ParagraphStyle("cellule_recap", parent=styles["Normal"], fontSize=9, leading=11)
    data = [["Médicament", "Quantité vendue", "Montant (FCFA)"]]
    for nom, qte, montant in recap:
        data.append([Paragraph(nom, cellule), str(qte), f"{montant:,.0f}"])
    data.append(["TOTAL", str(sum(q for _, q, _ in recap)),
                 f"{sum(m for _, _, m in recap):,.0f}"])
    table = Table(data, colWidths=[10 * cm, 4 * cm, 4.6 * cm], repeatRows=1)
    table.setStyle(TableStyle(_STYLE_TABLEAU_EXPORT + [("ALIGN", (0, 1), (0, -1), "LEFT")]))
    elements.append(table)
    elements.append(Spacer(1, 0.6 * cm))
