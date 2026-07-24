# caisse/urls.py — version finale avec exports
from django.urls import path
from . import views

urlpatterns = [
    path("", views.rapport_caisse, name="caisse"),
    path("rapport/", views.rapport_caisse, name="rapport_caisse"),
    path("rapport/pdf/", views.rapport_caisse_pdf, name="rapport_caisse_pdf"),
    path("api/rapport/", views.api_rapport_caisse, name="api_rapport_caisse"),

    # ✅ Export Excel
    path("export/excel/", views.export_caisse_excel, name="export_caisse_excel"),
]