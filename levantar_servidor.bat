@echo off
title Monitorea - Servidor completo
chcp 65001 >nul

cd /d "%~dp0"

echo ============================================
echo   Monitorea - Levantando servidor
echo ============================================

echo.
echo [1/1] Iniciando Django + MQTT (daphne)...
set MQTT_AUTOSTART=1
start "Monitorea - Django Server" cmd /k cd /d "%~dp0CORE" ^& "%~dp0venv\Scripts\daphne.exe" -b 127.0.0.1 -p 8000 MONITOREA.asgi:application

echo.
echo ============================================
echo   Servidor levantado correctamente.
echo   Django + MQTT integrado http://127.0.0.1:8000/
echo ============================================
echo.
pause
