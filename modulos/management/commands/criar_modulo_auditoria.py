from django.core.management.base import BaseCommand

from modulos.models import Modulo


class Command(BaseCommand):
    help = 'Cria ou atualiza o módulo Auditoria / Histórico.'

    def handle(self, *args, **options):
        modulo, criado = Modulo.objects.update_or_create(
            nome='Auditoria / Histórico',
            defaults={
                'descricao': 'Histórico de publicações, alterações e ações realizadas nos módulos da intranet.',
                'categoria': 'gestao',
                'icone': '🧾',
                'tag': 'Auditoria',
                'link': '/portal/modulos/auditoria/',
                'palavras_chave': (
                    'auditoria historico rastreabilidade logs publicacoes '
                    'alteracoes documentos avisos usuario gestao'
                ),
                'ativo': True,
                'ordem': 40,
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