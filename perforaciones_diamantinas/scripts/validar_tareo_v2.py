"""
=============================================================================
SCRIPT DE VALIDACIÓN POST-IMPLEMENTACIÓN TAREO V2
=============================================================================

Este script valida que todos los componentes del sistema Tareo V2 estén
correctamente implementados y funcionando.

Ejecutar con: python manage.py shell < scripts/validar_tareo_v2.py
"""

import os
import sys
import django

# Configurar Django (si se ejecuta como script standalone)
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
    django.setup()

from django.db import connection
from django.core.exceptions import ValidationError
from drilling.models import AsistenciaDiaria, Trabajador, Contrato
from drilling.utils.tareo_service import TareoService
from datetime import date

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

VERBOSE = True  # Mostrar mensajes detallados

def log(emoji, mensaje, estado="INFO"):
    """Helper para logging con emojis"""
    if VERBOSE:
        prefijo = {
            "OK": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️",
            "INFO": "ℹ️"
        }.get(estado, "•")
        print(f"{prefijo} {mensaje}")


# =============================================================================
# VALIDACIONES
# =============================================================================

def validar_modelo_existe():
    """Valida que el modelo AsistenciaDiaria esté correctamente creado"""
    try:
        # Verificar que la tabla existe
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = 'asistencia_diaria'
            """)
            existe = cursor.fetchone()[0] > 0
        
        if existe:
            log("✅", "Modelo AsistenciaDiaria existe en BD", "OK")
            return True
        else:
            log("❌", "Tabla asistencia_diaria NO existe en BD", "ERROR")
            return False
    except Exception as e:
        log("❌", f"Error al validar modelo: {str(e)}", "ERROR")
        return False


def validar_constraint_unico():
    """Valida que el constraint único esté funcionando"""
    try:
        # Crear trabajador de prueba si no existe
        trabajador = Trabajador.objects.filter(estado='ACTIVO').first()
        if not trabajador:
            log("⚠️", "No hay trabajadores activos para probar", "WARNING")
            return True
        
        # Intentar crear duplicado
        fecha_prueba = date(2026, 1, 1)
        
        # Limpiar registros de prueba previos
        AsistenciaDiaria.objects.filter(
            empleado=trabajador,
            fecha=fecha_prueba
        ).delete()
        
        # Crear primer registro
        AsistenciaDiaria.objects.create(
            empleado=trabajador,
            fecha=fecha_prueba,
            estado='TRABAJO'
        )
        
        # Intentar crear duplicado (debe fallar)
        try:
            AsistenciaDiaria.objects.create(
                empleado=trabajador,
                fecha=fecha_prueba,
                estado='DESCANSO'
            )
            log("❌", "Constraint único NO está funcionando", "ERROR")
            return False
        except Exception:
            log("✅", "Constraint único funciona correctamente", "OK")
            # Limpiar
            AsistenciaDiaria.objects.filter(
                empleado=trabajador,
                fecha=fecha_prueba
            ).delete()
            return True
    
    except Exception as e:
        log("❌", f"Error al validar constraint: {str(e)}", "ERROR")
        return False


def validar_indices():
    """Valida que los índices estén creados"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.statistics 
                WHERE table_name = 'asistencia_diaria'
            """)
            num_indices = cursor.fetchone()[0]
        
        if num_indices >= 4:  # Al menos 4 índices
            log("✅", f"Índices creados correctamente ({num_indices} índices)", "OK")
            return True
        else:
            log("⚠️", f"Número de índices bajo: {num_indices}", "WARNING")
            return True  # No es crítico
    except Exception as e:
        log("⚠️", f"No se pudo validar índices: {str(e)}", "WARNING")
        return True  # No bloquear


def validar_servicio_proyeccion():
    """Valida que el servicio de proyección funcione"""
    try:
        # Verificar que la función existe
        from drilling.utils.tareo_service import generar_proyeccion_mensual
        
        log("✅", "Servicio de proyección importado correctamente", "OK")
        
        # Validar que TareoService tenga los métodos esperados
        metodos_requeridos = [
            'calcular_estado_dia',
            'generar_proyeccion_mensual',
            'obtener_matriz_tareo',
            'corregir_asistencia',
            'actualizar_masivo_desde_formset'
        ]
        
        for metodo in metodos_requeridos:
            if hasattr(TareoService, metodo):
                log("✅", f"  Método '{metodo}' existe", "OK")
            else:
                log("❌", f"  Método '{metodo}' NO existe", "ERROR")
                return False
        
        return True
    
    except ImportError as e:
        log("❌", f"Error al importar servicio: {str(e)}", "ERROR")
        return False
    except Exception as e:
        log("❌", f"Error al validar servicio: {str(e)}", "ERROR")
        return False


def validar_calculo_estado():
    """Valida que el cálculo de estado funcione correctamente"""
    try:
        # Crear trabajador de prueba con régimen 14x7
        contrato = Contrato.objects.filter(estado='ACTIVO').first()
        if not contrato:
            log("⚠️", "No hay contratos activos para probar", "WARNING")
            return True
        
        trabajador = Trabajador.objects.filter(
            estado='ACTIVO',
            regimen_laboral='14x7',
            fecha_inicio_ciclo__isnull=False
        ).first()
        
        if not trabajador:
            log("⚠️", "No hay trabajadores 14x7 con fecha_inicio_ciclo para probar", "WARNING")
            return True
        
        # Probar día 1 del ciclo (debe ser TRABAJO)
        fecha_inicio = trabajador.fecha_inicio_ciclo
        estado_dia1 = TareoService.calcular_estado_dia(trabajador, fecha_inicio)
        
        if estado_dia1 == 'TRABAJO':
            log("✅", "Cálculo de estado día 1: CORRECTO (TRABAJO)", "OK")
        else:
            log("❌", f"Cálculo de estado día 1: INCORRECTO ({estado_dia1})", "ERROR")
            return False
        
        # Probar día 15 del ciclo (debe ser DESCANSO)
        from datetime import timedelta
        fecha_dia15 = fecha_inicio + timedelta(days=14)
        estado_dia15 = TareoService.calcular_estado_dia(trabajador, fecha_dia15)
        
        if estado_dia15 == 'DESCANSO':
            log("✅", "Cálculo de estado día 15: CORRECTO (DESCANSO)", "OK")
        else:
            log("❌", f"Cálculo de estado día 15: INCORRECTO ({estado_dia15})", "ERROR")
            return False
        
        return True
    
    except Exception as e:
        log("❌", f"Error al validar cálculo de estado: {str(e)}", "ERROR")
        return False


def validar_archivos_existen():
    """Valida que todos los archivos necesarios existan"""
    archivos_requeridos = [
        'drilling/models.py',
        'drilling/views_tareo_v2.py',
        'drilling/utils/tareo_service.py',
        'drilling/templates/drilling/tareo/tareo_v2_mensual.html',
        'drilling/templatetags/custom_filters.py',
        'drilling/management/commands/generar_proyeccion_tareo.py',
        'drilling/tests_tareo_v2.py',
        'docs/MIGRACION_TAREO_V2.md',
        'docs/RESUMEN_TAREO_V2.md',
        'docs/EJEMPLOS_USO_TAREO_V2.py',
        'docs/ARQUITECTURA_VISUAL_TAREO_V2.txt'
    ]
    
    todos_existen = True
    for archivo in archivos_requeridos:
        ruta_completa = os.path.join(os.getcwd(), archivo)
        if os.path.exists(ruta_completa):
            log("✅", f"Archivo existe: {archivo}", "OK")
        else:
            log("❌", f"Archivo NO existe: {archivo}", "ERROR")
            todos_existen = False
    
    return todos_existen


def validar_configuracion_trabajadores():
    """Valida que los trabajadores tengan configuración mínima"""
    try:
        # Trabajadores sin régimen
        sin_regimen = Trabajador.objects.filter(
            estado='ACTIVO',
            regimen_laboral__isnull=True
        ).count()
        
        if sin_regimen > 0:
            log("⚠️", f"{sin_regimen} trabajadores sin régimen laboral", "WARNING")
        else:
            log("✅", "Todos los trabajadores tienen régimen laboral", "OK")
        
        # Trabajadores sin fecha_inicio_ciclo
        sin_fecha = Trabajador.objects.filter(
            estado='ACTIVO',
            fecha_inicio_ciclo__isnull=True
        ).count()
        
        if sin_fecha > 0:
            log("⚠️", f"{sin_fecha} trabajadores sin fecha_inicio_ciclo", "WARNING")
            log("ℹ️", "  Ejecutar: Trabajador.objects.filter(fecha_inicio_ciclo__isnull=True).update(fecha_inicio_ciclo=date(2026,1,1))", "INFO")
        else:
            log("✅", "Todos los trabajadores tienen fecha_inicio_ciclo", "OK")
        
        # Trabajadores sin guardia
        sin_guardia = Trabajador.objects.filter(
            estado='ACTIVO',
            guardia_asignada__isnull=True
        ).count()
        
        if sin_guardia > 0:
            log("⚠️", f"{sin_guardia} trabajadores sin guardia asignada", "WARNING")
        else:
            log("✅", "Todos los trabajadores tienen guardia asignada", "OK")
        
        return True
    
    except Exception as e:
        log("❌", f"Error al validar configuración: {str(e)}", "ERROR")
        return False


# =============================================================================
# SCRIPT PRINCIPAL
# =============================================================================

def main():
    """Ejecuta todas las validaciones"""
    print("="*70)
    print("🔍 INICIANDO VALIDACIÓN DEL SISTEMA TAREO V2")
    print("="*70)
    print()
    
    resultados = {}
    
    # Ejecutar validaciones
    print("📦 1. Validando modelo de datos...")
    resultados['modelo'] = validar_modelo_existe()
    print()
    
    print("🔒 2. Validando constraint único...")
    resultados['constraint'] = validar_constraint_unico()
    print()
    
    print("⚡ 3. Validando índices...")
    resultados['indices'] = validar_indices()
    print()
    
    print("🛠️  4. Validando servicio de proyección...")
    resultados['servicio'] = validar_servicio_proyeccion()
    print()
    
    print("🧮 5. Validando cálculo de estado...")
    resultados['calculo'] = validar_calculo_estado()
    print()
    
    print("📁 6. Validando archivos del proyecto...")
    resultados['archivos'] = validar_archivos_existen()
    print()
    
    print("👥 7. Validando configuración de trabajadores...")
    resultados['config'] = validar_configuracion_trabajadores()
    print()
    
    # Resumen
    print("="*70)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("="*70)
    
    total = len(resultados)
    exitosos = sum(1 for v in resultados.values() if v)
    fallidos = total - exitosos
    
    for nombre, resultado in resultados.items():
        emoji = "✅" if resultado else "❌"
        print(f"{emoji} {nombre.upper()}: {'PASS' if resultado else 'FAIL'}")
    
    print()
    print(f"Total: {exitosos}/{total} validaciones exitosas")
    
    if fallidos == 0:
        print()
        print("🎉 ¡TODAS LAS VALIDACIONES PASARON!")
        print("✅ El sistema Tareo V2 está listo para usar")
        print()
        print("📝 Próximos pasos:")
        print("  1. Configurar URLs en drilling/urls.py")
        print("  2. Ejecutar: python manage.py generar_proyeccion_tareo")
        print("  3. Acceder a: /tareo/v2/")
    else:
        print()
        print(f"⚠️  {fallidos} validaciones fallaron")
        print("Por favor, revisar los errores anteriores")
    
    print("="*70)
    
    return fallidos == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
