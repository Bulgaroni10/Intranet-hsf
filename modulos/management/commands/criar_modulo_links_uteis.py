from django.core.management.base import BaseCommand

from modulos.models import Modulo


class Command(BaseCommand):
    help = 'Cria ou atualiza o módulo Links Úteis / Sistemas Internos.'

    def handle(self, *args, **options):
        modulo, criado = Modulo.objects.update_or_create(
            nome='Links Úteis / Sistemas Internos',
            defaults={
                'descricao': 'Central de atalhos para sistemas internos, portais e ferramentas de apoio.',
                'categoria': 'tecnologia',
                'icone': '🔗',
                'tag': 'Acessos',
                'link': '/portal/modulos/links-uteis/',
                'palavras_chave': (
                    'links uteis sistemas internos acessos mv pep idce doctor id '
                    'bookstack zabbix glpi chamados email webmail portal fornecedores'
                ),
                'ativo': True,
                'ordem': 15,
            }
        )

        if criado:
            self.stdout.write(
                self.style.SUCCESS(f'Módulo criado: {modulo.nome}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Módulo atualizado: {modulo.nome}')
            )