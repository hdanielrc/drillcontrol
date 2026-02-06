@echo off
REM ====================================================================
REM Script de Sincronización Diaria de Abastecimientos - TODOS LOS CENTROS DDH
REM Se ejecuta automáticamente a las 4:00 AM mediante Task Scheduler
REM Sincroniza los 19 centros de costo DDH configurados
REM ====================================================================

echo [%date% %time%] Iniciando sincronizacion diaria de abastecimientos DDH...

REM Cambiar al directorio del proyecto
cd /d "%~dp0"

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo Entorno virtual activado
)

REM Obtener el periodo actual (formato YYYYMM)
for /f "tokens=1-3 delims=/" %%a in ('echo %date%') do (
    set dia=%%a
    set mes=%%b
    set anio=%%c
)

REM Asegurar que mes tenga 2 dígitos
if %mes% LSS 10 set mes=0%mes%

REM Construir periodo (YYYYMM)
set PERIODO=%anio%%mes%

echo.
echo ====================================================================
echo Sincronizando TODOS los centros DDH para periodo: %PERIODO%
echo ====================================================================
echo.

REM Ejecutar sincronización masiva DDH para el mes actual
REM Nota: --todos-ddh sincroniza automáticamente los 19 centros de costo DDH
python manage.py sincronizar_abastecimientos %PERIODO% --todos-ddh --familia PDD >> logs\sync_abastecimientos_%PERIODO%.log 2>&1

REM Verificar código de salida
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Sincronizacion del mes actual completada exitosamente
) else (
    echo [%date% %time%] ERROR: Sincronizacion del mes actual fallo con codigo %ERRORLEVEL%
)

echo.
echo ====================================================================
echo Sincronizando mes anterior (datos rezagados)
echo ====================================================================
echo.

REM También sincronizar mes anterior por si hay datos rezagados
set /a mes_anterior=%mes%-1
if %mes_anterior% LSS 1 (
    set mes_anterior=12
    set /a anio_anterior=%anio%-1
) else (
    set anio_anterior=%anio%
)

REM Asegurar formato de 2 dígitos
if %mes_anterior% LSS 10 set mes_anterior=0%mes_anterior%
set PERIODO_ANTERIOR=%anio_anterior%%mes_anterior%

echo Sincronizando periodo anterior: %PERIODO_ANTERIOR%
python manage.py sincronizar_abastecimientos %PERIODO_ANTERIOR% --todos-ddh --familia PDD >> logs\sync_abastecimientos_%PERIODO_ANTERIOR%.log 2>&1

if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Sincronizacion del mes anterior completada exitosamente
) else (
    echo [%date% %time%] ERROR: Sincronizacion del mes anterior fallo con codigo %ERRORLEVEL%
)

echo.
echo [%date% %time%] Proceso de sincronizacion diaria finalizado
echo Logs guardados en: logs\sync_abastecimientos_*.log
echo ====================================================================
