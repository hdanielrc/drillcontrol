"""
Configuración de la aplicación Drilling.
"""

from django.apps import AppConfig


class DrillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'drilling'
    verbose_name = 'Sistema de Perforaciones Diamantinas'

    def ready(self):
        """
        Se ejecuta cuando Django termina de inicializar la aplicación.
        """
        # La sincronización automática se deshabilitó porque:
        # 1. No es necesario sincronizar cada vez que inicia el servidor
        # 2. Puede causar lentitud en desarrollo (recargas frecuentes)
        # 3. Es mejor usar sincronización programada (cron/task scheduler)
        #
        # Para sincronizar manualmente:
        #   python manage.py sync_all_contracts
        #
        # Para sincronización automática diaria:
        #   python setup_sync_schedule.py
        pass
