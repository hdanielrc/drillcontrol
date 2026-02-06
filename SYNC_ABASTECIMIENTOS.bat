@echo off
TITLE Sincronizador de Abastecimientos DrillControl
color 0A
CD /D "%~dp0"

echo ========================================================
echo   Sincronizador Automático de Abastecimientos
echo ========================================================
echo.

:: Activar entorno virtual si existe
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo .venv no encontrado, usando python del sistema...
)

:: Solicitar año (por defecto el actual)
set /p ANIO="Ingrese Año (Enter para actual): "
if "%ANIO%"=="" set ANIO=2025

:: Solicitar Centro de Costo (Opcional)
echo.
echo Opcional: Ingrese codigo Centro de Costo (ej: 000002)
echo Deje en blanco para sincronizar TODOS los contratos.
set /p CC="Centro de Costo: "

:: Construir comando
set CMD=python perforaciones_diamantinas/scripts/sync/sync_abastecimientos.py --year=%ANIO%

if not "%CC%"=="" (
    set CMD=%CMD% --cc=%CC%
)

echo.
echo Ejecutando: %CMD%
echo.
%CMD%

echo.
echo ========================================================
echo   Proceso Finalizado. Revise los logs si hubo errores.
echo ========================================================
pause
