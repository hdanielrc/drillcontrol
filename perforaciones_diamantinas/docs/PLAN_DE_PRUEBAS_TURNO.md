# PLAN DE PRUEBAS QA/QC: Módulo "Crear Turno Completo"
**Fecha:** 17/02/2026  
**Responsable:** QA/QC Analyst  
**Objetivo:** Validar la integridad de datos, carga y persistencia en la creación de reportes de turno (Parte Diario).

---

## 1. PRE-REQUISITOS
Antes de iniciar, asegurarse de tener en la base de datos:
- [ ] Un **Contrato** Activo.
- [ ] Una **Máquina** asociada a dicho contrato.
- [ ] Al menos un **Sondaje** activo para ese contrato.
- [ ] **Trabajadores** (Perforistas y Ayudantes) registrados.
- [ ] Catálogos cargados: **Tipos de Turno**, **Actividades**, **Complementos**, **Aditivos**.

---

## 2. RUTA DE PRUEBA: ESCENARIO "HAPPY PATH" (Flujo Normal)
**Objetivo:** Verificar que un reporte estándar se guarda correctamente en todas las tablas relacionadas.

### Paso 1: Cabecera del Turno
1.  Ingresar al módulo "Crear Turno Completo".
2.  **Fecha:** Seleccionar la fecha de ayer (operación real).
3.  **Turno:** Seleccionar "DÍA" (o equivalente).
4.  **Máquina:** Seleccionar una máquina (ej. *M-001*). *Validar que se filtren los sondajes de su contrato*.
5.  **Sondaje:** Seleccionar uno o más sondajes (ej. *S-105*).

### Paso 2: Personal (Cuadrilla)
1.  Agregar **Perforista**: Seleccionar trabajador, cargo "Perforista".
2.  Agregar **Ayudante**: Seleccionar trabajador, cargo "Ayudante".
3.  *Validación Visual:* Verificar que no permita duplicar el mismo trabajador en el mismo turno.

### Paso 3: Corridas de Perforación (Producción)
1.  Ingresar corrida 1:
    - **Desde:** 100.00
    - **Hasta:** 103.00
    - **Recuperación:** 3.00 (100%)
    - **Tipo:** HQ
2.  Ingresar corrida 2:
    - **Desde:** 103.00
    - **Hasta:** 104.50
    - **Recuperación:** 1.40 (mermado)
3.  *Validación Lógica:* El sistema debe calcular automáticamente el total perforado (4.50m).

### Paso 4: Distribución de Horas (Actividades)
**Importante:** La suma debe dar la duración del turno (ej. 12 horas).
1.  **07:00 - 08:00:** Charla de Seguridad (1h).
2.  **08:00 - 12:00:** Perforación (4h).
3.  **12:00 - 13:00:** Almuerzo (1h).
4.  **13:00 - 19:00:** Perforación (6h).
5.  *Validación:* Verificar que el script de suma de horas no muestre error.

### Paso 5: Consumibles
1.  **Aditivos:** Agregar "Bentonita", Cantidad "2", Unidad "Sacos".
2.  **Herramientas (Complementos):** Agregar "Broca HQ", Serie "12345", Metros Inicial "0", Metros Final "4.5".

### Paso 6: Guardado
1.  Clic en "Guardar Turno".
2.  Esperar mensaje de éxito: *"Turno creado correctamente"*.

---

## 3. MATRIZ DE VALIDACIÓN DE ERRORES (Casos Borde)

| ID | Prueba | Acción | Resultado Esperado | Pasa/No Pasa |
|----|--------|--------|--------------------|--------------|
| **E-01** | **Fecha Futura** | Intentar guardar un turno con fecha de mañana. | Alerta: "No se pueden registrar turnos futuros". | |
| **E-02** | **Sondaje Cruzado** | Intentar seleccionar un sondaje de otro contrato (si es editable). | El sistema debe bloquear o filtrar la lista. | |
| **E-03** | **Campos Vacíos** | Dejar "Máquina" vacío y dar clic en guardar. | Mensaje de error: "Este campo es requerido". | |
| **E-04** | **Caracteres Inválidos** | En "Metros Perforados" escribir "3,5 metros" (texto). | El campo solo debe aceptar números y punto decimal. | |
| **E-05** | **Horas Negativas** | Ingresar Hora Fin menor a Hora Inicio en actividades. | Validación de lógica temporal falla. | |
| **E-06** | **Inyección SQL** | En "Comentarios" escribir `' OR 1=1 --`. | El texto se guarda literal, sin ejecutar código. | |

---

## 4. VERIFICACIÓN EN BASE DE DATOS (Backend)
Usar el script `check_data_debug.py` para validar.

**Tablas a revisar:**
1.  `turnos`: Debe existir 1 registro con la fecha y máquina correctas.
2.  `turno_sondaje`: Debe existir la relación con el/los sondajes.
3.  `turno_avance`: El campo `metros_perforados` debe coincidir con la suma de corridas (4.50m).
4.  `turno_trabajador`: Deben aparecer 2 registros (Perforista y Ayudante).
5.  `turno_consumo` (Aditivos): Debe registrar la salida de almacén (si aplica) o el registro de uso.
6.  `turno_actividad`: La suma de horas debe coincidir.

---

## 5. CRITERIOS DE ACEPTACIÓN
- [ ] El turno se guarda y genera un ID único.
- [ ] Los metros perforados se suman al `Sondaje` (avance acumulado).
- [ ] El stock de aditivos (si hay módulo de inventario) se descuenta.
- [ ] No se generaron errores 500 (Pantalla Blanca) durante el proceso.
