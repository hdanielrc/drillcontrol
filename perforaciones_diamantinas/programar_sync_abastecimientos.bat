@echo off
REM ====================================================================
REM Launcher para ejecutar el script PowerShell de programación
REM Solicita privilegios de administrador automáticamente
REM ====================================================================

echo Ejecutando programacion de sincronizacion automatica...
echo Se requieren privilegios de Administrador
echo.

REM Ejecutar PowerShell como Administrador
powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0programar_sync_abastecimientos.ps1\"' -Verb RunAs"

echo.
echo Si no se abrio ninguna ventana, verifica que PowerShell este habilitado en tu sistema.
pause
