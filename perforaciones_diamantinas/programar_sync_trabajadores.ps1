# ====================================================================
# Script PowerShell para Programar Sincronización Diaria de Trabajadores
# Crea una tarea en Windows Task Scheduler que se ejecuta a las 4:00 AM
# ====================================================================

# Verificar si se ejecuta como Administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ ERROR: Este script requiere privilegios de Administrador" -ForegroundColor Red
    Write-Host "Por favor, ejecuta PowerShell como Administrador y vuelve a ejecutar este script." -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "PROGRAMACIÓN DE SINCRONIZACIÓN DIARIA DE TRABAJADORES" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Ruta del directorio actual (donde está el script)
$projectPath = $PSScriptRoot
$scriptPath = Join-Path $projectPath "sync_trabajadores_diario.bat"

# Verificar que existe el script .bat
if (-not (Test-Path $scriptPath)) {
    Write-Host "❌ ERROR: No se encontró el archivo sync_trabajadores_diario.bat" -ForegroundColor Red
    Write-Host "Ruta buscada: $scriptPath" -ForegroundColor Yellow
    pause
    exit 1
}

# Crear directorio de logs si no existe
$logsPath = Join-Path $projectPath "logs"
if (-not (Test-Path $logsPath)) {
    New-Item -ItemType Directory -Path $logsPath | Out-Null
    Write-Host "✓ Directorio de logs creado: $logsPath" -ForegroundColor Green
}

# Configuración de la tarea programada
$taskName = "DrillControl - Sync Trabajadores Diario"
$taskDescription = "Sincronización automática diaria de trabajadores desde API Vilbra Group a las 4:00 AM"
$taskAction = New-ScheduledTaskAction -Execute $scriptPath -WorkingDirectory $projectPath
$taskTrigger = New-ScheduledTaskTrigger -Daily -At "04:00AM"

# Configurar para que se ejecute incluso si el usuario no está logueado
$taskPrincipal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Configuración adicional
$taskSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -RestartCount 3 `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Verificar si ya existe la tarea
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "⚠️  La tarea '$taskName' ya existe." -ForegroundColor Yellow
    $response = Read-Host "¿Deseas reemplazarla? (S/N)"

    if ($response -eq "S" -or $response -eq "s") {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "✓ Tarea anterior eliminada" -ForegroundColor Green
    } else {
        Write-Host "Operación cancelada por el usuario." -ForegroundColor Yellow
        pause
        exit 0
    }
}

# Registrar la tarea programada
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Description $taskDescription `
        -Action $taskAction `
        -Trigger $taskTrigger `
        -Principal $taskPrincipal `
        -Settings $taskSettings `
        -Force | Out-Null

    Write-Host ""
    Write-Host "=====================================================================" -ForegroundColor Green
    Write-Host "✓ TAREA PROGRAMADA CREADA EXITOSAMENTE" -ForegroundColor Green
    Write-Host "=====================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Nombre de la tarea : $taskName" -ForegroundColor White
    Write-Host "Horario            : Todos los días a las 4:00 AM" -ForegroundColor White
    Write-Host "Script             : $scriptPath" -ForegroundColor White
    Write-Host "Logs               : $logsPath" -ForegroundColor White
    Write-Host ""
    Write-Host "Para administrar la tarea:" -ForegroundColor Cyan
    Write-Host "  1. Abre 'Programador de tareas' (taskschd.msc)" -ForegroundColor Yellow
    Write-Host "  2. Busca '$taskName'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Para ejecutar manualmente:" -ForegroundColor Cyan
    Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Yellow
    Write-Host ""

    # Preguntar si desea ejecutar una prueba inmediata
    Write-Host "¿Deseas ejecutar una prueba ahora? (S/N): " -NoNewline -ForegroundColor Cyan
    $testResponse = Read-Host

    if ($testResponse -eq "S" -or $testResponse -eq "s") {
        Write-Host ""
        Write-Host "Ejecutando tarea de prueba..." -ForegroundColor Yellow
        Start-ScheduledTask -TaskName $taskName
        Start-Sleep -Seconds 3
        Write-Host "✓ Tarea iniciada. Revisa logs\sync_trabajadores_*.log para ver el resultado." -ForegroundColor Green
    }

} catch {
    Write-Host ""
    Write-Host "❌ ERROR al crear la tarea programada:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
pause
