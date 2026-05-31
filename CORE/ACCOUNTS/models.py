from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


THEME_CHOICES = [
    ('auto',  'Auto (sistema)'),
    ('light', 'Claro'),
    ('dark',  'Oscuro'),
]


class CustomUser(AbstractUser):
    # Email único — necesario para identificar al usuario en el webhook de MercadoPago
    email = models.EmailField(unique=True)

    # Nombre de la empresa del usuario (obligatorio en el registro)
    empresa = models.CharField(max_length=150, help_text='Nombre de la empresa')

    # Preferencia de tema de la interfaz
    theme = models.CharField(max_length=10, default='auto', choices=THEME_CHOICES)

    # Campos de suscripción (actualizados automáticamente por el webhook de MP)
    is_premium    = models.BooleanField(default=False)
    premium_until = models.DateTimeField(null=True, blank=True)

    def tiene_premium_activo(self):
        """True si el usuario tiene suscripción premium vigente."""
        return (
            self.is_premium
            and self.premium_until is not None
            and self.premium_until > timezone.now()
        )

    def __str__(self):
        return self.username
