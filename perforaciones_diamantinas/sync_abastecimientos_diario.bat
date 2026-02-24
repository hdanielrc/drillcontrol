@echo off
setlocal enabledelayedexpansion
REM ====================================================================
REM Script de Sincronización Diaria de Abastecimientos - TODOS LOS CONTRATOS
REM Se ejecuta automáticamente a las 5:00 AM mediante Task Scheduler
REM Sincroniza los ultimos 3 meses para TODOS los contratos activos
REM Cubre todas las familias (PDD, ADIT, EPP, IN, etc.)
REM ====================================================================

echo [%date% %time%] Iniciando sincronizacion diaria de abastecimientos...

REM Cambiar al directorio del proyecto
cd /d "%~dp0"

REM Activar entorno virtual si existe
if exist "..\.venv\Scripts\activate.bat" (
    call ..\.venv\Scripts\activate.bat
    echo Entorno virtual activado
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo Entorno virtual activado
)

REM ====================================================================
REM Calcular los ultimos 3 meses usando Python puro (sin dependencias extra)
REM ====================================================================
for /f "delims=" %%i in ('python -c "from datetime import date; d=date.today(); m=d.month; y=d.year; p=[(y if m-i>0 else y-1, (m-i) if m-i>0 else m-i+12) for i in range(2,-1,-1)]; print(' '.join(str(a)+str(b).zfill(2) for a,b in p))"') do set PERIODOS=%%i

if "!PERIODOS!"=="" (
    echo ERROR: No se pudieron calcular los periodos. Verifica que Python este en el PATH.
    exit /b 1
)

echo Periodos a sincronizar: !PERIODOS!

REM ====================================================================
REM Sincronizar cada periodo (todos los contratos activos, todas las familias)
REM ====================================================================
for %%P in (!PERIODOS!) do (
    echo.
    echo ====================================================================
    echo Sincronizando periodo: %%P - TODOS los contratos activos
    echo ====================================================================
    python manage.py sincronizar_abastecimientos %%P --verbose >> logs\sync_abastecimientos_%%P.log 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [%date% %time%] Periodo %%P completado exitosamente
    ) else (
        echo [%date% %time%] ERROR en periodo %%P - codigo !ERRORLEVEL!
    )
)

echo.
echo [%date% %time%] Proceso de sincronizacion diaria finalizado
echo Logs guardados en: logs\sync_abastecimientos_*.log
echo ====================================================================
endlocal
