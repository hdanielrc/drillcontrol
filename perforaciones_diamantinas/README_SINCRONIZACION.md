# Sistema de Sincronización de Inventario API Vilbragroup

## Descripción General

Este sistema sincroniza automáticamente los productos diamantados (PDD) y aditivos de perforación (ADIT) desde las APIs de Vilbragroup hacia la base de datos local. Esto permite:

- ✅ Formularios más rápidos (sin llamadas API en tiempo real)
- ✅ Búsqueda y filtrado local
- ✅ Seguimiento del estado de productos (NUEVO, EN USO, DESCARTADO)
- ✅ Integridad referencial con turnos
- ✅ Trabajo offline

## Modelos Actualizados

### TipoComplemento (Productos Diamantados - PDD)
```python
- nombre: Nombre del producto (desde descripción API)
- categoria: Opcional (BROCA, REAMING_SHELL, etc.)
- descripcion: Opcional
- codigo: Código del producto desde API
- serie: Serie única del producto (ÚNICO en BD)
- estado: NUEVO | EN USO | DESCARTADO
- contrato: FK al contrato propietario
```

### TipoAditivo (Aditivos de Perforación - ADIT)
```python
- nombre: Nombre del aditivo (desde descripción API)
- categoria: Opcional (BENTONITA, POLIMEROS, etc.)
- unidad_medida_default: Opcional
- descripcion: Opcional
- codigo: Código del aditivo desde API
- contrato: FK al contrato propietario
```

## Comandos de Sincronización

### 1. Sincronizar Productos Diamantados (PDD)

```bash
# Sincronización básica (usa centro de costo del contrato)
python manage.py sync_productos_diamantados --contrato-id=1

# Con centro de costo específico
python manage.py sync_productos_diamantados --contrato-id=1 --centro-costo=000003

# Modo dry-run (simular sin cambios)
python manage.py sync_productos_diamantados --contrato-id=1 --dry-run

# Con salida detallada
python manage.py sync_productos_diamantados --contrato-id=1 --verbose
```

**Comportamiento:**
- Usa `serie` como identificador único
- Crea nuevos productos con estado `NUEVO`
- Actualiza nombre y código si cambian en la API
- NO modifica el estado de productos existentes

### 2. Sincronizar Aditivos (ADIT)

```bash
# Sincronización básica
python manage.py sync_aditivos --contrato-id=1

# Con centro de costo específico
python manage.py sync_aditivos --contrato-id=1 --centro-costo=000003

# Modo dry-run
python manage.py sync_aditivos --contrato-id=1 --dry-run --verbose
```

**Comportamiento:**
- Usa `codigo + contrato` como identificador único
- Crea nuevos aditivos o actualiza existentes
- Actualiza nombre si cambia en la API

## Script de Sincronización Rápida

Para sincronizar ambos (PDD y ADIT) en un solo comando:

```bash
python sync_condestable.py
```

Este script:
1. Busca automáticamente el contrato CONDESTABLE
2. Sincroniza PDD
3. Sincroniza ADIT
4. Muestra resumen de resultados

## Flujo de Trabajo Recomendado

### Configuración Inicial

1. **Aplicar migraciones:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Verificar código de centro de costo:**
   ```python
   from drilling.models import Contrato
   contrato = Contrato.objects.get(id=1)
   print(contrato.codigo_centro_costo)  # Debe mostrar: 000003
   ```

3. **Ejecutar sincronización inicial:**
   ```bash
   python sync_condestable.py
   ```

### Sincronización Periódica

Ejecutar manualmente cuando:
- Llegan nuevos productos al almacén
- Hay cambios en el inventario de la API
- Se necesita actualizar la información

**Frecuencia recomendada:** Semanal o cuando sea notificado de nuevos productos

### Gestión de Estados (PDD)

Los productos diamantados tienen 3 estados:

- **NUEVO**: Producto sincronizado, disponible para uso
- **EN USO**: Producto asignado a un turno activo
- **DESCARTADO**: Producto que ya no es utilizable

**Cambios de estado:**
- La sincronización NO modifica estados existentes
- Los estados se actualizan manualmente o desde el módulo de turnos
- Solo productos en estado `NUEVO` aparecen en formularios de turno

## Templates Actualizados

Los formularios de creación de turnos ahora muestran:

### Productos Diamantados (PDD)
- Nombre del producto + Serie en el selector
- Campo de serie es **readonly** (se auto-completa al seleccionar)
- Solo muestra productos con estado `NUEVO` del contrato del usuario

### Aditivos (ADIT)
- Nombre + Código en el selector
- Solo muestra aditivos del contrato del usuario

## Vistas Actualizadas

La vista `crear_turno_completo` filtra automáticamente:

```python
tipos_complemento = TipoComplemento.objects.filter(
    contrato=user_contrato,
    estado='NUEVO'
)

tipos_aditivo = TipoAditivo.objects.filter(
    contrato=user_contrato
)
```

## Solución de Problemas

### Error: "No existe un contrato con ID X"
- Verificar que el contrato existe: `Contrato.objects.filter(id=X).exists()`
- Listar contratos disponibles: `Contrato.objects.values_list('id', 'nombre_contrato')`

### Error: "El contrato no tiene código de centro de costo"
- Asignar código de centro de costo:
  ```python
  contrato = Contrato.objects.get(id=1)
  contrato.codigo_centro_costo = '000003'
  contrato.save()
  ```

### Error: "Error al obtener productos de la API"
- Verificar conectividad a internet
- Verificar token API en `.env`: `VILBRAGROUP_API_TOKEN`
- Probar API manualmente:
  ```python
  from drilling.api_client import get_api_client
  client = get_api_client()
  productos = client.obtener_productos_diamantados('000003')
  print(len(productos))
  ```

### No aparecen productos en el formulario
1. Verificar que la sincronización fue exitosa
2. Verificar que los productos tienen estado `NUEVO`:
   ```python
   from drilling.models import TipoComplemento
   TipoComplemento.objects.filter(contrato_id=1, estado='NUEVO').count()
   ```
3. Verificar que el usuario tiene contrato asignado

## Datos de Ejemplo - CONDESTABLE

Después de sincronizar CONDESTABLE (centro de costo 000003):

- **PDD esperados:** ~258 productos diamantados
- **ADIT esperados:** ~10 aditivos
- **Códigos PDD únicos:** ~28 (múltiples series por código)
- **Series únicas:** 258 (cada producto tiene serie única)

## Próximos Pasos

1. ✅ Aplicar migraciones
2. ✅ Ejecutar sincronización inicial
3. ✅ Probar creación de turno con productos sincronizados
4. 🔄 Configurar sincronización automática (cron/Celery) - Opcional
5. 🔄 Implementar gestión de estados desde UI - Opcional
6. 🔄 Sincronizar otros contratos (AMERICANA, CHUNGAR, etc.)

## Mantenimiento

### Agregar nuevo contrato
1. Obtener código de centro de costo del cliente
2. Asignar al contrato:
   ```python
   contrato = Contrato.objects.get(nombre_contrato='NUEVO CONTRATO')
   contrato.codigo_centro_costo = '000XXX'
   contrato.save()
   ```
3. Ejecutar sincronización:
   ```bash
   python manage.py sync_productos_diamantados --contrato-id=X
   python manage.py sync_aditivos --contrato-id=X
   ```

### Limpiar datos de prueba
```python
from drilling.models import TipoComplemento, TipoAditivo

# Eliminar PDD de un contrato específico
TipoComplemento.objects.filter(contrato_id=1).delete()

# Eliminar ADIT de un contrato específico
TipoAditivo.objects.filter(contrato_id=1).delete()
```

## Notas Técnicas

- Las series son **únicas globalmente** (no solo por contrato)
- Los aditivos usan `codigo + contrato` como clave única
- La sincronización usa transacciones para consistencia
- Los campos `categoria`, `descripcion` y `unidad_medida_default` son opcionales
- La API retorna estructuras: `{"perforistas": [...]}` y `{"articulos": [...]}`
