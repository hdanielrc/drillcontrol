@echo off
REM ====================================================================
REM Launcher para programar la sincronización diaria de Trabajadores
REM Solicita privilegios de administrador automáticamente
REM ====================================================================

echo Programando sincronizacion diaria de Trabajadores (4:00 AM)...
echo Se requieren privilegios de Administrador
echo.

powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0programar_sync_trabajadores.ps1\"' -Verb RunAs"

echo.
echo Si no se abrio ninguna ventana, ejecuta PowerShell como Administrador manualmente.
pause
