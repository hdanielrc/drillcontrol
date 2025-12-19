from drilling.models import CustomUser

# Crear superusuario
user = CustomUser.objects.create_superuser(
    username='admin',
    email='admin@drillcontrol.com',
    password='admin123'
)
user.first_name = 'Administrador'
user.last_name = 'Sistema'
user.save()
print("✓ Superusuario creado: admin / admin123")
