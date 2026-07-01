from django.core.management.base import BaseCommand

from modulos.models import Modulo


class Command(BaseCommand):
    help = 'Cria ou atualiza o módulo Manuais e Procedimentos.'

    def handle(self, *args, **options):
        modulo, criado = Modulo.objects.update_or_create(
            nome='Manuais e Procedimentos',
            defaults={
                'descricao': 'Central de POPs, manuais, procedimentos e documentos internos.',
                'categoria': 'administrativo',
                'icone': '📚',
                'tag': 'Documentos',
                'link': '/portal/modulos/manuais-procedimentos/',
                'palavras_chave': (
                    'manuais procedimentos pop documentos tutoriais treinamento '
                    'normas protocolos arquivos instrucoes'
                ),
                'ativo': True,
                'ordem': 20,
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