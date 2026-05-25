from django.db import models


class Temperatura(models.Model):
    valor = models.FloatField()
    sensor_id = models.CharField(max_length=50, default='sensor_01')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Temperatura'
        verbose_name_plural = 'Temperaturas'
        db_table = 'DASHBOARD_TEMP_VOLT_temperatura'

    def __str__(self):
        return f'{self.sensor_id}: {self.valor}°C @ {self.timestamp}'


class Voltaje(models.Model):
    valor = models.FloatField()
    sensor_id = models.CharField(max_length=50, default='voltaje_01')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Voltaje'
        verbose_name_plural = 'Voltajes'

    def __str__(self):
        return f'{self.sensor_id}: {self.valor}V @ {self.timestamp}'
