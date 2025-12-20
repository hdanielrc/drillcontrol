@echo off
REM Script para programar la sincronizacion diaria de stock a las 2 AM

echo ========================================
echo CONFIGURACION DE TAREA PROGRAMADA
echo Sincronizacion de Stock API - 2:00 AM
echo ========================================
echo.

set TASK_NAME=DrillControl_Sync_Stock_API
set SCRIPT_PATH=%~dp0sync_stock_diario.py
set PYTHON_PATH=%~dp0venv\Scripts\python.exe

REM Verificar que existe Python en el venv
if not exist "%PYTHON_PATH%" (
    echo [ERROR] No se encontro Python en el entorno virtual
    echo Buscado en: %PYTHON_PATH%
    pause
    exit /b 1
)

REM Verificar que existe el script
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] No se encontro el script sync_stock_diario.py
    pause
    exit /b 1
)

echo [OK] Python encontrado: %PYTHON_PATH%
echo [OK] Script encontrado: %SCRIPT_PATH%
echo.

REM Eliminar tarea existente si existe
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [AVISO] Eliminando tarea programada existente...
    schtasks /Delete /TN "%TASK_NAME%" /F >nul
)

REM Crear la tarea programada
echo [CREANDO] Programando tarea para las 2:00 AM diariamente...
schtasks /Create /TN "%TASK_NAME%" /TR "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /SC DAILY /ST 02:00 /F /RL HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo [EXITO] Tarea programada creada!
    echo ========================================
    echo.
    echo Detalles:
    echo   - Nombre: %TASK_NAME%
    echo   - Horario: Diario a las 2:00 AM
    echo   - Script: %SCRIPT_PATH%
    echo   - Python: %PYTHON_PATH%
    echo.
    echo Para ejecutar manualmente:
    echo   schtasks /Run /TN "%TASK_NAME%"
    echo.
    echo Para ver el estado:
    echo   schtasks /Query /TN "%TASK_NAME%"
    echo.
    echo Para desactivar:
    echo   schtasks /Change /TN "%TASK_NAME%" /DISABLE
    echo.
    
    REM Preguntar si desea ejecutar ahora
    set /p EJECUTAR="Desea ejecutar la sincronizacion ahora? (S/N): "
    if /i "%EJECUTAR%"=="S" (
        echo.
        echo [EJECUTANDO] Iniciando sincronizacion...
        schtasks /Run /TN "%TASK_NAME%"
        echo.
        echo [OK] Revise los logs en: %~dp0logs\
    )
) else (
    echo.
    echo [ERROR] No se pudo crear la tarea programada
    echo Intente ejecutar este script como Administrador
)

echo.
pause
