from django.contrib import admin

from .models import FamilleMedicament, CatalogueMedicament, Medicament


@admin.register(FamilleMedicament)
class FamilleMedicamentAdmin(admin.ModelAdmin):
    list_display = ('nom',)
    search_fields = ('nom',)


@admin.register(CatalogueMedicament)
class CatalogueMedicamentAdmin(admin.ModelAdmin):
    list_display = ('nom', 'famille')
    list_filter = ('famille',)
    search_fields = ('nom',)


@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = ('catalogue', 'stock', 'prix', 'seuil_alerte', 'fournisseur')
    list_filter = ('fournisseur',)
    search_fields = ('catalogue__nom',)