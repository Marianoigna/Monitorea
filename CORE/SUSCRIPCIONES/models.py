from django.db import models
from django.conf import settings
from django.utils import timezone


class Plan(models.Model):
    GRATUITO = 'gratuito'
    PREMIUM  = 'premium'   # legacy (preexistente)
    MENSUAL  = 'mensual'
    ANUAL    = 'anual'
    TIPO_CHOICES = [
        (GRATUITO, 'Gratuito'),
        (PREMIUM,  'Premium'),
        (MENSUAL,  'Mensual'),
        (ANUAL,    'Anual'),
    ]

    nombre           = models.CharField(max_length=50, choices=TIPO_CHOICES, unique=True)
    precio_mensual   = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    descripcion      = models.TextField(blank=True)

    def es_premium(self):
        """True para cualquier tipo de plan de pago."""
        return self.nombre in (self.PREMIUM, self.MENSUAL, self.ANUAL)

    def __str__(self):
        return self.get_nombre_display()


class Suscripcion(models.Model):
    ACTIVA     = 'activa'
    VENCIDA    = 'vencida'
    CANCELADA  = 'cancelada'
    TRIAL      = 'trial'
    ESTADO_CHOICES = [
        (ACTIVA,    'Activa'),
        (VENCIDA,   'Vencida'),
        (CANCELADA, 'Cancelada'),
        (TRIAL,     'Período de prueba'),
    ]

    usuario            = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='suscripcion',
    )
    plan               = models.ForeignKey(Plan, on_delete=models.PROTECT)
    estado             = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ACTIVA)
    fecha_inicio       = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento  = models.DateTimeField()
    # ID de suscripción recurrente en Mercado Pago (preapproval id)
    gateway_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    # Código de 6 dígitos para confirmar la anulación por correo
    codigo_cancelacion      = models.CharField(max_length=6, blank=True, null=True)

    def esta_activa(self):
        """Devuelve True si el plan es de pago y la suscripción no venció."""
        return (
            self.plan.es_premium()
            and self.estado == self.ACTIVA
            and self.fecha_vencimiento > timezone.now()
        )

    def __str__(self):
        return f'{self.usuario.username} — {self.plan} ({self.estado})'


class Pago(models.Model):
    suscripcion        = models.ForeignKey(Suscripcion, on_delete=models.CASCADE, related_name='pagos')
    monto              = models.DecimalField(max_digits=8, decimal_places=2)
    fecha              = models.DateTimeField(auto_now_add=True)
    metodo             = models.CharField(max_length=50, blank=True)   # 'stripe', 'mercadopago', etc.
    referencia_gateway = models.CharField(max_length=200, blank=True)  # ID de transacción externo
    exitoso            = models.BooleanField(default=True)

    def __str__(self):
        return f'Pago ${self.monto} — {self.suscripcion.usuario.username} ({self.fecha.date()})'
