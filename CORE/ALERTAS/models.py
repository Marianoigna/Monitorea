from django.db import models

TIPO_SENSOR_CHOICES = [
    ('temperatura', 'Temperatura'),
    ('tension',     'Tensión'),
    ('corriente',   'Corriente'),
    ('humedad',     'Humedad'),
    ('presion',     'Presión'),
]


class ConfiguracionAlerta(models.Model):
    dispositivo = models.ForeignKey(
        'DASHBOARD.Dispositivo',
        on_delete=models.CASCADE,
        related_name='alertas',
    )
    tipo_sensor = models.CharField(max_length=20, choices=TIPO_SENSOR_CHOICES)
    min_valor = models.FloatField(null=True, blank=True)
    max_valor = models.FloatField(null=True, blank=True)
    whatsapp_destino = models.CharField(max_length=20, null=True, blank=True)
    ultima_notificacion = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('dispositivo', 'tipo_sensor')
        verbose_name = 'Configuración de alerta'
        verbose_name_plural = 'Configuraciones de alertas'

    def __str__(self):
        return f'{self.dispositivo.nombre} — {self.tipo_sensor}'


class HistorialAlerta(models.Model):
    dispositivo = models.ForeignKey(
        'DASHBOARD.Dispositivo',
        on_delete=models.CASCADE,
        related_name='historial_alertas',
    )
    tipo_sensor = models.CharField(max_length=20)
    valor_disparador = models.FloatField()
    mensaje = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Historial de alerta'
        verbose_name_plural = 'Historial de alertas'

    def __str__(self):
        return f'{self.dispositivo.nombre} — {self.tipo_sensor} @ {self.timestamp}'
