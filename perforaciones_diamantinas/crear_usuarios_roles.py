"""
Script para crear usuarios por rol para cada contrato
- ADMINISTRADOR, LOGISTICO, RESIDENTE por cada contrato
- DANIEL CPRO (Control de Proyectos)
- DANIEL GRN (Gerencia)
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import CustomUser, Contrato

def normalizar_nombre(nombre):
    """Normaliza el nombre del contrato para username"""
    # Remover espacios y caracteres especiales
    return nombre.upper().replace(' ', '').replace('-', '')

def crear_usuarios_contrato():
    """Crea usuarios para cada contrato activo"""
    print("="*80)
    print("CREANDO USUARIOS POR CONTRATO")
    print("="*80)
    
    contratos = Contrato.objects.filter(estado='ACTIVO')
    roles_contrato = ['ADMINISTRADOR', 'LOGISTICO', 'RESIDENTE']
    
    creados = 0
    existentes = 0
    
    for contrato in contratos:
        print(f"\n--- Contrato: {contrato.nombre_contrato} ---")
        nombre_normalizado = normalizar_nombre(contrato.nombre_contrato)
        
        for rol in roles_contrato:
            username = f"{rol}{nombre_normalizado}"
            
            # Verificar si ya existe
            if CustomUser.objects.filter(username=username).exists():
                print(f"  ⚠️  Usuario ya existe: {username}")
                existentes += 1
                continue
            
            # Crear usuario
            usuario = CustomUser.objects.create_user(
                username=username,
                password='VilbraDD2024',  # Contraseña por defecto
                role=rol,
                contrato=contrato,
                is_staff=True if rol == 'ADMINISTRADOR' else False,
                is_system_admin=False
            )
            print(f"  ✅ Usuario creado: {username} (Rol: {rol})")
            creados += 1
    
    print(f"\n✅ Usuarios de contrato creados: {creados}")
    print(f"⚠️  Usuarios que ya existían: {existentes}")

def crear_usuarios_globales():
    """Crea usuarios de CONTROL_PROYECTOS y GERENCIA"""
    print("\n" + "="*80)
    print("CREANDO USUARIOS GLOBALES")
    print("="*80)
    
    usuarios_globales = [
        {
            'username': 'DANIELCPRO',
            'role': 'CONTROL_PROYECTOS',
            'nombre': 'Daniel Control de Proyectos'
        },
        {
            'username': 'DANIELGRN',
            'role': 'GERENCIA',
            'nombre': 'Daniel Gerencia'
        }
    ]
    
    for usuario_data in usuarios_globales:
        username = usuario_data['username']
        
        if CustomUser.objects.filter(username=username).exists():
            print(f"⚠️  Usuario ya existe: {username}")
            continue
        
        usuario = CustomUser.objects.create_user(
            username=username,
            password='VilbraDD2024',  # Contraseña por defecto
            role=usuario_data['role'],
            contrato=None,  # Sin contrato específico
            is_staff=True,
            is_system_admin=True  # Tienen acceso a todo el sistema
        )
        print(f"✅ Usuario creado: {username} (Rol: {usuario_data['role']})")

def mostrar_resumen():
    """Muestra resumen de usuarios creados"""
    print("\n" + "="*80)
    print("RESUMEN DE USUARIOS")
    print("="*80)
    
    usuarios = CustomUser.objects.all().select_related('contrato').order_by('role', 'username')
    
    print(f"\nTotal de usuarios: {usuarios.count()}\n")
    
    # Agrupar por rol
    por_rol = {}
    for usuario in usuarios:
        rol = usuario.role if usuario.role else 'SIN_ROL'
        if rol not in por_rol:
            por_rol[rol] = []
        por_rol[rol].append(usuario)
    
    for rol, users in sorted(por_rol.items()):
        print(f"\n--- {rol} ({len(users)} usuarios) ---")
        for user in users:
            contrato_info = f" → {user.contrato.nombre_contrato}" if user.contrato else " → GLOBAL"
            admin_flag = " [ADMIN SISTEMA]" if user.is_system_admin else ""
            print(f"  • {user.username}{contrato_info}{admin_flag}")
    
    print("\n" + "="*80)
    print("NOTA: Contraseña por defecto para todos: VilbraDD2024")
    print("="*80)

def main():
    print("="*80)
    print("INICIO DE CREACIÓN DE USUARIOS")
    print("="*80)
    
    crear_usuarios_contrato()
    crear_usuarios_globales()
    mostrar_resumen()
    
    print("\n✅ PROCESO COMPLETADO")

if __name__ == "__main__":
    main()
