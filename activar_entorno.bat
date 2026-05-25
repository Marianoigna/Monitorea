@echo off
title ERROR PROOFING - Entorno Virtual

:: Cambiar al directorio del proyecto
cd /d "%~dp0"

echo ============================================
echo   Activando entorno virtual - ERROR PROOFING
echo ============================================

:: Activar el entorno virtual usando cmd.exe (no requiere cambiar ExecutionPolicy)
call "%~dp0venv\Scripts\activate.bat"

echo.
echo [OK] Entorno virtual activado correctamente.
echo      Python activo: 
python -c "import sys; print(sys.executable)"
echo.

:: Abrir una nueva sesion de PowerShell con el entorno activado
powershell -NoExit -ExecutionPolicy RemoteSigned -Command "& '%~dp0venv\Scripts\Activate.ps1'; Write-Host '✔ Entorno venv activo en PowerShell' -ForegroundColor Green"
