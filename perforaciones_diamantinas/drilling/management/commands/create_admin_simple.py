from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from drilling.models import Cliente, Contrato

User = get_user_model()

class Command(BaseCommand):
    help = 'Crea un superusuario simple con cliente y contrato básicos'

    def handle(self, *args, **options):
        # Crear cliente simple
        cliente, created = Cliente.objects.get_or_create(nombre='Cliente Demo')
        if created:
            self.stdout.write(self.style.SUCCESS('Cliente Demo creado'))
        
        # Crear contrato simple
        contrato, created = Contrato.objects.get_or_create(
            nombre_contrato='Sistema Principal',
            defaults={
                'cliente': cliente, 
                'duracion_turno': 8, 
                'estado': 'ACTIVO'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Contrato Sistema Principal creado'))
        
        # Crear superusuario
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@perforaciones.com',
                password='admin123',
                first_name='Administrador',
                last_name='Sistema',
                contrato=contrato,
                is_system_admin=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Superusuario admin creado con contrato {contrato.nombre_contrato}')
            )
        else:
            self.stdout.write(
                self.style.WARNING('El usuario admin ya existe')
            )