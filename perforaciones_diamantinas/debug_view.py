"""Debug directo del view de login"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.views import LoginView

factory = RequestFactory()
request = factory.get('/login/')

print("=" * 80)
print("TEST: Llamando directamente al LoginView")
print("=" * 80)

try:
    view = LoginView.as_view()
    response = view(request)
    print(f"Status Code: {response.status_code}")
    print("OK - View funciono correctamente")
except Exception as e:
    print(f"\nERROR CAPTURADO:")
    print(f"Tipo: {type(e).__name__}")
    print(f"Mensaje: {e}")
    print("\nTraceback completo:")
    import traceback
    traceback.print_exc()
