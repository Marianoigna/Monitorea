from django.contrib import admin

from .models import ConfiguracionAlerta, HistorialAlerta


@admin.register(ConfiguracionAlerta)
class ConfiguracionAlertaAdmin(admin.ModelAdmin):
    list_display  = ('dispositivo', 'tipo_sensor', 'min_valor', 'max_valor', 'whatsapp_destino', 'activo')
    list_filter   = ('tipo_sensor', 'activo')
    search_fields = ('dispositivo__nombre',)


@admin.register(HistorialAlerta)
class HistorialAlertaAdmin(admin.ModelAdmin):
    list_display  = ('dispositivo', 'tipo_sensor', 'valor_disparador', 'timestamp')
    list_filter   = ('tipo_sensor',)
    search_fields = ('dispositivo__nombre', 'mensaje')
    readonly_fields = ('timestamp',)
