from django.core.management.base import BaseCommand

from modulos.models import Modulo


class Command(BaseCommand):
    help = 'Cria ou atualiza o módulo Documentos / Protocolos ONA.'

    def handle(self, *args, **options):
        modulo, criado = Modulo.objects.update_or_create(
            nome='Documentos / Protocolos ONA',
            defaults={
                'descricao': 'Central de POPs, protocolos, políticas internas, fluxos e documentos institucionais.',
                'categoria': 'administrativo',
                'icone': '📑',
                'tag': 'ONA',
                'link': '/portal/modulos/documentos/',
                'palavras_chave': (
                    'documentos protocolos ona pop politica norma manual formulario '
                    'fluxo qualidade setor unidade validade vencimento'
                ),
                'ativo': True,
                'ordem': 8,
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