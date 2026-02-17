from django.apps import AppConfig


class infraestruturaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'infraestrutura'

    # NOVO: Conecta os signals
    def ready(self):
        import infraestrutura.signals