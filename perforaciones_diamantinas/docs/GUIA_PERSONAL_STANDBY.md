# 🔄 GUÍA: SISTEMA DE PERSONAL STANDBY (RESERVA)

## 📋 ¿Qué es el Personal STANDBY?

El **Personal STANDBY** (o personal de reserva) son trabajadores que:

- ✅ **NO tienen guardia fija** (A, B, o C)
- ✅ **Sirven para cubrir ausencias** (faltas, descansos médicos, vacaciones)
- ✅ **Brindan flexibilidad operativa** al tener más personal disponible que máquinas
- ✅ **Están activos en el sistema** pero sin asignación permanente a equipos

---

## 🎯 ¿Por qué necesitamos Personal STANDBY?

### Problema sin STANDBY:
```
❌ Guardias rígidas: A, B, C
❌ Si alguien falta → Queda un equipo incompleto
❌ No hay flexibilidad para cubrir ausencias
❌ Difícil gestionar rotaciones
```

### Solución con STANDBY:
```
✅ Guardias operativas: A, B, C (personal fijo)
✅ Personal STANDBY: Cubre ausencias
✅ Mayor flexibilidad operativa
✅ Mejor gestión de imprevistos
```

---

## 🔧 Implementación Técnica

### 1. Campo en la Base de Datos

Se agregó el campo `es_standby` al modelo `Trabajador`:

```python
es_standby = models.BooleanField(
    default=False,
    verbose_name='Personal STANDBY',
    help_text='Marca este trabajador como personal de reserva para cubrir ausencias'
)
```

### 2. Lógica de Asignación de Guardias

La función `generar_guardias_automaticas()` fue modificada para:

1. **Filtrar trabajadores STANDBY** antes de asignar guardias
2. **Distribuir proporcionalmente** el personal disponible
3. **Formar guardias según disponibilidad real** (1, 2 o 3 guardias)
4. **Limpiar guardias** del personal STANDBY (sin guardia fija)

```python
# Excluir personal STANDBY de guardias fijas
if trabajador.es_standby:
    personal_standby.append(trabajador)
    continue
```

---

## 📝 Cómo Marcar Personal como STANDBY

### Opción 1: Desde el Admin de Django

1. Ir a **Admin → Trabajadores**
2. Buscar al trabajador
3. Marcar checkbox **"Es STANDBY"**
4. Guardar

### Opción 2: Usando el Script de Gestión

```bash
cd perforaciones_diamantinas
python manage.py shell < scripts/marcar_personal_standby.py
```

El script permite:

- ✅ **Listar** todo el personal STANDBY actual
- ✅ **Marcar** trabajadores como STANDBY por DNI
- ✅ **Desmarcar** trabajadores (volver a regular)
- ✅ **Sugerir** candidatos para STANDBY

#### Ejemplo: Marcar trabajadores como STANDBY

Editar el archivo `scripts/marcar_personal_standby.py`:

```python
# Opción 3: Marcar trabajadores específicos como STANDBY
print("3️⃣ Marcando trabajadores como STANDBY...")
dnis_a_marcar = [
    '45678912',  # Juan Pérez (Perforista)
    '78945612',  # María García (Ayudante)
    '32165498',  # Carlos López (Ayudante)
]
marcar_standby_por_dni(dnis_a_marcar, es_standby=True)
```

---

## 🎯 Criterios para Elegir Personal STANDBY

### Buenos Candidatos:

1. **Trabajadores sin máquina asignada permanente**
   - No están vinculados a un equipo específico
   
2. **Personal "flotante" que cubre múltiples frentes**
   - Tienen experiencia con varias máquinas
   
3. **Trabajadores con mayor antigüedad/experiencia**
   - Pueden adaptarse rápidamente a diferentes equipos
   
4. **Excedente según análisis de carga**
   - Si tienes 12 perforistas pero solo 9 máquinas → 3 pueden ser STANDBY

### Ejemplo de Distribución Típica:

```
Contrato con 9 máquinas operativas:
- 9 Perforistas fijos (3 por guardia A, B, C)
- 18 Ayudantes fijos (6 por guardia)
- 3 Perforistas STANDBY (personal de reserva)
- 6 Ayudantes STANDBY (personal de reserva)
-------------------------------------------
Total: 12 Perforistas + 24 Ayudantes
```

---

## 🔄 Flujo Operativo con Personal STANDBY

### Escenario Normal:
```
Guardia A: Perf-1 + Ayud-1 + Ayud-2  → Máquina X
Guardia B: Perf-2 + Ayud-3 + Ayud-4  → Máquina Y
Guardia C: Perf-3 + Ayud-5 + Ayud-6  → Máquina Z
STANDBY: Perf-4, Ayud-7, Ayud-8 (esperando)
```

### Escenario con Ausencia:
```
❌ Ayud-2 (Guardia A) falta por descanso médico

✅ Supervisor asigna Ayud-7 (STANDBY) a cubrir
   → Ayud-7 trabaja en turno de Guardia A ese día
```

### En el Sistema:
- El **TurnoTrabajador** registra la asignación real del día
- El personal STANDBY aparece disponible para asignar
- No interfiere con la proyección de tareo automática

---

## 🖥️ Visualización en el Sistema

### Lista de Trabajadores (Admin):

| Apellidos | Nombres | Cargo | Guardia | Tipo | Estado |
|-----------|---------|-------|---------|------|--------|
| García    | Juan    | Perforista | A | - | ACTIVO |
| López     | María   | Ayudante | A | - | ACTIVO |
| Pérez     | Carlos  | Perforista | B | - | ACTIVO |
| Ramírez   | Luis    | Perforista | - | 🔄 STANDBY | ACTIVO |
| Torres    | Ana     | Ayudante | - | 🔄 STANDBY | ACTIVO |

### Filtros Disponibles:
- Por **Estado** (ACTIVO, CESADO)
- Por **Es STANDBY** (Sí/No)
- Por **Guardia Asignada** (A, B, C, Sin asignar)
- Por **Cargo**
- Por **Contrato**

---

## ⚙️ Proceso de Generación de Guardias

### Antes (Problema):
```
1. Contar TODO el personal activo
2. Intentar formar 3 guardias completas
3. ❌ Error: No hay suficiente para la Guardia C
4. ❌ Falla la asignación
```

### Ahora (Solución):
```
1. Excluir personal STANDBY
2. Contar personal disponible para guardias fijas
3. Calcular cuántas guardias podemos formar
4. ✅ Formar 1, 2 o 3 guardias según disponibilidad
5. ✅ Limpiar guardias del personal STANDBY
6. ✅ Informar composición y advertencias
```

---

## 📊 Ejemplo Real: Contrato XRD12DST-001

### Situación Actual:
```
Personal Activo Total:
- 12 Perforistas
- 24 Ayudantes
- 5 Geólogos
- 3 Mecánicos

Máquinas Operativas: 9

Análisis:
- Necesario por guardia: 3 Perforistas + 6 Ayudantes = 9 personas
- Necesario total (3 guardias): 9 Perforistas + 18 Ayudantes = 27 personas
- Excedente: 3 Perforistas + 6 Ayudantes = 9 personas
```

### Propuesta de Asignación:
```
GUARDIAS FIJAS:
├─ Guardia A: 3 Perforistas + 6 Ayudantes
├─ Guardia B: 3 Perforistas + 6 Ayudantes
└─ Guardia C: 3 Perforistas + 6 Ayudantes

PERSONAL STANDBY (Reserva):
├─ 3 Perforistas STANDBY
└─ 6 Ayudantes STANDBY
```

---

## 🚀 Migración y Actualización

### Aplicar la Migración:

```bash
cd perforaciones_diamantinas
python manage.py migrate drilling
```

Esto creará el campo `es_standby` en la tabla `trabajadores`.

### Valores por Defecto:
- `es_standby = False` para todo el personal existente
- Debes marcar manualmente quién será STANDBY

---

## ✅ Ventajas del Sistema

1. **Mayor Flexibilidad Operativa**
   - Cubrir ausencias sin descomponer equipos

2. **Gestión Realista**
   - Refleja la realidad: No todo el personal trabaja todos los días

3. **Prevención de Errores**
   - No fuerza guardias que no pueden formarse

4. **Adaptabilidad**
   - Se ajusta a la disponibilidad real de personal

5. **Trazabilidad**
   - Claro quién es fijo y quién es reserva

---

## 📞 Soporte y Dudas

Si tienes preguntas sobre el sistema de Personal STANDBY:

1. Revisa esta guía
2. Ejecuta el script de análisis: `scripts/marcar_personal_standby.py`
3. Consulta con el equipo de desarrollo

---

**Última actualización:** Febrero 2026  
**Versión del Sistema:** DrillControl v2.0
