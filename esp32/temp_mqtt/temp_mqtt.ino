/*
 * temp_mqtt.ino
 * =============
 * Sketch para ESP32 con sensor de temperatura DS18B20.
 * Lee la temperatura y la publica via MQTT (broker.emqx.io:1883) al topic
 * configurado. El servidor Django recibe los datos a través del
 * mqtt_client.py integrado.
 *
 * Hardware necesario:
 *   - ESP32 (cualquier variante)
 *   - Sensor DS18B20 (One-Wire)
 *     · Pin DATA → GPIO4 (configurable con PIN_TEMP)
 *     · Resistencia pull-up de 4.7kΩ entre DATA y 3.3V
 *
 * Dependencias (instalar desde el Library Manager del IDE):
 *   - PubSubClient (Nick O'Leary)
 *   - OneWire (Paul Stoffregen)
 *   - DallasTemperature (Miles Burton)
 *
 * Configuración rápida:
 *   1. Modificar WIFI_SSID y WIFI_PASSWORD con los datos de tu red.
 *   2. Ajustar MQTT_TOPIC_TEMP si usás un topic personalizado.
 *   3. Ajustar SENSOR_ID para identificar el sensor en el dashboard.
 *   4. Flashear el ESP32 y abrir el Serial Monitor a 115200 bps.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>

// ── WiFi ──────────────────────────────────────────────────────────────────────
const char* WIFI_SSID     = "TU_RED_WIFI";
const char* WIFI_PASSWORD = "TU_CONTRASEÑA";

// ── MQTT ──────────────────────────────────────────────────────────────────────
const char* MQTT_BROKER   = "broker.emqx.io";
const int   MQTT_PORT     = 1883;           // TCP sin TLS (más simple en ESP32)
const char* MQTT_TOPIC_TEMP = "temperatura_prueba";
const char* SENSOR_ID     = "heladera_01"; // Identificador del sensor en el dashboard

// ── Sensor DS18B20 ────────────────────────────────────────────────────────────
const int PIN_TEMP = 4;                    // GPIO donde está el pin DATA del DS18B20
OneWire oneWire(PIN_TEMP);
DallasTemperature sensors(&oneWire);

// ── Intervalo de publicación ──────────────────────────────────────────────────
const unsigned long INTERVALO_MS = 10000;  // Publicar cada 10 segundos

// ── Variables globales ────────────────────────────────────────────────────────
WiFiClient   wifiClient;
PubSubClient mqttClient(wifiClient);
unsigned long ultimaPublicacion = 0;


// ── Funciones de conexión ─────────────────────────────────────────────────────

void conectarWiFi() {
    if (WiFi.status() == WL_CONNECTED) return;

    Serial.printf("[WiFi] Conectando a %s", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int intentos = 0;
    while (WiFi.status() != WL_CONNECTED && intentos < 30) {
        delay(500);
        Serial.print(".");
        intentos++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[WiFi] Conectado. IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[WiFi] Error de conexión. Reintentando en el próximo ciclo.");
    }
}

void conectarMQTT() {
    if (mqttClient.connected()) return;

    String clientId = "ESP32_" + String(SENSOR_ID) + "_" + String(random(0xffff), HEX);

    Serial.printf("[MQTT] Conectando a %s:%d ...", MQTT_BROKER, MQTT_PORT);

    if (mqttClient.connect(clientId.c_str())) {
        Serial.println(" OK");
    } else {
        Serial.printf(" Error: %d\n", mqttClient.state());
    }
}

// ── Publicar temperatura ──────────────────────────────────────────────────────

void publicarTemperatura() {
    sensors.requestTemperatures();
    float temperatura = sensors.getTempCByIndex(0);

    if (temperatura == DEVICE_DISCONNECTED_C) {
        Serial.println("[Sensor] Error: sensor desconectado");
        return;
    }

    // Crear payload JSON
    StaticJsonDocument<128> doc;
    doc["sensor_id"] = SENSOR_ID;
    doc["valor"]     = temperatura;

    char payload[128];
    serializeJson(doc, payload);

    if (mqttClient.publish(MQTT_TOPIC_TEMP, payload)) {
        Serial.printf("[MQTT] Publicado: %s → %s\n", MQTT_TOPIC_TEMP, payload);
    } else {
        Serial.println("[MQTT] Error al publicar");
    }
}

// ── Setup y Loop ──────────────────────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    Serial.println("\n=== CONTROL TEMPERATURA ESP32 ===");

    sensors.begin();
    Serial.printf("[Sensor] DS18B20 detectado en GPIO%d\n", PIN_TEMP);

    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);

    conectarWiFi();
    conectarMQTT();
}

void loop() {
    // Mantener conexiones activas
    if (WiFi.status() != WL_CONNECTED) {
        conectarWiFi();
    }
    if (!mqttClient.connected()) {
        conectarMQTT();
    }
    mqttClient.loop();

    // Publicar temperatura según intervalo
    unsigned long ahora = millis();
    if (ahora - ultimaPublicacion >= INTERVALO_MS) {
        ultimaPublicacion = ahora;
        publicarTemperatura();
    }
}
