# 🤖 Sistema Automático de Horas Extras

## 📋 Descripción General

El sistema ahora **calcula y asigna automáticamente las horas extras a TODOS los trabajadores** de un turno cuando se cumple la condición de metraje mínimo.

## ✅ ¿Cómo Funciona?

### 1. **Asignación Automática**

Cuando se guarda o actualiza el avance de un turno (`TurnoAvance`), el sistema:

1. ✅ Verifica si existe una configuración de horas extras activa para el contrato
2. ✅ Busca primero configuración específica de la máquina
3. ✅ Si no existe, busca configuración general (todas las máquinas)
4. ✅ Valida que el metraje del turno cumpla el mínimo requerido
5. ✅ Verifica las fechas de vigencia de la configuración
6. ✅ **Asigna las horas extras a TODOS los trabajadores del turno**

### 2. **Todos los Trabajadores son Beneficiados**

**SÍ**, cuando se cumple la condición de metraje, **TODOS los trabajadores** asociados al turno reciben horas extras, sin importar su función (Perforista o Ayudante).

### 3. **Actualización Automática**

- Si se actualiza el metraje del turno, las horas extras se **recalculan automáticamente**
- Si el nuevo metraje ya no cumple la condición, las horas extras se **eliminan automáticamente**
- Si se agregan/quitan trabajadores del turno después de calcular horas extras, se debe recalcular manualmente

## 🎯 Ejemplo Práctico

### Configuración:
- **Contrato**: Americana
- **Metraje mínimo**: 35.00 metros
- **Horas extras a otorgar**: 1.00 hora
- **Aplicable a**: Todas las máquinas

### Turno #123:
- **Fecha**: 21/11/2024
- **Máquina**: Sandvik DL411
- **Trabajadores**:
  - Juan Pérez (Perforista) - DNI: 12345678
  - Carlos López (Ayudante) - DNI: 87654321
  - María García (Ayudante) - DNI: 11223344

### Resultado cuando se registran 38.5 metros:

✅ **Juan Pérez**: 1.00 hora extra
✅ **Carlos López**: 1.00 hora extra  
✅ **María García**: 1.00 hora extra

**Total**: 3 trabajadores × 1.00h = 3.00 horas extras otorgadas

## 🔄 ¿Cuándo se Calculan las Horas Extras?

### Automáticamente:
1. ✅ Al crear un turno con avance desde el formulario completo
2. ✅ Al actualizar el metraje de un turno existente
3. ✅ Al guardar/actualizar el registro de `TurnoAvance`

### Manualmente (comando):
```bash
# Recalcular todos los turnos
python manage.py recalcular_horas_extras

# Ver qué cambiaría sin aplicar (simulación)
python manage.py recalcular_horas_extras --dry-run

# Recalcular un contrato específico
python manage.py recalcular_horas_extras --contrato=1

# Recalcular un rango de fechas
python manage.py recalcular_horas_extras --desde=2024-11-01 --hasta=2024-11-30

# Recalcular un turno específico
python manage.py recalcular_horas_extras --turno=123
```

## 📊 Registro de Horas Extras

Cada registro de `TurnoHoraExtra` contiene:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `turno` | Turno asociado | Turno #123 |
| `trabajador` | Trabajador beneficiado | Juan Pérez (DNI: 12345678) |
| `horas_extra` | Cantidad de horas | 1.00 |
| `metros_turno` | Metraje que generó las HE | 38.50m |
| `configuracion_aplicada` | Config usada | Americana: 35m → 1h |
| `observaciones` | Detalle automático | "Generado automáticamente. Metraje: 38.5m >= 35m" |

## 🔍 Validaciones

El sistema valida:

1. ✅ **Configuración activa**: Solo se aplican configuraciones con `activo=True`
2. ✅ **Vigencia**: Respeta `fecha_inicio` y `fecha_fin` de la configuración
3. ✅ **Metraje mínimo**: El avance debe ser >= metros_minimos
4. ✅ **Prioridad**: Configuración específica de máquina > Configuración general
5. ✅ **Trabajadores**: Solo se asignan HE a trabajadores activos del turno

## ⚙️ Configuración

### Crear Configuración de Horas Extras:

1. Ir a `Configuración > Gestionar Horas Extras`
2. Seleccionar el contrato
3. Configurar:
   - **General**: Para todas las máquinas del contrato
   - **Específica**: Para una máquina en particular
4. Definir:
   - Metraje mínimo (ej: 35.00m)
   - Horas extras a otorgar (ej: 1.00h)
   - Activar/desactivar
   - Fechas de vigencia (opcional)

### Prioridad de Aplicación:

```
1. Configuración específica de máquina (si existe y está activa)
   ↓
2. Configuración general del contrato (si existe y está activa)
   ↓
3. Sin horas extras (no aplica ninguna configuración)
```

## 🔄 Recalcular Horas Extras de Turnos Existentes

Si ya tienes turnos registrados antes de activar este sistema, usa el comando:

```bash
# Ver qué se va a hacer (simulación segura)
python manage.py recalcular_horas_extras --dry-run

# Aplicar cambios reales
python manage.py recalcular_horas_extras
```

### Ejemplo de salida:

```
============================================================
Total de turnos a procesar: 150
============================================================

Procesando Turno #123:
  Fecha: 2024-11-15
  Contrato: Americana
  Máquina: Sandvik DL411
  Metros: 38.50m
  Trabajadores: 3
  ✓ Aplica configuración: 35.0m → 1.0h
  ✓ 3 trabajadores recibirán 1.0h extra

Procesando Turno #124:
  Fecha: 2024-11-16
  Contrato: Americana
  Máquina: Atlas Copco U6
  Metros: 28.00m
  Trabajadores: 2
  - No aplica ninguna configuración (metros insuficientes)

============================================================
RESUMEN
============================================================
Turnos procesados: 150
Turnos con horas extras: 89
Trabajadores beneficiados: 267
Total horas extras otorgadas: 267.00h

✓ Recálculo completado exitosamente
```

## 📈 Reportes

Ver las horas extras asignadas:

1. Ir a `Turnos > Horas Extras` (o `Configuración > Reporte Horas Extras`)
2. Filtrar por:
   - Rango de fechas
   - Contrato
   - Trabajador específico
3. Ver:
   - Resumen por trabajador
   - Detalle por turno
4. Exportar a Excel

## ⚠️ Notas Importantes

### ✅ Ventajas del Sistema Automático:
- No hay que registrar horas extras manualmente
- Se aplica la misma regla a todos los trabajadores (equidad)
- Reduce errores humanos
- Auditabilidad completa (se registra la configuración aplicada)

### ⚠️ Consideraciones:
- **Las horas extras se calculan por turno completo**, no por trabajador individual
- Si un trabajador no debería recibir HE, **no lo agregues al turno** o edita manualmente después
- El sistema elimina y recrea las HE al actualizar el metraje
- Las configuraciones pueden tener vigencia temporal (fechas inicio/fin)

### 🔧 Modificaciones Manuales:
Si necesitas ajustar manualmente las horas extras de un trabajador:
1. Ve al admin de Django: `/admin/drilling/turnohoraextra/`
2. Busca el registro del turno y trabajador
3. Edita según necesites

## 🆘 Solución de Problemas

### No se están asignando horas extras automáticamente:

✅ Verifica que:
1. Existe una configuración activa (`activo=True`)
2. El metraje cumple el mínimo requerido
3. La configuración está asignada al contrato correcto
4. Las fechas de vigencia incluyen la fecha del turno
5. Los trabajadores están asociados al turno antes de guardar el avance

### Las horas extras no aparecen en el reporte:

✅ Verifica que:
1. El turno tiene trabajadores asociados
2. El turno tiene avance registrado
3. La configuración estaba activa al momento de guardar
4. No hay errores en los logs del servidor

### Necesito recalcular un turno específico:

```bash
python manage.py recalcular_horas_extras --turno=123
```

## 📞 Soporte

Para problemas o dudas:
1. Revisa los logs del servidor Django
2. Ejecuta el comando con `--dry-run` para ver qué haría
3. Contacta al administrador del sistema
