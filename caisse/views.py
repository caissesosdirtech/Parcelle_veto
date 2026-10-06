import json
from django.shortcuts import render
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

# Dépendances ReportLab (PDF)
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# Dépendances OpenPyXL (Excel)
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

# Modèles
from ventes.models import Vente
from ventes.medicaments_vendus import recap_medicaments, texte_medicaments


# ── VUE WEB ───────────────────────────────────────────────────────────────────

@login_required
def rapport_caisse(request):
    """Affiche le rapport de caisse avec statistiques et historique filtrable."""
    if hasattr(request.user, 'role') and request.user.role == 'EMPLOYE' and not request.user.is_superuser:
        raise PermissionDenied("Accès refusé : Le rapport de caisse est strictly réservé aux docteurs.")

    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    ventes = (
        Vente.objects.select_related(
            "client",
            "ordonnance__consultation__client",
            "ordonnance__consultation__animal",
        )
        .prefetch_related("lignes__medicament")
        .order_by("-date", "-id")
    )

    if date_debut:
        ventes = ventes.filter(date__date__gte=date_debut)
    if date_fin:
        ventes = ventes.filter(date__date__lte=date_fin)

    total_recettes = ventes.aggregate(total=Sum("total"))["total"] or 0
    recettes_jour = Vente.objects.filter(
        date__date=timezone.now().date()
    ).aggregate(total=Sum("total"))["total"] or 0
    nombre_ventes = ventes.count()
    ticket_moyen = (total_recettes / nombre_ventes) if nombre_ventes > 0 else 0

    recettes = (
        ventes
        .annotate(jour=TruncDate("date"))
        .values("jour")
        .annotate(total=Sum("total"))
        .order_by("jour")
    )

    return render(request, "caisse/rapport_caisse.html", {
        "ventes": ventes,
        "total_recettes": total_recettes,
        "recettes_jour": recettes_jour,
        "nombre_ventes": nombre_ventes,
        "ticket_moyen": ticket_moyen,
        "recettes": recettes,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "active_page": "caisse",
    })


# ── API FLUTTER ───────────────────────────────────────────────────────────────

def api_rapport_caisse(request):
    """
    GET /caisse/api/rapport/?date_debut=YYYY-MM-DD&date_fin=YYYY-MM-DD
    Retourne les statistiques et la liste des ventes pour CaisseScreen Flutter.
    """
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    ventes_qs = (
        Vente.objects.select_related(
            "client",
            "ordonnance__consultation__client",
            "ordonnance__consultation__animal",
        )
        .order_by("-date", "-id")
    )

    if date_debut:
        ventes_qs = ventes_qs.filter(date__date__gte=date_debut)
    if date_fin:
        ventes_qs = ventes_qs.filter(date__date__lte=date_fin)

    total_recettes = ventes_qs.aggregate(total=Sum("total"))["total"] or 0
    recettes_jour = Vente.objects.filter(
        date__date=timezone.now().date()
    ).aggregate(total=Sum("total"))["total"] or 0
    nombre_ventes = ventes_qs.count()
    ticket_moyen = (float(total_recettes) / nombre_ventes) if nombre_ventes > 0 else 0

    ventes_data = []
    for v in ventes_qs:
        try:
            if v.ordonnance and v.ordonnance.consultation:
                client = v.ordonnance.consultation.client.nom
                animal = v.ordonnance.consultation.animal.nom
                type_vente = "Ordonnance"
            else:
                client = v.client.nom if v.client else "Anonyme"
                animal = ""
                type_vente = "Directe"
        except Exception:
            client = "Anonyme"
            animal = ""
            type_vente = "Directe"

        ventes_data.append({
            "id": v.id,
            "date": v.date.strftime("%d/%m/%Y"),
            "client": client,
            "animal": animal,
            "type": type_vente,
            "montant": float(v.total or 0),
        })

    return JsonResponse({
        "stats": {
            "total_recettes": float(total_recettes),
            "recettes_jour": float(recettes_jour),
            "nombre_ventes": nombre_ventes,
            "ticket_moyen": round(ticket_moyen, 0),
        },
        "ventes": ventes_data,
    }, status=200)


# ── PDF ───────────────────────────────────────────────────────────────────────

def rapport_caisse_pdf(request):
    """Génère un rapport de caisse imprimable au format PDF."""
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    ventes = (
        Vente.objects.select_related(
            "client",
            "ordonnance__consultation__client",
            "ordonnance__consultation__animal",
        )
        .prefetch_related("lignes__medicament__catalogue")
        .order_by("-date", "-id")
    )

    if date_debut:
        ventes = ventes.filter(date__date__gte=date_debut)
    if date_fin:
        ventes = ventes.filter(date__date__lte=date_fin)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="rapport_caisse_parcelles_veto.pdf"'

    doc = SimpleDocTemplate(
        response, pagesize=A4,
        rightMargin=1.2 * cm, leftMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
    )

    styles = getSampleStyleSheet()
    cellule = ParagraphStyle("cellule", parent=styles["Normal"], fontSize=8, leading=10)
    elements = []

    # En-tête
    gauche = Paragraph(
        "<b>Dr. Ibrahima Pierre GUISSE</b><br/>"
        "Parcelles Assainies<br/>Thiès, Sénégal<br/>"
        "En face des cimetières Keur Dago<br/>"
        "Tél : 221 775385729 / 768331623<br/>"
        "E-mail : parcelles-veto@gmail.com",
        styles["Normal"],
    )
    droite = Paragraph(
        f'<para alignment="right"><b>Date :</b><br/>'
        f'{timezone.now().strftime("%d/%m/%Y %H:%M")}</para>',
        styles["Normal"],
    )
    header = Table([[gauche, droite]], colWidths=[12 * cm, 6 * cm])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 0.4 * cm))

    # Titre
    titre_style = styles["Heading2"]
    titre_style.alignment = TA_CENTER
    elements.append(Paragraph("<b>RAPPORT DE CAISSE - PARCELLES VETO</b>", titre_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Tableau des ventes
    ventes = list(ventes)
    data = [["N°", "Date", "Client", "Animal", "Type", "Médicaments vendus", "Montant (FCFA)"]]
    total_general = 0

    for vente in ventes:
        try:
            if vente.ordonnance and vente.ordonnance.consultation:
                client = vente.ordonnance.consultation.client.nom
                animal = vente.ordonnance.consultation.animal.nom
                type_vente = "Ordonnance"
            else:
                client = vente.client.nom if vente.client else "Anonyme"
                animal = "-"
                type_vente = "Directe"
        except Exception:
            client = "Anonyme"
            animal = "-"
            type_vente = "Directe"

        montant = vente.total or 0
        total_general += montant
        data.append([
            str(vente.id),
            vente.date.strftime("%d/%m/%Y"),
            Paragraph(client, cellule), Paragraph(animal, cellule), type_vente,
            Paragraph(texte_medicaments(vente), cellule),
            f"{montant:,.0f}",
        ])

    data.append(["", "", "", "", "", "TOTAL", f"{total_general:,.0f} FCFA"])

    table = Table(
        data,
        colWidths=[1.1 * cm, 2 * cm, 3.2 * cm, 2.4 * cm, 2 * cm, 5.2 * cm, 2.7 * cm],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -2), colors.whitesmoke),
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -2), 8),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8F5E9")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.darkgreen),
        ("FONTSIZE", (0, -1), (-1, -1), 10),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.6 * cm))

    # Récapitulatif : quantité vendue par médicament sur la période
    recap = recap_medicaments(ventes)
    if recap:
        elements.append(Paragraph("<b>Récapitulatif des médicaments vendus</b>", styles["Heading3"]))
        data_recap = [["Médicament", "Quantité vendue", "Montant (FCFA)"]]
        for nom, qte, montant_med in recap:
            data_recap.append([Paragraph(nom, cellule), str(qte), f"{montant_med:,.0f}"])
        data_recap.append(["TOTAL", str(sum(q for _, q, _ in recap)),
                           f"{sum(m for _, _, m in recap):,.0f}"])
        table_recap = Table(data_recap, colWidths=[10 * cm, 4 * cm, 4.6 * cm], repeatRows=1)
        table_recap.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 1), (-1, -2), colors.whitesmoke),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8F5E9")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.darkgreen),
        ]))
        elements.append(table_recap)
        elements.append(Spacer(1, 0.6 * cm))

    resume_style = ParagraphStyle("resume", parent=styles["Normal"], alignment=TA_RIGHT)
    elements.append(Paragraph(f"<b>Total général : {total_general:,.0f} FCFA</b>", resume_style))
    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph(
        "<para alignment='center'><font size='9'>Parcelles Veto - La santé animale, notre priorité.</font></para>",
        styles["Normal"],
    ))

    doc.build(elements)
    return response


# ── EXPORT EXCEL ─────────────────────────────────────────────────────────────

def export_caisse_excel(request):
    """Exporte les ventes de la caisse sous format tableur Excel (.xlsx)."""
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    ventes = (
        Vente.objects.select_related(
            "client",
            "ordonnance__consultation__client",
            "ordonnance__consultation__animal",
        )
        .prefetch_related("lignes__medicament__catalogue")
        .order_by("-date", "-id")
    )

    if date_debut:
        ventes = ventes.filter(date__date__gte=date_debut)
    if date_fin:
        ventes = ventes.filter(date__date__lte=date_fin)

    wb = Workbook()
    ws = wb.active
    ws.title = "Rapport Caisse"

    ventes = list(ventes)
    headers = ["N°", "Date", "Client", "Animal", "Type", "Médicaments vendus", "Montant (FCFA)"]
    ws.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2E7D4F", end_color="2E7D4F", fill_type="solid")
    
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    total_general = 0
    for vente in ventes:
        try:
            if vente.ordonnance and vente.ordonnance.consultation:
                client = vente.ordonnance.consultation.client.nom
                animal = vente.ordonnance.consultation.animal.nom
                type_vente = "Ordonnance"
            else:
                client = vente.client.nom if vente.client else "Anonyme"
                animal = "-"
                type_vente = "Directe"
        except Exception:
            client = "Anonyme"
            animal = "-"
            type_vente = "Directe"

        montant = float(vente.total or 0)
        total_general += montant
        ws.append([
            vente.id,
            vente.date.strftime("%d/%m/%Y"),
            client, animal, type_vente,
            texte_medicaments(vente),
            montant,
        ])
        ws.cell(row=ws.max_row, column=6).alignment = Alignment(wrap_text=True, vertical="top")

    # Ligne de total
    ws.append(["", "", "", "", "", "TOTAL", float(total_general)])
    last_row = ws.max_row
    for col in range(1, 8):
        ws.cell(row=last_row, column=col).font = Font(bold=True)

    for col_letter, largeur in zip("ABCDEFG", [8, 12, 22, 16, 12, 50, 16]):
        ws.column_dimensions[col_letter].width = largeur

    # Deuxième feuille : quantité vendue par médicament
    ws2 = wb.create_sheet("Médicaments vendus")
    ws2.append(["Médicament", "Quantité vendue", "Montant (FCFA)"])
    for col in range(1, 4):
        cell = ws2.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    for nom, qte, montant_med in recap_medicaments(ventes):
        ws2.append([nom, qte, montant_med])
    for col_letter, largeur in zip("ABC", [36, 18, 18]):
        ws2.column_dimensions[col_letter].width = largeur

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="rapport_caisse.xlsx"'
    wb.save(response)
    return response