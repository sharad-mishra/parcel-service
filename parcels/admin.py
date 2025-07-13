from django.contrib import admin
from .models import Parcel

@admin.register(Parcel)
class ParcelAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender_id', 'status', 'created_at')
    search_fields = ('id', 'sender_id', 'assigned_driver_id')
