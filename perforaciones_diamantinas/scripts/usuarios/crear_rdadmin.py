from drilling.models import CustomUser

# Verificar si ya existe
if CustomUser.objects.filter(username='rdadmin').exists():
    print("⚠ Usuario 'rdadmin' ya existe")
    user = CustomUser.objects.get(username='rdadmin')
    print(f"   Email: {user.email}")
    print(f"   Superusuario: {user.is_superuser}")
    print(f"   Role: {user.role}")
else:
    # Crear superusuario rdadmin
    user = CustomUser.objects.create_superuser(
        username='rdadmin',
        email='rdadmin@drillcontrol.com',
        password='rdadmin2025'
    )
    user.first_name = 'RD'
    user.last_name = 'Admin'
    user.is_system_admin = True
    user.role = 'ADMIN_SISTEMA'
    user.save()
    print("✓ Superusuario creado exitosamente")
    print("   Username: rdadmin")
    print("   Password: rdadmin2025")
    print("   Email: rdadmin@drillcontrol.com")
    print("   Role: ADMIN_SISTEMA")
