from django.contrib import admin

from .models import Fournisseur


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'telephone', 'email')
    search_fields = ('nom', 'email')