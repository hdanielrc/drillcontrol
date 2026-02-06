# Guía de Sincronización Automática de Abastecimientos

## Resumen

Sistema de sincronización automática diaria que importa abastecimientos desde la API externa y los registra en el sistema, creando automáticamente el historial de brocas con serie.

---

## 📋 Requisitos Previos

1. **Windows Server** o **Windows 10/11**
2. **PowerShell** habilitado
3. **Privilegios de Administrador**
4. **Proyecto DrillControl** instalado y funcionando
5. **Token de API** configurado en `settings.py`

---

## 🚀 Instalación (Una sola vez)

### Opción 1: Instalación Automática (Recomendada)

1. **Ejecutar el script de programación:**
   ```
   Doble clic en: programar_sync_abastecimientos.bat
   ```

2. **Aceptar permisos de Administrador** cuando se solicite

3. **Confirmar la programación** cuando aparezca el prompt

4. **Opcionalmente, ejecutar prueba inmediata**

✅ ¡Listo! La tarea se ejecutará automáticamente todos los días a las 4:00 AM.

---

### Opción 2: Instalación Manual (PowerShell)

1. Abrir **PowerShell como Administrador**

2. Navegar al directorio del proyecto:
   ```powershell
   cd "C:\Users\danie\OneDrive\Escritorio\drillcontrol\perforaciones_diamantinas"
   ```

3. Ejecutar el script de programación:
   ```powershell
   .\programar_sync_abastecimientos.ps1
   ```

---

## 📅 Funcionamiento

### Horario de Ejecución
- **Hora:** 4:00 AM todos los días
- **Duración estimada:** 2-5 minutos
- **Reintentos:** 3 intentos con intervalo de 5 minutos

### Datos Sincronizados
- ✅ **Mes actual:** Todos los abastecimientos del periodo en curso
- ✅ **Mes anterior:** Datos rezagados o correcciones

### Familias Sincronizadas
- **PDD (Productos Diamantados):** Brocas con serie individual
- Opcional: ADIT (Aditivos)

---

## 📊 Logs y Monitoreo

### Ubicación de Logs
```
perforaciones_diamantinas/logs/sync_abastecimientos_YYYYMM.log
```

### Ejemplo de ubicación:
```
logs/sync_abastecimientos_202602.log  (Febrero 2026)
logs/sync_abastecimientos_202601.log  (Enero 2026)
```

### Ver logs recientes:
```powershell
# PowerShell
Get-Content logs\sync_abastecimientos_202602.log -Tail 50

# CMD
type logs\sync_abastecimientos_202602.log
```

---

## 🛠️ Administración de la Tarea

### Ver Estado de la Tarea

**Opción 1: Interfaz Gráfica**
1. Presionar `Win + R`
2. Escribir: `taskschd.msc`
3. Buscar: `DrillControl - Sync Abastecimientos Diario`

**Opción 2: PowerShell**
```powershell
Get-ScheduledTask -TaskName "DrillControl - Sync Abastecimientos Diario"
```

### Ejecutar Manualmente (Prueba)

**PowerShell:**
```powershell
Start-ScheduledTask -TaskName "DrillControl - Sync Abastecimientos Diario"
```

**CMD:**
```cmd
schtasks /run /tn "DrillControl - Sync Abastecimientos Diario"
```

### Deshabilitar Temporalmente

**PowerShell:**
```powershell
Disable-ScheduledTask -TaskName "DrillControl - Sync Abastecimientos Diario"
```

**CMD:**
```cmd
schtasks /change /tn "DrillControl - Sync Abastecimientos Diario" /disable
```

### Habilitar Nuevamente

**PowerShell:**
```powershell
Enable-ScheduledTask -TaskName "DrillControl - Sync Abastecimientos Diario"
```

**CMD:**
```cmd
schtasks /change /tn "DrillControl - Sync Abastecimientos Diario" /enable
```

### Eliminar Tarea

**PowerShell:**
```powershell
Unregister-ScheduledTask -TaskName "DrillControl - Sync Abastecimientos Diario" -Confirm:$false
```

**CMD:**
```cmd
schtasks /delete /tn "DrillControl - Sync Abastecimientos Diario" /f
```

---

## 🔧 Ejecución Manual (Sin Tarea Programada)

### Sincronizar Periodo Específico

```bash
# Sincronizar Febrero 2026 (solo brocas)
python manage.py sincronizar_abastecimientos 202602 --familia PDD

# Sincronizar Enero 2026 (todas las familias)
python manage.py sincronizar_abastecimientos 202601

# Ver detalles completos
python manage.py sincronizar_abastecimientos 202602 --verbose
```

### Ejecutar Script BAT Directamente

```cmd
cd perforaciones_diamantinas
sync_abastecimientos_diario.bat
```

---

## 📧 Notificaciones (Configuración Futura)

Para recibir emails con el resultado de cada sincronización:

1. Modificar el script `sync_abastecimientos_diario.bat`
2. Agregar comando de envío de email al final
3. Usar utilidad como `blat.exe` o script PowerShell

Ejemplo con PowerShell:
```powershell
Send-MailMessage -From "sistema@empresa.com" `
    -To "admin@empresa.com" `
    -Subject "Sincronización Abastecimientos Completada" `
    -Body (Get-Content logs\sync_abastecimientos_202602.log -Raw) `
    -SmtpServer "smtp.empresa.com"
```

---

## 🐛 Solución de Problemas

### Problema: La tarea no se ejecuta

**Verificar:**
1. ✅ Estado de la tarea en Task Scheduler
2. ✅ Usuario tiene permisos (debe ejecutarse como SYSTEM)
3. ✅ Ruta del script es correcta
4. ✅ Python está en el PATH del sistema

### Problema: Error de conexión a API

**Verificar:**
1. ✅ Token configurado en `settings.py`
2. ✅ Centro de costo configurado correctamente
3. ✅ Servidor tiene acceso a internet
4. ✅ Firewall permite conexiones HTTPS

**Ver logs:**
```bash
type logs\sync_abastecimientos_202602.log
```

### Problema: No se crean registros en HistorialBroca

**Verificar:**
1. ✅ Artículos tienen familia `PDD`
2. ✅ Campo `serie` no es nulo
3. ✅ Contratos existen en la base de datos
4. ✅ TipoComplemento se crea automáticamente

---

## 📈 Métricas y Estadísticas

### Dashboard Web
Acceder a: `http://tu-servidor/abastecimientos/`

Visualizar:
- 📊 Total de abastecimientos sincronizados
- 🔧 Brocas con historial creado
- 💰 Valor total de abastecimientos
- 📅 Últimas sincronizaciones

### API de Estadísticas
```bash
# Ver resumen de abastecimientos
python manage.py shell

>>> from drilling.utils.abastecimiento_service import abastecimiento_service
>>> resumen = abastecimiento_service.obtener_resumen_abastecimientos(
...     contrato_id=1,
...     familia='PDD'
... )
>>> print(resumen)
```

---

## 🔐 Seguridad

### Permisos Recomendados

- **Script .bat:** Solo lectura para usuarios estándar
- **Logs:** Carpeta con permisos de escritura
- **Token API:** Solo en `settings.py` (nunca en código)

### Backup

Realizar backup periódico de:
- ✅ Base de datos PostgreSQL
- ✅ Logs de sincronización
- ✅ Archivos de configuración

---

## 📞 Soporte

Para problemas o consultas:
1. Revisar logs en `logs/sync_abastecimientos_*.log`
2. Ejecutar con `--verbose` para más detalles
3. Contactar al equipo de desarrollo

---

## 🎯 Próximas Mejoras

- [ ] Notificaciones por email automáticas
- [ ] Dashboard de monitoreo en tiempo real
- [ ] Alertas si la sincronización falla
- [ ] Sincronización incremental (solo cambios)
- [ ] Integración con API de consumidos

---

**Última actualización:** Febrero 2026
**Versión:** 1.0
