from django.db import models
from django.conf import settings


class Establecimiento(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='establecimientos',
    )
    nombre = models.CharField(max_length=150, help_text='Nombre de la sucursal o unidad')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Establecimiento'
        verbose_name_plural = 'Establecimientos'

    def __str__(self):
        return f'{self.usuario.empresa} — {self.nombre}'


class Dispositivo(models.Model):
    establecimiento = models.ForeignKey(
        Establecimiento,
        on_delete=models.CASCADE,
        related_name='dispositivos',
    )
    nombre = models.CharField(max_length=150, help_text='Ej: Tablero Principal, Cámara 1')
    mac_address = models.CharField(
        max_length=17,
        unique=True,
        help_text='Dirección MAC del ESP32 (ej: AA:BB:CC:DD:EE:FF)',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Dispositivo'
        verbose_name_plural = 'Dispositivos'

    def __str__(self):
        return f'{self.nombre} ({self.mac_address})'


TIPO_SENSOR_CHOICES = [
    ('temperatura', 'Temperatura'),
    ('tension',     'Tensión'),
    ('corriente',   'Corriente'),
    ('humedad',     'Humedad'),
    ('presion',     'Presión'),
]


class SensorConfig(models.Model):
    dispositivo = models.ForeignKey(
        Dispositivo,
        on_delete=models.CASCADE,
        related_name='sensores',
    )
    tipo_sensor = models.CharField(max_length=20, choices=TIPO_SENSOR_CHOICES)
    canal = models.IntegerField(help_text='Índice del canal en el payload JSON (0, 1, 2…)')
    nombre_personalizado = models.CharField(
        max_length=100,
        help_text='Ej: Temp. Retorno, Fase R',
    )

    class Meta:
        unique_together = ('dispositivo', 'tipo_sensor', 'canal')
        ordering = ['tipo_sensor', 'canal']
        verbose_name = 'Configuración de sensor'
        verbose_name_plural = 'Configuraciones de sensores'

    def __str__(self):
        return f'{self.nombre_personalizado} ({self.tipo_sensor}[{self.canal}])'


class Telemetria(models.Model):
    """Lectura genérica de cualquier tipo de sensor."""
    dispositivo = models.ForeignKey(
        Dispositivo,
        on_delete=models.CASCADE,
        related_name='telemetrias',
    )
    tipo_sensor = models.CharField(max_length=20, choices=TIPO_SENSOR_CHOICES)
    canal = models.IntegerField(default=0)
    valor = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Telemetría'
        verbose_name_plural = 'Telemetrías'

    def __str__(self):
        return f'{self.dispositivo.mac_address}[{self.tipo_sensor}:{self.canal}]: {self.valor} @ {self.timestamp}'
