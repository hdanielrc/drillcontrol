"""
Script para configurar sincronización diaria automática.

Este script te ayuda a configurar la sincronización automática diaria
usando diferentes métodos según tu sistema operativo.

Windows: Programador de tareas (Task Scheduler)
Linux/Mac: Cron
"""

import os
import sys
import platform

def get_project_path():
    """Obtiene la ruta del proyecto"""
    return os.path.dirname(os.path.abspath(__file__))

def get_python_path():
    """Obtiene la ruta del ejecutable de Python"""
    return sys.executable

def show_windows_instructions():
    """Muestra instrucciones para Windows"""
    project_path = get_project_path()
    python_path = get_python_path()
    
    print("\n" + "="*70)
    print("CONFIGURAR SINCRONIZACIÓN DIARIA EN WINDOWS")
    print("="*70 + "\n")
    
    print("Opción 1: Programador de Tareas (Recomendado)")
    print("-" * 70)
    print("\n1. Abre el Programador de tareas:")
    print("   - Presiona Win+R")
    print("   - Escribe: taskschd.msc")
    print("   - Presiona Enter")
    print("\n2. Crea una nueva tarea:")
    print("   - Clic en 'Crear tarea básica'")
    print("   - Nombre: Sincronización Drilling Control")
    print("   - Descripción: Sincroniza inventario desde API Vilbragroup")
    print("\n3. Configurar desencadenador:")
    print("   - Selecciona 'Diariamente'")
    print("   - Hora: 02:00 AM (o la hora que prefieras)")
    print("\n4. Configurar acción:")
    print("   - Selecciona 'Iniciar un programa'")
    print(f"   - Programa: {python_path}")
    print(f"   - Argumentos: manage.py sync_all_contracts")
    print(f"   - Iniciar en: {project_path}")
    print("\n5. Finalizar y guardar")
    
    print("\n\nOpción 2: Script BAT (Manual)")
    print("-" * 70)
    
    bat_content = f"""@echo off
REM Script de sincronización diaria
cd /d {project_path}
"{python_path}" manage.py sync_all_contracts
echo Sincronizacion completada: %date% %time% >> sync_log.txt
"""
    
    bat_file = os.path.join(project_path, 'sync_daily.bat')
    
    try:
        with open(bat_file, 'w') as f:
            f.write(bat_content)
        print(f"\n✓ Archivo BAT creado: {bat_file}")
        print("\nPuedes ejecutarlo manualmente o agregarlo al Programador de tareas")
    except Exception as e:
        print(f"\n✗ Error creando archivo BAT: {e}")

def show_linux_instructions():
    """Muestra instrucciones para Linux/Mac"""
    project_path = get_project_path()
    python_path = get_python_path()
    
    print("\n" + "="*70)
    print("CONFIGURAR SINCRONIZACIÓN DIARIA EN LINUX/MAC")
    print("="*70 + "\n")
    
    print("Usando Cron:")
    print("-" * 70)
    
    cron_line = f"0 2 * * * cd {project_path} && {python_path} manage.py sync_all_contracts >> sync_log.txt 2>&1"
    
    print("\n1. Abre el crontab:")
    print("   crontab -e")
    print("\n2. Agrega esta línea al final:")
    print(f"   {cron_line}")
    print("\n3. Guarda y cierra (Ctrl+X, luego Y, luego Enter)")
    print("\n4. Verifica que se agregó:")
    print("   crontab -l")
    
    print("\n\nExplicación:")
    print("  0 2 * * * = Todos los días a las 2:00 AM")
    print("  Puedes cambiar la hora modificando '0 2' (minuto hora)")
    
    # Crear script shell
    sh_content = f"""#!/bin/bash
# Script de sincronización diaria
cd {project_path}
{python_path} manage.py sync_all_contracts
echo "Sincronización completada: $(date)" >> sync_log.txt
"""
    
    sh_file = os.path.join(project_path, 'sync_daily.sh')
    
    try:
        with open(sh_file, 'w') as f:
            f.write(sh_content)
        os.chmod(sh_file, 0o755)
        print(f"\n✓ Script shell creado: {sh_file}")
        print(f"\nPuedes ejecutarlo manualmente: ./sync_daily.sh")
    except Exception as e:
        print(f"\n✗ Error creando script: {e}")

def show_manual_instructions():
    """Muestra instrucciones para ejecutar manualmente"""
    project_path = get_project_path()
    
    print("\n" + "="*70)
    print("EJECUTAR SINCRONIZACIÓN MANUALMENTE")
    print("="*70 + "\n")
    
    print("Ejecuta este comando cuando necesites sincronizar:")
    print(f"\n  cd {project_path}")
    print("  python manage.py sync_all_contracts")
    
    print("\n\nOpciones disponibles:")
    print("  --dry-run     : Simular sin hacer cambios")
    print("  --verbose     : Mostrar información detallada")
    print("  --skip-pdd    : Omitir productos diamantados")
    print("  --skip-adit   : Omitir aditivos")
    
    print("\n\nEjemplos:")
    print("  python manage.py sync_all_contracts --dry-run")
    print("  python manage.py sync_all_contracts --verbose")

def main():
    """Función principal"""
    print("\n" + "="*70)
    print("CONFIGURACIÓN DE SINCRONIZACIÓN AUTOMÁTICA")
    print("Sistema de Perforaciones Diamantinas")
    print("="*70)
    
    system = platform.system()
    
    print(f"\nSistema detectado: {system}")
    print(f"Python: {get_python_path()}")
    print(f"Proyecto: {get_project_path()}")
    
    if system == "Windows":
        show_windows_instructions()
    else:
        show_linux_instructions()
    
    show_manual_instructions()
    
    print("\n" + "="*70)
    print("INFORMACIÓN ADICIONAL")
    print("="*70)
    print("\nLa sincronización automática también se ejecuta:")
    print("  ✓ Al iniciar el servidor Django (en segundo plano)")
    print("  ✓ Se recomienda programar actualización diaria a las 2:00 AM")
    print("\nLogs de sincronización:")
    print(f"  Ver archivo: {os.path.join(get_project_path(), 'sync_log.txt')}")
    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    main()
