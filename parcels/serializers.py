from rest_framework import serializers
from .models import Parcel

class ParcelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcel
        fields = '__all__'
        read_only_fields = ['id', 'sender_id', 'tracking_id', 'status', 'created_at', 'updated_at']
