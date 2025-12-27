# GUÍA DE SINCRONIZACIÓN AUTOMÁTICA DE STOCK API

## RESUMEN
Sistema de sincronización automática que consulta las APIs de Vilbragroup para obtener:
- **PDD (Productos Diamantados)**: Stock de herramientas y equipos de perforación
- **ADIT (Aditivos)**: Stock de materiales y aditivos

## ARCHIVOS CREADOS

### 1. sync_stock_diario.py
Script principal que ejecuta la sincronización para todos los contratos:
- Consulta la API de PDD para cada centro de costo
- Consulta la API de ADIT para cada centro de costo
- Genera logs detallados en el directorio `logs/`
- Formato de log: `sync_stock_YYYYMMDD.log`

### 2. programar_sync_stock.bat
Script para programar la tarea en Windows (requiere permisos de administrador):
- Crea una tarea programada que se ejecuta diariamente a las 2:00 AM
- Usa el Python del entorno virtual
- Configura logs automáticos

## EJECUCIÓN MANUAL

Para ejecutar la sincronización manualmente:

```cmd
cd perforaciones_diamantinas
venv\Scripts\python.exe sync_stock_diario.py
```

O desde PowerShell:
```powershell
cd perforaciones_diamantinas
.\venv\Scripts\python.exe sync_stock_diario.py
```

## PROGRAMAR EJECUCIÓN AUTOMÁTICA A LAS 2 AM

### OPCIÓN 1: Usando el script BAT (Recomendado)

1. Clic derecho en `programar_sync_stock.bat`
2. Seleccionar "Ejecutar como administrador"
3. Confirmar cuando pregunte si desea ejecutar ahora para probar

### OPCIÓN 2: Manualmente usando Programador de Tareas

1. Abrir "Programador de tareas" (Task Scheduler)
2. Clic en "Crear tarea básica"
3. Nombre: `DrillControl_Sync_Stock_API`
4. Desencadenador: Diariamente a las 2:00 AM
5. Acción: Iniciar un programa
   - Programa: `C:\Users\PERDLAP140.VILBRAGROUP\Documents\drillcontrol\drillcontrol\perforaciones_diamantinas\venv\Scripts\python.exe`
   - Argumentos: `"C:\Users\PERDLAP140.VILBRAGROUP\Documents\drillcontrol\drillcontrol\perforaciones_diamantinas\sync_stock_diario.py"`
   - Iniciar en: `C:\Users\PERDLAP140.VILBRAGROUP\Documents\drillcontrol\drillcontrol\perforaciones_diamantinas`
6. Configuración adicional (Propiedades de la tarea):
   - Ejecutar con los privilegios más altos
   - Ejecutar tanto si el usuario inicia sesión como si no
   - No detener si se pasa a batería

### OPCIÓN 3: Comando PowerShell (como administrador)

```powershell
$taskName = "DrillControl_Sync_Stock_API"
$pythonPath = "C:\Users\PERDLAP140.VILBRAGROUP\Documents\drillcontrol\drillcontrol\perforaciones_diamantinas\venv\Scripts\python.exe"
$scriptPath = "C:\Users\PERDLAP140.VILBRAGROUP\Documents\drillcontrol\drillcontrol\perforaciones_diamantinas\sync_stock_diario.py"

$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory "C:\Users\PERDLAP140.VILBRAGROUP\Documents\drillcontrol\drillcontrol\perforaciones_diamantinas"
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Sincronizacion diaria de stock desde API Vilbragroup" -Force
```

## VERIFICAR ESTADO DE LA TAREA

```cmd
schtasks /Query /TN "DrillControl_Sync_Stock_API" /FO LIST /V
```

## EJECUTAR MANUALMENTE LA TAREA PROGRAMADA

```cmd
schtasks /Run /TN "DrillControl_Sync_Stock_API"
```

## REVISAR LOGS

Los logs se guardan en: `perforaciones_diamantinas\logs\`

Nombre del archivo: `sync_stock_YYYYMMDD.log`

Ejemplo para ver el log de hoy:
```cmd
cd perforaciones_diamantinas\logs
type sync_stock_20251220.log
```

## DESACTIVAR/ACTIVAR LA TAREA

Desactivar:
```cmd
schtasks /Change /TN "DrillControl_Sync_Stock_API" /DISABLE
```

Activar:
```cmd
schtasks /Change /TN "DrillControl_Sync_Stock_API" /ENABLE
```

## ELIMINAR LA TAREA

```cmd
schtasks /Delete /TN "DrillControl_Sync_Stock_API" /F
```

## QUÉ HACE LA SINCRONIZACIÓN

1. **Se conecta a la base de datos** para obtener todos los contratos activos
2. **Por cada contrato:**
   - Consulta la API de PDD (Productos Diamantados)
   - Consulta la API de ADIT (Aditivos)
   - Registra la cantidad de artículos obtenidos
3. **Genera un log completo** con:
   - Fecha y hora de ejecución
   - Contratos procesados
   - Cantidad de artículos por tipo (PDD/ADIT)
   - Errores si los hay
4. **Resumen final** con estadísticas de la sincronización

## PRÓXIMOS PASOS

Cuando termines de llenar los Excel con los contratos, la sincronización comenzará a obtener datos reales de las APIs para cada centro de costo configurado.

Los datos obtenidos están disponibles para ser procesados o guardados en la base de datos según sea necesario.

## EJEMPLO DE LOG

```
2025-12-20 02:00:01,123 - INFO - ================================================================================
2025-12-20 02:00:01,123 - INFO - INICIO DE SINCRONIZACIÓN DIARIA DE STOCK
2025-12-20 02:00:01,123 - INFO - Fecha y hora: 2025-12-20 02:00:01
2025-12-20 02:00:01,123 - INFO - ================================================================================
2025-12-20 02:00:02,456 - INFO - ================================================================================
2025-12-20 02:00:02,456 - INFO - Procesando contrato: CONDESTABLE
2025-12-20 02:00:02,456 - INFO - Centro de Costo: 000003
2025-12-20 02:00:02,456 - INFO - ================================================================================
2025-12-20 02:00:03,789 - INFO - ✅ CONDESTABLE: 145 artículos PDD obtenidos
2025-12-20 02:00:05,012 - INFO - ✅ CONDESTABLE: 23 artículos ADIT obtenidos
2025-12-20 02:00:05,234 - INFO - ================================================================================
2025-12-20 02:00:05,234 - INFO - RESUMEN DE SINCRONIZACIÓN
2025-12-20 02:00:05,234 - INFO - ================================================================================
2025-12-20 02:00:05,234 - INFO - PDD exitosos: 1
2025-12-20 02:00:05,234 - INFO - PDD fallidos: 0
2025-12-20 02:00:05,234 - INFO - ADIT exitosos: 1
2025-12-20 02:00:05,234 - INFO - ADIT fallidos: 0
```
