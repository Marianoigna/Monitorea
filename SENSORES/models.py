from django.db import models


class Temperatura(models.Model):
    valor = models.FloatField()                          # Valor de temperatura
    sensor_id = models.CharField(max_length=50, default='sensor_01')  # ID del sensor
    timestamp = models.DateTimeField(auto_now_add=True)  # Fecha/hora automática

    class Meta:
        ordering = ['-timestamp']                        # Más reciente primero
        verbose_name = 'Temperatura'
        verbose_name_plural = 'Temperaturas'

    def __str__(self):
        return f'{self.sensor_id}: {self.valor}°C @ {self.timestamp}'
