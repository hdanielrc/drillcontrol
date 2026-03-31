from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('drilling', '0082_add_meta_turno'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── 1. Nuevos campos en Maquina ──────────────────────────────────────
        migrations.AddField(
            model_name='maquina',
            name='numero_serie',
            field=models.CharField(blank=True, max_length=100, verbose_name='Número de serie'),
        ),
        migrations.AddField(
            model_name='maquina',
            name='marca',
            field=models.CharField(blank=True, max_length=100, verbose_name='Marca'),
        ),
        migrations.AddField(
            model_name='maquina',
            name='modelo_equipo',
            field=models.CharField(blank=True, max_length=100, verbose_name='Modelo'),
        ),
        migrations.AddField(
            model_name='maquina',
            name='año_fabricacion',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Año de fabricación'),
        ),
        migrations.AddField(
            model_name='maquina',
            name='potencia_hp',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Potencia (HP)'),
        ),
        migrations.AddField(
            model_name='maquina',
            name='observaciones',
            field=models.TextField(blank=True, verbose_name='Observaciones'),
        ),
        migrations.AddField(
            model_name='maquina',
            name='ultimo_mantenimiento_fecha',
            field=models.DateField(blank=True, null=True, verbose_name='Último mantenimiento'),
        ),
        migrations.AddField(
            model_name='maquina',
            name='ultimo_mantenimiento_horometro',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Horómetro último mtto.'),
        ),
        migrations.AddField(
            model_name='maquina',
            name='proximo_mantenimiento_horometro',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Próximo mtto. (hrs)'),
        ),
        migrations.AddField(
            model_name='maquina',
            name='intervalo_mantenimiento_horas',
            field=models.DecimalField(decimal_places=2, default=250, max_digits=8, verbose_name='Intervalo mtto. (hrs)'),
        ),
        migrations.AddField(
            model_name='maquina',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='maquina',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),

        # ── 2. Nuevo modelo MantenimientoMaquina ─────────────────────────────
        migrations.CreateModel(
            name='MantenimientoMaquina',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('fecha_inicio', models.DateField(verbose_name='Fecha inicio')),
                ('fecha_fin', models.DateField(blank=True, null=True, verbose_name='Fecha fin')),
                ('horometro_registro', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Horómetro al momento del mtto. (hrs)')),
                ('tipo', models.CharField(
                    choices=[('PREVENTIVO','Preventivo'),('CORRECTIVO','Correctivo'),
                             ('INSPECCION','Inspección'),('OVERHAUL','Overhaul / Revisión mayor'),('EMERGENCIA','Emergencia')],
                    default='PREVENTIVO', max_length=20, verbose_name='Tipo de mantenimiento'
                )),
                ('prioridad', models.CharField(
                    choices=[('BAJA','Baja'),('MEDIA','Media'),('ALTA','Alta'),('CRITICA','Crítica')],
                    default='MEDIA', max_length=10, verbose_name='Prioridad'
                )),
                ('estado_ot', models.CharField(
                    choices=[('PENDIENTE','Pendiente'),('EN_PROCESO','En proceso'),('COMPLETADO','Completado'),('CANCELADO','Cancelado')],
                    default='PENDIENTE', max_length=15, verbose_name='Estado OT'
                )),
                ('descripcion', models.TextField(verbose_name='Descripción del problema / motivo')),
                ('trabajo_realizado', models.TextField(blank=True, verbose_name='Trabajo realizado')),
                ('repuestos_utilizados', models.TextField(blank=True, verbose_name='Repuestos / materiales utilizados')),
                ('tiempo_parada_horas', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Tiempo de parada (hrs)')),
                ('costo_mano_obra', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Costo mano de obra (S/)')),
                ('costo_repuestos', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Costo repuestos (S/)')),
                ('costo_total', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Costo total (S/)')),
                ('proveedor_taller', models.CharField(blank=True, max_length=200, verbose_name='Proveedor / Taller')),
                ('proxima_intervencion_horometro', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Próxima intervención (hrs)')),
                ('estado_posterior', models.CharField(
                    choices=[('OPERATIVO','Operativo'),('MANTENIMIENTO','En Mantenimiento'),('FUERA_SERVICIO','Fuera de Servicio')],
                    default='OPERATIVO', max_length=20, verbose_name='Estado posterior al mtto.'
                )),
                ('responsable_tecnico', models.CharField(blank=True, max_length=200, verbose_name='Responsable técnico')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones adicionales')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('maquina', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mantenimientos', to='drilling.maquina', verbose_name='Máquina'
                )),
                ('registrado_por', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='mantenimientos_maquina_registrados', to=settings.AUTH_USER_MODEL, verbose_name='Registrado por'
                )),
                ('aprobado_por', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='mantenimientos_maquina_aprobados', to=settings.AUTH_USER_MODEL, verbose_name='Aprobado por'
                )),
            ],
            options={
                'verbose_name': 'Mantenimiento de Máquina',
                'verbose_name_plural': 'Mantenimientos de Máquinas',
                'db_table': 'mantenimiento_maquina',
                'ordering': ['-fecha_inicio', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='mantenimientomaquina',
            index=models.Index(fields=['maquina', 'fecha_inicio'], name='mant_maq_maq_fecha_idx'),
        ),
        migrations.AddIndex(
            model_name='mantenimientomaquina',
            index=models.Index(fields=['tipo'], name='mant_maq_tipo_idx'),
        ),
        migrations.AddIndex(
            model_name='mantenimientomaquina',
            index=models.Index(fields=['estado_ot'], name='mant_maq_estado_ot_idx'),
        ),
        migrations.AddIndex(
            model_name='mantenimientomaquina',
            index=models.Index(fields=['fecha_inicio'], name='mant_maq_fecha_idx'),
        ),
    ]
