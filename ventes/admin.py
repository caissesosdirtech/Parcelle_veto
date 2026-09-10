from django.contrib import admin

from .models import Vente, LigneVente


class LigneVenteInline(admin.TabularInline):
    model = LigneVente
    extra = 1


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'date', 'total', 'ordonnance')
    list_filter = ('date',)
    search_fields = ('client__nom',)
    inlines = [LigneVenteInline]


@admin.register(LigneVente)
class LigneVenteAdmin(admin.ModelAdmin):
    list_display = ('vente', 'medicament', 'quantite', 'prix_unitaire', 'montant_total')