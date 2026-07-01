from django.core.management.base import BaseCommand

from modulos.models import Modulo


class Command(BaseCommand):
    help = 'Cria ou atualiza o módulo Avisos / Comunicados.'

    def handle(self, *args, **options):
        modulo, criado = Modulo.objects.update_or_create(
            nome='Avisos / Comunicados',
            defaults={
                'descricao': 'Central de comunicados internos, manutenções, avisos e orientações operacionais.',
                'categoria': 'administrativo',
                'icone': '📢',
                'tag': 'Avisos',
                'link': '/portal/modulos/avisos/',
                'palavras_chave': (
                    'avisos comunicados manutencao indisponibilidade orientacoes '
                    'mudanca de fluxo ti operacional unidade'
                ),
                'ativo': True,
                'ordem': 5,
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