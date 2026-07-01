from django.apps import AppConfig


class BaseConhecimentoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'base_conhecimento'
    verbose_name = 'Base de Conhecimento'