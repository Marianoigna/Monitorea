from rest_framework import serializers
from .models import Temperatura


class TemperaturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Temperatura
        fields = ['id', 'sensor_id', 'valor', 'timestamp']
        read_only_fields = ['id', 'timestamp']
