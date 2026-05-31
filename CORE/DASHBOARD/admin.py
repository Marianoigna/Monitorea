from django.contrib import admin
from .models import Establecimiento, Dispositivo, SensorConfig, Temperatura, Voltaje


@admin.register(Establecimiento)
class EstablecimientoAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'usuario', 'fecha_creacion')
    list_filter   = ('usuario',)
    search_fields = ('nombre', 'usuario__username', 'usuario__empresa')


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'mac_address', 'establecimiento', 'fecha_creacion')
    list_filter   = ('establecimiento__usuario',)
    search_fields = ('nombre', 'mac_address')


@admin.register(SensorConfig)
class SensorConfigAdmin(admin.ModelAdmin):
    list_display  = ('nombre_personalizado', 'tipo_sensor', 'canal', 'dispositivo')
    list_filter   = ('tipo_sensor',)
    search_fields = ('nombre_personalizado', 'dispositivo__nombre', 'dispositivo__mac_address')


@admin.register(Temperatura)
class TemperaturaAdmin(admin.ModelAdmin):
    list_display = ('dispositivo', 'canal', 'valor', 'timestamp')
    list_filter  = ('dispositivo',)
    ordering     = ('-timestamp',)


@admin.register(Voltaje)
class VoltajeAdmin(admin.ModelAdmin):
    list_display = ('dispositivo', 'canal', 'valor', 'timestamp')
    list_filter  = ('dispositivo',)
    ordering     = ('-timestamp',)
