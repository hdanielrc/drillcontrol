from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from drilling.models import Cliente, Contrato

User = get_user_model()

class Command(BaseCommand):
    help = 'Crea un superusuario con contrato inicial'

    def handle(self, *args, **options):
        # 1) Crear (o tomar) admin primero, sin contrato aún
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@perforaciones.com',
                password='admin123',
                first_name='Administrador',
                last_name='Sistema',
                is_system_admin=True
            )
            self.stdout.write(self.style.SUCCESS('Superusuario admin creado'))
        else:
            admin_user = User.objects.get(username='admin')
            self.stdout.write(self.style.WARNING('El usuario admin ya existe'))

        # 2) Crear cliente sin created_by si el modelo no permite null, 
        # pero como tienes NOT NULL, lo hacemos después de tener admin
        cliente, _ = Cliente.objects.get_or_create(nombre='Cliente Demo')

        # 3) Crear contrato y asignarlo
        contrato, _ = Contrato.objects.get_or_create(
            nombre_contrato='Sistema Principal',
            defaults={
                'cliente': cliente,
                'duracion_turno': 8,
                'estado': 'ACTIVO'
            }
        )

        # 4) Asignar contrato al admin si no lo tiene
        if admin_user.contrato_id is None:
            admin_user.contrato = contrato
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'Contrato asignado al admin: {contrato.nombre_contrato}'))

        # 5) Actualizar cliente.created_by ahora que ya existe admin
        if cliente.created_by_id is None:
            cliente.created_by = admin_user
            cliente.save()

        self.stdout.write(self.style.SUCCESS('Proceso completado'))
