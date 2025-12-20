"""Script para debuguear el error del login"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

# Crear cliente de prueba
client = Client()

print("=" * 80)
print("TEST: Intentando acceder al login")
print("=" * 80)

try:
    response = client.get('/login/')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 500:
        print("\nERROR 500 - Internal Server Error")
        print("\nContenido de la respuesta:")
        print(response.content.decode('utf-8')[:1000])
    elif response.status_code == 200:
        print("\nLogin page cargo correctamente")
    else:
        print(f"\nStatus inesperado: {response.status_code}")
        print("\nContenido:")
        print(response.content.decode('utf-8')[:1000])
        
except Exception as e:
    print(f"\nEXCEPCION CAPTURADA:")
    print(f"Tipo: {type(e).__name__}")
    print(f"Mensaje: {str(e)}")
    
    import traceback
    print("\nTraceback completo:")
    traceback.print_exc()

print("\n" + "=" * 80)
print("Verificando usuarios en la BD:")
print("=" * 80)
usuarios = CustomUser.objects.all()[:5]
for u in usuarios:
    print(f"  - {u.username}: role='{u.role}' (valid={u.role in [r[0] for r in CustomUser.USER_ROLES]})")
    
print(f"\nTotal usuarios: {CustomUser.objects.count()}")
print(f"Roles válidos: {[r[0] for r in CustomUser.USER_ROLES]}")
