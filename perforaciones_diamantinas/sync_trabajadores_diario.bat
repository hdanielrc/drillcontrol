@echo off
setlocal
REM ====================================================================
REM Script de Sincronización Diaria de Trabajadores
REM Se ejecuta automáticamente a las 4:00 AM mediante Task Scheduler
REM Sincroniza trabajadores desde la API de Vilbra Group
REM ====================================================================

echo [%date% %time%] Iniciando sincronizacion diaria de trabajadores...

REM Cambiar al directorio del proyecto
cd /d "%~dp0"

REM Crear directorio de logs si no existe
if not exist "logs" mkdir logs

REM Activar entorno virtual si existe
if exist "..\venv\Scripts\activate.bat" (
    call ..\venv\Scripts\activate.bat
    echo Entorno virtual activado
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo Entorno virtual activado
)

REM Ejecutar el script de sincronización
echo Ejecutando sync_trabajadores.py...
python scripts\sync\sync_trabajadores.py >> logs\sync_trabajadores_%date:~-4,4%%date:~-7,2%%date:~0,2%.log 2>&1

if %errorlevel% == 0 (
    echo [%date% %time%] Sincronizacion completada exitosamente.
) else (
    echo [%date% %time%] ERROR en la sincronizacion. Revisa logs\sync_trabajadores_*.log
)

endlocal
