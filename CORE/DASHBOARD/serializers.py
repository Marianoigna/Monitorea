from rest_framework import serializers
from .models import Temperatura, Voltaje


class TemperaturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Temperatura
        fields = ['id', 'dispositivo', 'canal', 'valor', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class VoltajeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voltaje
        fields = ['id', 'dispositivo', 'canal', 'valor', 'timestamp']
        read_only_fields = ['id', 'timestamp']
