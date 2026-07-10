import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from convenios.models import ProcedimentoTUSS


class Command(BaseCommand):
    help = 'Importa catálogo TUSS de CSV UTF-8 sem excluir registros existentes.'

    def add_arguments(self, parser):
        parser.add_argument('arquivo')
        parser.add_argument('--simular', action='store_true')

    def handle(self, *args, **options):
        caminho = Path(options['arquivo']).resolve()
        if not caminho.is_file() or caminho.suffix.lower() != '.csv':
            raise CommandError('Informe um arquivo CSV existente.')

        criados = atualizados = ignorados = 0
        with caminho.open('r', encoding='utf-8-sig', newline='') as arquivo:
            leitor = csv.DictReader(arquivo)
            obrigatorias = {'codigo_tuss', 'descricao'}
            if not obrigatorias.issubset(set(leitor.fieldnames or [])):
                raise CommandError('Colunas obrigatórias: codigo_tuss, descricao.')
            with transaction.atomic():
                for numero, linha in enumerate(leitor, start=2):
                    codigo = ''.join(c for c in linha.get('codigo_tuss', '').strip() if c.isdigit())
                    descricao = linha.get('descricao', '').strip()
                    if not codigo or not descricao:
                        ignorados += 1
                        self.stderr.write(f'Linha {numero} ignorada: código ou descrição ausente.')
                        continue
                    _, criado = ProcedimentoTUSS.objects.update_or_create(
                        codigo_tuss=codigo,
                        defaults={
                            'descricao': descricao,
                            'grupo': linha.get('grupo', '').strip(),
                            'subgrupo': linha.get('subgrupo', '').strip(),
                            'codigo_mv': linha.get('codigo_mv', '').strip(),
                            'observacao': linha.get('observacao', '').strip(),
                            'ativo': linha.get('ativo', '1').strip().lower() not in {'0', 'false', 'não', 'nao'},
                        },
                    )
                    criados += int(criado)
                    atualizados += int(not criado)
                if options['simular']:
                    transaction.set_rollback(True)
        modo = 'SIMULAÇÃO' if options['simular'] else 'IMPORTAÇÃO'
        self.stdout.write(self.style.SUCCESS(
            f'{modo}: {criados} criados, {atualizados} atualizados, {ignorados} ignorados.'
        ))
