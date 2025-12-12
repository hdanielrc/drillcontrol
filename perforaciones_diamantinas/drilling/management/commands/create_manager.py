from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from drilling.models import Contrato

User = get_user_model()

class Command(BaseCommand):
    help = 'Crea un usuario Manager de Contrato'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Nombre de usuario')
        parser.add_argument('password', type=str, help='Contraseña')
        parser.add_argument('--first_name', type=str, help='Nombre', default='')
        parser.add_argument('--last_name', type=str, help='Apellido', default='')
        parser.add_argument('--email', type=str, help='Email', default='')
        parser.add_argument('--contrato', type=str, help='Nombre del contrato', 
                          default='Sistema Principal')

    def handle(self, *args, **options):
        try:
            contrato = Contrato.objects.get(nombre_contrato=options['contrato'])
        except Contrato.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Contrato '{options['contrato']}' no existe")
            )
            return

        if User.objects.filter(username=options['username']).exists():
            self.stdout.write(
                self.style.ERROR(f"Usuario '{options['username']}' ya existe")
            )
            return

        user = User.objects.create_user(
            username=options['username'],
            password=options['password'],
            first_name=options['first_name'],
            last_name=options['last_name'],
            email=options['email'],
            contrato=contrato,
            role='MANAGER_CONTRATO',
            is_system_admin=False,
            is_staff=True,      # Puede acceder al admin Django con restricciones
            is_superuser=False
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Manager '{user.username}' creado exitosamente "
                f"para el contrato '{contrato.nombre_contrato}'"
            )
        )
