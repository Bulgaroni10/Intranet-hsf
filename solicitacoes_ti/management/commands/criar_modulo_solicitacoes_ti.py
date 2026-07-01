from django.core.management.base import BaseCommand

from modulos.models import Modulo


class Command(BaseCommand):
    help = 'Cria ou atualiza o módulo Solicitações Internas de TI.'

    def handle(self, *args, **options):
        modulo, criado = Modulo.objects.update_or_create(
            nome='Solicitações Internas de TI',
            defaults={
                'descricao': 'Abertura e acompanhamento de solicitações internas para a equipe de Tecnologia da Informação.',
                'categoria': 'tecnologia',
                'icone': '🎫',
                'tag': 'Solicitações',
                'link': '/portal/modulos/solicitacoes-ti/',
                'palavras_chave': (
                    'solicitacoes chamados ti suporte acesso sistema impressora '
                    'rede internet ramal equipamento mv pep idce email'
                ),
                'ativo': True,
                'ordem': 18,
            }
        )

        if criado:
            self.stdout.write(self.style.SUCCESS(f'Módulo criado: {modulo.nome}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Módulo atualizado: {modulo.nome}'))