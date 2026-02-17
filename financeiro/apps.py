from django.apps import AppConfig


class financeiroConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financeiro'

    # NOVO: Conecta os signals
    def ready(self):
        import financeiro.signals