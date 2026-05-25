from rest_framework import serializers
from .models import Temperatura, Voltaje


class TemperaturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Temperatura
        fields = ['id', 'sensor_id', 'valor', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class VoltajeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voltaje
        fields = ['id', 'sensor_id', 'valor', 'timestamp']
        read_only_fields = ['id', 'timestamp']
