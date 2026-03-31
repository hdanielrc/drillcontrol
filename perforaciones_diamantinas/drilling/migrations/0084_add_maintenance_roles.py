"""
Migración: Agregar roles de mantenimiento al sistema.
- JEFE_MANTENIMIENTO: Gerencia de mantenimiento (todos los contratos)
- MANTENIMIENTO: Mantenimiento de contrato (solo su contrato)
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0083_maquina_ficha_mantenimiento_maquina'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('ADMINISTRADOR_GENERAL', 'Administrador General del Sistema'),
                    ('ADMINISTRADOR', 'Administrador de Contrato'),
                    ('LOGISTICO', 'Logístico'),
                    ('RESIDENTE', 'Residente'),
                    ('CONTROL_PROYECTOS', 'Control de Proyectos'),
                    ('GERENCIA', 'Gerencia'),
                    ('GERENTE_GENERAL', 'Gerente General'),
                    ('HEADCOUNT', 'Gestión de Personal y Headcount'),
                    ('JEFE_MANTENIMIENTO', 'Jefe de Mantenimiento'),
                    ('MANTENIMIENTO', 'Mantenimiento de Contrato'),
                    ('MANAGER_CONTRATO', 'Manager de Contrato'),
                    ('SUPERVISOR', 'Supervisor'),
                ],
                default='ADMINISTRADOR',
                help_text='Define los permisos y accesos del usuario',
                max_length=30,
                verbose_name='Rol del usuario',
            ),
        ),
    ]
