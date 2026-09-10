from django.contrib import admin

from .models import MouvementCaisse


@admin.register(MouvementCaisse)
class MouvementCaisseAdmin(admin.ModelAdmin):
    list_display = ('type_mouvement', 'montant', 'motif', 'date')
    list_filter = ('type_mouvement',)