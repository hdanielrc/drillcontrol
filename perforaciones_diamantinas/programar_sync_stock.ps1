# Script para programar la sincronizacion diaria de stock a las 2 AM
# Ejecutar como administrador

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CONFIGURACION DE TAREA PROGRAMADA" -ForegroundColor Cyan
Write-Host "Sincronizacion de Stock API - 2:00 AM" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Configuracion
$TaskName = "DrillControl_Sync_Stock_API"
$ScriptPath = Join-Path $PSScriptRoot "sync_stock_diario.py"
$WorkingDir = $PSScriptRoot
$LogDir = Join-Path $WorkingDir "logs"

# Crear directorio de logs si no existe
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Write-Host "[OK] Directorio de logs creado: $LogDir" -ForegroundColor Green
}

# Verificar que el script existe
if (-not (Test-Path $ScriptPath)) {
    Write-Host "[ERROR] No se encontro el script $ScriptPath" -ForegroundColor Red
    exit 1
}

# Obtener la ruta de Python (buscar en venv o sistema)
$PythonPath = $null
$VenvPython = Join-Path $WorkingDir "venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonPath = $VenvPython
    Write-Host "[OK] Python encontrado en entorno virtual: $VenvPython" -ForegroundColor Green
} else {
    # Buscar Python en el sistema
    $SystemPython = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($SystemPython) {
        $PythonPath = $SystemPython
        Write-Host "[OK] Python encontrado en sistema: $SystemPython" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] No se encontro Python. Instale Python o active el entorno virtual." -ForegroundColor Red
        exit 1
    }
}

# Eliminar tarea existente si existe
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "[AVISO] Eliminando tarea programada existente..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Crear la accion (ejecutar el script Python)
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "`"$ScriptPath`"" `
    -WorkingDirectory $WorkingDir

# Crear el trigger (diario a las 2 AM)
$Trigger = New-ScheduledTaskTrigger -Daily -At "02:00"

# Configurar para que se ejecute con el usuario actual
$Principal = New-ScheduledTaskPrincipal `
    -UserId "NT AUTHORITY\SYSTEM" `
    -RunLevel Highest

# Configurar ajustes adicionales
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Registrar la tarea
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Description "Sincronizacion diaria de stock de PDD y Aditivos desde API Vilbragroup" `
        -Force | Out-Null
    
    Write-Host ""
    Write-Host "[EXITO] Tarea programada creada exitosamente!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Detalles de la tarea:" -ForegroundColor Cyan
    Write-Host "  - Nombre: $TaskName" -ForegroundColor White
    Write-Host "  - Horario: Todos los dias a las 2:00 AM" -ForegroundColor White
    Write-Host "  - Script: $ScriptPath" -ForegroundColor White
    Write-Host "  - Python: $PythonPath" -ForegroundColor White
    Write-Host "  - Logs: $LogDir" -ForegroundColor White
    Write-Host ""
    
    # Preguntar si desea ejecutar ahora
    $RunNow = Read-Host "Desea ejecutar la sincronizacion ahora para probar? (S/N)"
    if ($RunNow -eq "S" -or $RunNow -eq "s") {
        Write-Host ""
        Write-Host "[EJECUTANDO] Sincronizacion..." -ForegroundColor Yellow
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "[OK] Sincronizacion iniciada. Revise los logs en: $LogDir" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "Para ver el estado de la tarea, use:" -ForegroundColor Cyan
    Write-Host "  Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo" -ForegroundColor White
    Write-Host ""
    Write-Host "Para ejecutar manualmente la tarea:" -ForegroundColor Cyan
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "Para desactivar la tarea:" -ForegroundColor Cyan
    Write-Host "  Disable-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "[ERROR] No se pudo crear la tarea programada: $_" -ForegroundColor Red
    exit 1
}
