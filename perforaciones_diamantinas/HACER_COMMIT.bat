@echo off
echo ========================================
echo COMMIT DE CAMBIOS
echo ========================================
echo.

cd /d "%~dp0"

echo Agregando archivos...
git add -A

echo.
echo Haciendo commit...
git commit -m "feat: Control de Proyectos + fix calculo metros + config produccion"

echo.
echo Push al repositorio remoto? (S/N)
set /p PUSH=
if /i "%PUSH%"=="S" (
    git push
    echo.
    echo Push completado!
) else (
    echo.
    echo Commit local creado. Usa 'git push' cuando estes listo.
)

echo.
pause
