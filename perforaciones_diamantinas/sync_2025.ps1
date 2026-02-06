# Script para sincronizar abastecimientos de todo el año 2025
# Se ejecuta sobre todos los centros de costo DDH y familia PDD (Brocas)

$months = 1..12

foreach ($month in $months) {
    # Formatear mes a 2 dígitos (01, 02, etc.)
    $monthStr = $month.ToString("00")
    $periodo = "2025$monthStr"
    
    Write-Host "----------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host "Iniciando sincronización para el periodo: $periodo" -ForegroundColor Yellow
    Write-Host "----------------------------------------------------------------" -ForegroundColor Cyan
    
    # Ejecutar comando de gestión
    python manage.py sincronizar_abastecimientos $periodo --todos-ddh --familia PDD
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Error al sincronizar periodo $periodo" -ForegroundColor Red
    } else {
        Write-Host "✅ Periodo $periodo completado" -ForegroundColor Green
    }
    
    # Pequeña pausa para no saturar
    Start-Sleep -Seconds 2
}

Write-Host "----------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "Sincronización anual 2025 completada." -ForegroundColor Green
