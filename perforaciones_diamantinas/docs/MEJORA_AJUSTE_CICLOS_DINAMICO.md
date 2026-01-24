# MEJORA: AJUSTE DINÁMICO DE CICLOS DE TRABAJO
## Sistema Inteligente de Proyección Basado en Días Reales

---

## 🎯 PROBLEMA A RESOLVER

### Caso Real:
Un trabajador con régimen **14x7**:
- **Proyección**: Debe ir a descanso el 10 de enero
- **Realidad**: Se queda 4 días más apoyando (hasta el 14 de enero)
- **Problema**: La proyección de febrero NO se ajusta, queda desfasada permanentemente

### Limitación Actual:
```python
# Sistema actual (estático):
dias_transcurridos = (fecha_consulta - fecha_inicio_ciclo).days
posicion_ciclo = dias_transcurridos % ciclo_total
```
- Calcula desde una `fecha_inicio_ciclo` fija
- NO considera días reales trabajados
- Requiere ajuste manual de `fecha_inicio_ciclo`

---

## 📊 BENCHMARKING: MEJORES PRÁCTICAS DEL MERCADO

### Software Analizado:
1. **Deputy** (385,000+ usuarios)
2. **When I Work** (Millones de usuarios)
3. **Replicon/Deltek** (Industria minera/petrolera)

### Características Identificadas:

#### ✅ **1. Ajuste Automático de Ciclos**
- Cuando se registra una extensión/reducción, recalcula automáticamente
- Mantiene "balance de días" trabajados vs proyectados

#### ✅ **2. Rolling Schedule (Horario Rotativo Dinámico)**
- Punto de referencia "móvil" que se actualiza con la realidad
- Cada mes toma en cuenta anomalías del mes anterior

#### ✅ **3. Balance Tracking**
```
Ejemplo:
- Proyectado: 14 días trabajo
- Real: 18 días trabajo (+4 extra)
- Sistema ajusta: Próximo descanso será 11 días (7 + 4)
```

#### ✅ **4. Tipos de Ajuste**
- **Compensación adelantada**: Próximo descanso más largo
- **Compensación diferida**: Próximo ciclo empieza antes
- **Sin compensación**: Trabajador pierde/gana días (configurable)

---

## 🔧 SOLUCIÓN PROPUESTA: 3 NIVELES

### **NIVEL 1: QUICK FIX (2-3 horas)** ⭐ RECOMENDADO PARA IMPLEMENTAR YA

#### Funcionalidad:
- Botón "Ajustar Ciclo Automáticamente" en interfaz de tareo
- Cuando supervisor confirma cambios del mes, sistema recalcula `fecha_inicio_ciclo`

#### Implementación:

```python
# drilling/utils/tareo_service.py

@staticmethod
def ajustar_ciclo_por_mes_real(trabajador, anio, mes):
    """
    Ajusta la fecha_inicio_ciclo basándose en días realmente trabajados del mes.
    
    Casos de uso:
    - Trabajador extendió su turno (más días de trabajo)
    - Trabajador se fue antes (menos días de trabajo)
    - Cambios por emergencias, vacaciones, etc.
    """
    from datetime import date, timedelta
    from calendar import monthrange
    
    # Obtener primer y último día del mes
    primer_dia = date(anio, mes, 1)
    num_dias = monthrange(anio, mes)[1]
    ultimo_dia = date(anio, mes, num_dias)
    
    # Obtener régimen
    regimen = trabajador.regimen_laboral
    if regimen not in TareoService.REGIMEN_CONFIG:
        return None
    
    dias_trabajo_ciclo, dias_descanso_ciclo = TareoService.REGIMEN_CONFIG[regimen]
    ciclo_total = dias_trabajo_ciclo + dias_descanso_ciclo
    
    # Contar días REALMENTE trabajados en el mes
    dias_reales_trabajados = AsistenciaDiaria.objects.filter(
        empleado=trabajador,
        fecha__gte=primer_dia,
        fecha__lte=ultimo_dia,
        estado='TRABAJO'
    ).count()
    
    # Contar días que DEBÍAN ser trabajo según proyección
    dias_proyectados_trabajo = 0
    fecha_actual = primer_dia
    while fecha_actual <= ultimo_dia:
        estado_proyectado = TareoService.calcular_estado_dia(trabajador, fecha_actual)
        if estado_proyectado == 'TRABAJO':
            dias_proyectados_trabajo += 1
        fecha_actual += timedelta(days=1)
    
    # Calcular diferencia
    diferencia = dias_reales_trabajados - dias_proyectados_trabajo
    
    if diferencia == 0:
        logger.info(f"Trabajador {trabajador.id}: No hay diferencia, ciclo correcto")
        return {
            'ajustado': False,
            'diferencia': 0,
            'mensaje': 'Ciclo está correctamente alineado'
        }
    
    # Ajustar fecha_inicio_ciclo
    # Si trabajó días extra, "adelantar" el ciclo (restar días a fecha_inicio)
    # Si trabajó menos, "atrasar" el ciclo (sumar días a fecha_inicio)
    nueva_fecha_inicio = trabajador.fecha_inicio_ciclo - timedelta(days=diferencia)
    
    fecha_inicio_anterior = trabajador.fecha_inicio_ciclo
    trabajador.fecha_inicio_ciclo = nueva_fecha_inicio
    trabajador.save()
    
    logger.info(
        f"Trabajador {trabajador.id}: Ajuste de ciclo. "
        f"Diferencia: {diferencia} días. "
        f"Fecha inicio: {fecha_inicio_anterior} → {nueva_fecha_inicio}"
    )
    
    return {
        'ajustado': True,
        'diferencia': diferencia,
        'fecha_anterior': fecha_inicio_anterior,
        'fecha_nueva': nueva_fecha_inicio,
        'mensaje': f"Ciclo ajustado por {abs(diferencia)} días {'extra' if diferencia > 0 else 'menos'}"
    }
```

#### API Endpoint:

```python
# drilling/views_tareo_v2.py

@login_required
@require_http_methods(["POST"])
def api_ajustar_ciclo_trabajador(request):
    """
    Endpoint para ajustar el ciclo de un trabajador basándose en el mes real.
    """
    try:
        trabajador_id = request.POST.get('trabajador_id')
        mes = int(request.POST.get('mes'))
        anio = int(request.POST.get('anio'))
        
        trabajador = Trabajador.objects.get(id=trabajador_id)
        
        # Verificar permisos (solo manager o admin)
        if not (request.user.is_staff or request.user.role == 'manager'):
            return JsonResponse({'error': 'Permisos insuficientes'}, status=403)
        
        # Ajustar ciclo
        resultado = TareoService.ajustar_ciclo_por_mes_real(trabajador, anio, mes)
        
        if resultado['ajustado']:
            return JsonResponse({
                'success': True,
                'mensaje': resultado['mensaje'],
                'diferencia': resultado['diferencia'],
                'fecha_nueva': resultado['fecha_nueva'].strftime('%Y-%m-%d')
            })
        else:
            return JsonResponse({
                'success': True,
                'mensaje': resultado['mensaje']
            })
            
    except Trabajador.DoesNotExist:
        return JsonResponse({'error': 'Trabajador no encontrado'}, status=404)
    except Exception as e:
        logger.error(f"Error ajustando ciclo: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
```

#### URL:
```python
# drilling/urls.py
path('tareo/v2/api/ajustar-ciclo/', api_ajustar_ciclo_trabajador, name='api_ajustar_ciclo'),
```

#### UI (Botón en Template):

```html
<!-- drilling/templates/drilling/tareo/tareo_v2_mensual.html -->

<!-- Agregar en la sección de acciones -->
<div class="mb-3">
    <button type="button" class="btn btn-warning" onclick="ajustarCiclosAutomaticamente()">
        <i class="fas fa-sync-alt me-2"></i>
        Ajustar Ciclos según Mes Real
    </button>
    <small class="text-muted ms-2">
        Actualiza automáticamente los ciclos de los trabajadores basándose en días realmente trabajados
    </small>
</div>

<script>
function ajustarCiclosAutomaticamente() {
    if (!confirm('¿Desea ajustar los ciclos de todos los trabajadores basándose en el tareo real de este mes?\n\nEsto actualizará la proyección del próximo mes.')) {
        return;
    }
    
    const trabajadores = document.querySelectorAll('[data-trabajador-id]');
    let procesados = 0;
    let ajustados = 0;
    
    trabajadores.forEach(elem => {
        const trabajadorId = elem.dataset.trabajadorId;
        
        fetch('{% url "api_ajustar_ciclo" %}', {
            method: 'POST',
            headers: {
                'X-CSRFToken': '{{ csrf_token }}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `trabajador_id=${trabajadorId}&mes={{ mes }}&anio={{ anio }}`
        })
        .then(response => response.json())
        .then(data => {
            procesados++;
            if (data.ajustado) {
                ajustados++;
            }
            
            if (procesados === trabajadores.length) {
                alert(`Proceso completado:\n${ajustados} ciclos ajustados\n${procesados - ajustados} sin cambios`);
                location.reload();
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    });
}
</script>
```

---

### **NIVEL 2: PROYECCIÓN HÍBRIDA (1-2 días)** 🚀 SOLUCIÓN INTERMEDIA

#### Concepto:
- Combina proyección matemática + historial real
- Cada proyección considera los últimos 3 meses de historia

#### Algoritmo:

```python
@staticmethod
def calcular_estado_dia_hibrido(trabajador, fecha_consulta):
    """
    Calcula estado del día considerando:
    1. Régimen laboral matemático
    2. Patrón real de los últimos 90 días
    3. Ajuste dinámico si hay desfase
    """
    # Paso 1: Cálculo tradicional
    estado_matematico = TareoService.calcular_estado_dia(trabajador, fecha_consulta)
    
    # Paso 2: Verificar si hay historia reciente
    fecha_limite = fecha_consulta - timedelta(days=90)
    
    asistencias_recientes = AsistenciaDiaria.objects.filter(
        empleado=trabajador,
        fecha__gte=fecha_limite,
        fecha__lt=fecha_consulta,
        es_proyeccion=False  # Solo contar correcciones reales
    ).order_by('-fecha')[:30]  # Últimos 30 días reales
    
    if asistencias_recientes.count() < 10:
        # Poca historia, usar cálculo matemático
        return estado_matematico
    
    # Paso 3: Analizar patrón real
    dias_reales_trabajo = asistencias_recientes.filter(estado='TRABAJO').count()
    dias_reales_descanso = asistencias_recientes.filter(estado='DESCANSO').count()
    total_dias_reales = dias_reales_trabajo + dias_reales_descanso
    
    if total_dias_reales == 0:
        return estado_matematico
    
    # Calcular ratio real vs esperado
    regimen = trabajador.regimen_laboral
    dias_trabajo_ciclo, dias_descanso_ciclo = TareoService.REGIMEN_CONFIG.get(regimen, (14, 7))
    ciclo_total = dias_trabajo_ciclo + dias_descanso_ciclo
    
    ratio_esperado = dias_trabajo_ciclo / ciclo_total
    ratio_real = dias_reales_trabajo / total_dias_reales
    
    # Si el ratio real difiere significativamente (>10%), hay desfase
    diferencia_ratio = abs(ratio_real - ratio_esperado)
    
    if diferencia_ratio > 0.10:  # 10% de tolerancia
        # Hay desfase, usar patrón real como guía
        logger.warning(
            f"Trabajador {trabajador.id}: Desfase detectado. "
            f"Esperado: {ratio_esperado:.2%}, Real: {ratio_real:.2%}"
        )
        
        # Proyectar basándose en último día real
        ultimo_dia_real = asistencias_recientes.first()
        dias_desde_ultimo = (fecha_consulta - ultimo_dia_real.fecha).days
        
        # Contar días de trabajo consecutivos recientes
        dias_consecutivos_trabajo = 0
        for asistencia in asistencias_recientes:
            if asistencia.estado == 'TRABAJO':
                dias_consecutivos_trabajo += 1
            else:
                break
        
        # Si lleva muchos días trabajando, probablemente le toca descanso pronto
        if dias_consecutivos_trabajo >= dias_trabajo_ciclo:
            return 'DESCANSO'
        else:
            return 'TRABAJO'
    
    # No hay desfase significativo, usar cálculo matemático
    return estado_matematico
```

---

### **NIVEL 3: SISTEMA COMPLETO DE BALANCE (3-5 días)** 🎯 SOLUCIÓN DEFINITIVA

#### Nuevo Modelo:

```python
# drilling/models.py

class BalanceCicloTrabajador(models.Model):
    """
    Tracking de balance de días trabajados vs proyectados.
    Permite compensaciones y ajustes automáticos.
    """
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, related_name='balances_ciclo')
    fecha_inicio_periodo = models.DateField(verbose_name='Inicio del período')
    fecha_fin_periodo = models.DateField(verbose_name='Fin del período')
    
    # Proyección
    dias_trabajo_proyectados = models.IntegerField(default=0)
    dias_descanso_proyectados = models.IntegerField(default=0)
    
    # Realidad
    dias_trabajo_reales = models.IntegerField(default=0)
    dias_descanso_reales = models.IntegerField(default=0)
    
    # Balance
    diferencia_trabajo = models.IntegerField(
        default=0,
        help_text='Días de trabajo extra (+) o menos (-)'
    )
    diferencia_descanso = models.IntegerField(
        default=0,
        help_text='Días de descanso extra (+) o menos (-)'
    )
    
    # Compensación
    compensacion_aplicada = models.BooleanField(default=False)
    tipo_compensacion = models.CharField(
        max_length=20,
        choices=[
            ('NINGUNA', 'Sin compensación'),
            ('ADELANTAR_DESCANSO', 'Adelantar descanso'),
            ('EXTENDER_DESCANSO', 'Extender próximo descanso'),
            ('AJUSTAR_CICLO', 'Ajustar ciclo completo'),
        ],
        default='NINGUNA'
    )
    
    fecha_compensacion = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'balance_ciclo_trabajador'
        verbose_name = 'Balance de Ciclo'
        verbose_name_plural = 'Balances de Ciclo'
        ordering = ['-fecha_inicio_periodo']
        indexes = [
            models.Index(fields=['trabajador', '-fecha_inicio_periodo']),
            models.Index(fields=['compensacion_aplicada', 'fecha_compensacion']),
        ]
    
    def __str__(self):
        return f"{self.trabajador} - {self.fecha_inicio_periodo} ({self.diferencia_trabajo:+d} días)"
    
    def calcular_balance(self):
        """Calcula el balance comparando proyección vs realidad"""
        self.diferencia_trabajo = self.dias_trabajo_reales - self.dias_trabajo_proyectados
        self.diferencia_descanso = self.dias_descanso_reales - self.dias_descanso_proyectados
        self.save()
        return self.diferencia_trabajo
    
    def requiere_compensacion(self):
        """Determina si el balance requiere compensación (umbral: ±2 días)"""
        return abs(self.diferencia_trabajo) >= 2
```

#### Servicio de Balance:

```python
# drilling/utils/balance_service.py

class BalanceService:
    
    @staticmethod
    def registrar_balance_mensual(trabajador, anio, mes):
        """
        Registra el balance del mes y determina si requiere compensación.
        """
        from datetime import date
        from calendar import monthrange
        
        primer_dia = date(anio, mes, 1)
        num_dias = monthrange(anio, mes)[1]
        ultimo_dia = date(anio, mes, num_dias)
        
        # Contar días proyectados
        proyecciones = AsistenciaDiaria.objects.filter(
            empleado=trabajador,
            fecha__gte=primer_dia,
            fecha__lte=ultimo_dia,
            es_proyeccion=True
        )
        
        dias_trabajo_proy = proyecciones.filter(estado='TRABAJO').count()
        dias_descanso_proy = proyecciones.filter(estado='DESCANSO').count()
        
        # Contar días reales
        reales = AsistenciaDiaria.objects.filter(
            empleado=trabajador,
            fecha__gte=primer_dia,
            fecha__lte=ultimo_dia,
            es_proyeccion=False
        )
        
        dias_trabajo_real = reales.filter(estado='TRABAJO').count()
        dias_descanso_real = reales.filter(estado='DESCANSO').count()
        
        # Crear o actualizar balance
        balance, created = BalanceCicloTrabajador.objects.update_or_create(
            trabajador=trabajador,
            fecha_inicio_periodo=primer_dia,
            fecha_fin_periodo=ultimo_dia,
            defaults={
                'dias_trabajo_proyectados': dias_trabajo_proy,
                'dias_descanso_proyectados': dias_descanso_proy,
                'dias_trabajo_reales': dias_trabajo_real,
                'dias_descanso_reales': dias_descanso_real,
            }
        )
        
        balance.calcular_balance()
        
        # Sugerir tipo de compensación
        if balance.requiere_compensacion():
            if balance.diferencia_trabajo > 0:
                # Trabajó días extra → extender próximo descanso
                balance.tipo_compensacion = 'EXTENDER_DESCANSO'
            else:
                # Trabajó menos → adelantar próximo descanso
                balance.tipo_compensacion = 'ADELANTAR_DESCANSO'
            balance.save()
        
        return balance
    
    @staticmethod
    def aplicar_compensacion(balance):
        """
        Aplica la compensación ajustando fecha_inicio_ciclo del trabajador.
        """
        if balance.compensacion_aplicada:
            logger.warning(f"Compensación ya aplicada para balance {balance.id}")
            return False
        
        trabajador = balance.trabajador
        diferencia = balance.diferencia_trabajo
        
        if diferencia == 0:
            return False
        
        # Ajustar fecha_inicio_ciclo
        trabajador.fecha_inicio_ciclo = trabajador.fecha_inicio_ciclo - timedelta(days=diferencia)
        trabajador.save()
        
        balance.compensacion_aplicada = True
        balance.fecha_compensacion = date.today()
        balance.observaciones += f"\nCompensación aplicada automáticamente el {date.today()}"
        balance.save()
        
        logger.info(
            f"Compensación aplicada para {trabajador}: {diferencia:+d} días. "
            f"Nueva fecha inicio ciclo: {trabajador.fecha_inicio_ciclo}"
        )
        
        return True
```

---

## 📋 PLAN DE IMPLEMENTACIÓN RECOMENDADO

### **FASE 1: Quick Win (Esta semana)** ⭐
1. Implementar **Nivel 1**: Ajuste manual con botón
2. Probar con 5-10 trabajadores reales
3. Validar con supervisores

**Tiempo**: 3-4 horas
**Riesgo**: Bajo
**Valor**: Alto (resuelve el 80% del problema)

### **FASE 2: Mejora Incremental (Próximo mes)**
1. Implementar **Nivel 2**: Proyección híbrida
2. Dashboard de monitoreo de desfases
3. Alertas automáticas cuando hay desfase >5 días

**Tiempo**: 2 días
**Riesgo**: Medio
**Valor**: Muy alto (automatización parcial)

### **FASE 3: Sistema Completo (Q1 2026)**
1. Implementar **Nivel 3**: Sistema de balance completo
2. Migración de base de datos
3. Reportes de balance histórico
4. API para integraciones

**Tiempo**: 5 días
**Riesgo**: Medio-Alto
**Valor**: Máximo (solución definitiva)

---

## 🎯 RECOMENDACIÓN FINAL

**Implementar NIVEL 1 inmediatamente** y evaluar resultados antes de decidir si avanzar a niveles superiores.

### Razones:
- ✅ Soluciona el 80% del problema
- ✅ Bajo riesgo técnico
- ✅ Implementación rápida (3-4 horas)
- ✅ No requiere cambios de BD
- ✅ Validación fácil con usuarios

### Próximos Pasos:
1. **Hoy**: Implementar código del Nivel 1
2. **Mañana**: Pruebas con datos reales
3. **Siguientes 2 semanas**: Monitorear uso y feedback
4. **Mes 2**: Decisión sobre Nivel 2/3 basada en experiencia real

---

## 📚 REFERENCIAS

- **Deputy**: Shift management con ajuste automático
- **When I Work**: Rolling schedules para turnos rotativos
- **Replicon**: Solución específica para minería/petróleo con ciclos FIFO (Fly-In-Fly-Out)

---

**Documento creado**: Enero 2026  
**Autor**: Sistema DrillControl  
**Versión**: 1.0
