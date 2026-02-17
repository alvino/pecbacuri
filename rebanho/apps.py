from django.apps import AppConfig


class rebanhoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rebanho'

    # NOVO: Conecta os signals
    def ready(self):
        import rebanho.signals