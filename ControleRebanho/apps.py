from django.apps import AppConfig


class ControlerebanhoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ControleRebanho'

    # NOVO: Conecta os signals
    def ready(self):
        import ControleRebanho.signals