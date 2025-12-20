#!/usr/bin/env python
"""
Script para crear la migración del modelo HistorialBroca
"""
import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

print("\n" + "="*80)
print("CREAR MIGRACIÓN PARA HISTORIALBROCA")
print("="*80)

print("\nPara crear la migración, ejecuta:")
print("\n  python manage.py makemigrations drilling -n historial_broca")
print("\nPara aplicar la migración:")
print("\n  python manage.py migrate drilling")
print("\n" + "="*80)
