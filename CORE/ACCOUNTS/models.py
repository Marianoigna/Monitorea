from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    # Email único — necesario para identificar al usuario en el webhook de MercadoPago
    email = models.EmailField(unique=True)

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
