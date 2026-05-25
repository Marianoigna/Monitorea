from django.test import TestCase
from .models import Temperatura, Voltaje


class TemperaturaModelTest(TestCase):
    def test_crear_temperatura(self):
        t = Temperatura.objects.create(valor=5.0, sensor_id='heladera_01')
        self.assertEqual(t.valor, 5.0)
        self.assertEqual(t.sensor_id, 'heladera_01')
        self.assertIsNotNone(t.timestamp)

    def test_str_temperatura(self):
        t = Temperatura.objects.create(valor=-18.0, sensor_id='freezer_01')
        self.assertIn('freezer_01', str(t))
        self.assertIn('-18.0', str(t))


class VoltajeModelTest(TestCase):
    def test_crear_voltaje(self):
        v = Voltaje.objects.create(valor=220.5, sensor_id='voltaje_01')
        self.assertEqual(v.valor, 220.5)
        self.assertEqual(v.sensor_id, 'voltaje_01')

    def test_str_voltaje(self):
        v = Voltaje.objects.create(valor=220.0, sensor_id='voltaje_01')
        self.assertIn('voltaje_01', str(v))
        self.assertIn('220.0', str(v))
