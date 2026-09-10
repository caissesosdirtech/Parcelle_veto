from django.contrib import admin

from .models import Animal


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ('nom', 'espece', 'race', 'sexe', 'client')
    list_filter = ('espece', 'sexe')
    search_fields = ('nom', 'client__nom')