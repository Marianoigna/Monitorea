from rest_framework import serializers
from .models import Telemetria


class TelemetriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Telemetria
        fields = ['id', 'dispositivo', 'tipo_sensor', 'canal', 'valor', 'timestamp']
        read_only_fields = ['id', 'timestamp']
