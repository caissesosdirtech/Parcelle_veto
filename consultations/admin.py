from django.contrib import admin

from .models import (
    RendezVous,
    RendezVousManuel,
    Consultation,
    Ordonnance,
    LigneOrdonnance,
)


class VerrouAdminMixin:
    """Un rendez-vous terminé s'affiche en lecture seule dans l'administration."""

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.est_verrouille:
            return False
        return super().has_change_permission(request, obj)


@admin.register(RendezVous)
class RendezVousAdmin(VerrouAdminMixin, admin.ModelAdmin):
    list_display = ('animal', 'date_rdv', 'type_rdv', 'statut')
    list_filter = ('statut', 'type_rdv')


@admin.register(RendezVousManuel)
class RendezVousManuelAdmin(VerrouAdminMixin, admin.ModelAdmin):
    list_display = ('nom_client', 'nom_animal', 'date_rdv', 'lieu', 'statut')
    list_filter = ('statut', 'lieu')
    search_fields = ('nom_client', 'nom_animal', 'telephone')


class LigneOrdonnanceInline(admin.TabularInline):
    model = LigneOrdonnance
    extra = 1


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('client', 'animal', 'date', 'statut', 'lieu', 'veterinaire')
    list_filter = ('statut', 'lieu')
    search_fields = ('client__nom', 'animal__nom')


@admin.register(Ordonnance)
class OrdonnanceAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'date_creation')
    inlines = [LigneOrdonnanceInline]


@admin.register(LigneOrdonnance)
class LigneOrdonnanceAdmin(admin.ModelAdmin):
    list_display = ('ordonnance', 'medicament', 'quantite', 'posologie')