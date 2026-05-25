@echo off
title ERROR PROOFING — Servidor completo

cd /d "%~dp0"

echo ============================================
echo   ERROR PROOFING — Levantando servidor
echo ============================================

:: Activar entorno virtual
call "%~dp0venv\Scripts\activate.bat"

echo.
echo [1/2] Iniciando MQTT Subscriber...
start "MQTT Subscriber" cmd /k "cd /d ""%~dp0CORE"" && call ""%~dp0venv\Scripts\activate.bat"" && python mqtt_subscriber.py"

:: Pequeña pausa para que el subscriber se conecte primero
timeout /t 2 /nobreak >nul

echo [2/2] Iniciando Django (daphne)...
start "Django Server" cmd /k "cd /d ""%~dp0CORE"" && call ""%~dp0venv\Scripts\activate.bat"" && daphne -b 127.0.0.1 -p 8000 MONITOREA.asgi:application"

echo.
echo ============================================
echo   Ambos procesos levantados correctamente.
echo   Django  → http://127.0.0.1:8000/
echo   MQTT    → broker.emqx.io / temperatura_prueba
echo ============================================
echo.
pause
