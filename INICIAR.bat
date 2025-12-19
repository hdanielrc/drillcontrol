@echo off
REM Script rapido para iniciar el servidor Django

cd /d "%~dp0perforaciones_diamantinas"

if not exist "venv" (
    echo ERROR: Entorno virtual no encontrado
    echo Por favor ejecuta INSTALAR.bat primero
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo ========================================
echo   DRILL CONTROL - SERVIDOR DESARROLLO
echo ========================================
echo.
echo [*] Iniciando servidor Django...
echo [*] Accede en: http://localhost:8000
echo [*] Presiona Ctrl+C para detener
echo.

python manage.py runserver
