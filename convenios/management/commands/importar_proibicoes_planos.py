from pathlib import Path
import csv

from django.core.management.base import BaseCommand, CommandError

from convenios.models import (
    Convenio,
    PlanoConvenio,
    ProcedimentoProibidoPlano,
)


def limpar(valor):
    if valor is None:
        return ''

    valor = str(valor).strip()

    if valor.endswith('.0'):
        valor = valor[:-2]

    return valor


def primeira_coluna_com_valor(row, inicio=0):
    for valor in row[inicio:]:
        texto = limpar(valor)

        if texto:
            return texto

    return ''


def normalizar_label(valor):
    return limpar(valor).lower().replace('ê', 'e').replace('é', 'e').replace(':', '').strip()


def obter_convenio(codigo_mv, nome):
    codigo_mv = limpar(codigo_mv)
    nome = limpar(nome)

    convenio = None

    if nome:
        convenio = Convenio.objects.filter(nome__iexact=nome).first()

    if not convenio and codigo_mv:
        convenio = Convenio.objects.filter(codigo_mv=codigo_mv).first()

    if not convenio:
        convenio = Convenio.objects.create(
            codigo_mv=codigo_mv,
            nome=nome,
            ativo=True,
        )
        return convenio, True

    # Atualiza código se estiver vazio
    if codigo_mv and not convenio.codigo_mv:
        convenio.codigo_mv = codigo_mv

    # Só atualiza nome se não gerar duplicidade
    if nome and convenio.nome.lower() != nome.lower():
        nome_ja_existe = Convenio.objects.filter(
            nome__iexact=nome
        ).exclude(id=convenio.id).exists()

        if not nome_ja_existe:
            convenio.nome = nome

    convenio.ativo = True
    convenio.save()

    return convenio, False


def obter_plano(convenio, codigo_mv, nome):
    codigo_mv = limpar(codigo_mv)
    nome = limpar(nome)

    plano = None

    if codigo_mv:
        plano = PlanoConvenio.objects.filter(
            convenio=convenio,
            codigo_mv=codigo_mv
        ).first()

    if not plano and nome:
        plano = PlanoConvenio.objects.filter(
            convenio=convenio,
            nome__iexact=nome
        ).first()

    if not plano:
        plano = PlanoConvenio.objects.create(
            convenio=convenio,
            codigo_mv=codigo_mv,
            nome=nome,
            ativo=True,
        )
        return plano, True

    if codigo_mv and not plano.codigo_mv:
        plano.codigo_mv = codigo_mv

    if nome:
        plano.nome = nome

    plano.ativo = True
    plano.save()

    return plano, False


class Command(BaseCommand):
    help = 'Importa procedimentos proibidos por plano a partir do CSV do MV.'

    def add_arguments(self, parser):
        parser.add_argument(
            'arquivo',
            type=str,
            help='Caminho do arquivo r_conpla_proib.csv'
        )

        parser.add_argument(
            '--encoding',
            type=str,
            default='latin-1',
            help='Encoding do arquivo CSV. Padrão: latin-1'
        )

    def handle(self, *args, **options):
        caminho = Path(options['arquivo'])
        encoding = options['encoding']

        if not caminho.exists():
            raise CommandError(f'Arquivo não encontrado: {caminho}')

        convenio_atual = None
        plano_atual = None

        total_convenios_criados = 0
        total_planos_criados = 0
        total_criados = 0
        total_atualizados = 0
        total_erros = 0
        total_linhas = 0

        self.stdout.write(self.style.WARNING('Iniciando importação de proibições de procedimentos...'))

        with caminho.open('r', encoding=encoding, newline='') as arquivo_csv:
            leitor = csv.reader(arquivo_csv, delimiter=',')

            for numero_linha, row in enumerate(leitor, start=1):
                total_linhas += 1

                if not row:
                    continue

                row = list(row)

                primeira = limpar(row[0]) if len(row) > 0 else ''
                segunda = limpar(row[1]) if len(row) > 1 else ''

                # Linha de convênio
                # Exemplo:
                # Convênio:,,,,19,,PORTO SEGURO - SEGURO SAUDE,
                if normalizar_label(primeira) == 'convenio':
                    codigo_convenio = limpar(row[4]) if len(row) > 4 else ''
                    nome_convenio = limpar(row[6]) if len(row) > 6 else ''

                    if not nome_convenio:
                        nome_convenio = primeira_coluna_com_valor(row, inicio=1)

                    if not nome_convenio:
                        total_erros += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'Linha {numero_linha}: convênio sem nome.'
                            )
                        )
                        convenio_atual = None
                        plano_atual = None
                        continue

                    convenio_atual, criado = obter_convenio(
                        codigo_mv=codigo_convenio,
                        nome=nome_convenio
                    )

                    if criado:
                        total_convenios_criados += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Linha {numero_linha}: convênio criado: {codigo_convenio} - {nome_convenio}'
                            )
                        )

                    plano_atual = None
                    continue

                # Linha de plano
                # Exemplo:
                # ,Plano:,,215,,P 200 E COPAR,,
                if normalizar_label(segunda) == 'plano':
                    if not convenio_atual:
                        total_erros += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'Linha {numero_linha}: plano encontrado sem convênio anterior.'
                            )
                        )
                        plano_atual = None
                        continue

                    codigo_plano = limpar(row[3]) if len(row) > 3 else ''
                    nome_plano = limpar(row[5]) if len(row) > 5 else ''

                    if not nome_plano:
                        nome_plano = primeira_coluna_com_valor(row, inicio=2)

                    if not nome_plano:
                        total_erros += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'Linha {numero_linha}: plano sem nome.'
                            )
                        )
                        plano_atual = None
                        continue

                    plano_atual, criado = obter_plano(
                        convenio=convenio_atual,
                        codigo_mv=codigo_plano,
                        nome=nome_plano
                    )

                    if criado:
                        total_planos_criados += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Linha {numero_linha}: plano criado: {convenio_atual.nome} - {codigo_plano} - {nome_plano}'
                            )
                        )

                    continue

                # Ignora linha de título
                texto_linha = ' '.join([limpar(c) for c in row]).lower()

                if 'proibi' in texto_linha:
                    continue

                # Linhas de procedimento
                # Exemplo:
                # ,,40302784,,,,,"VITAMINA B1, DOSAGEM"
                codigo_procedimento = limpar(row[2]) if len(row) > 2 else ''
                descricao_procedimento = limpar(row[7]) if len(row) > 7 else ''

                if not codigo_procedimento or not descricao_procedimento:
                    continue

                if not codigo_procedimento.isdigit():
                    continue

                if not convenio_atual or not plano_atual:
                    total_erros += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'Linha {numero_linha}: procedimento sem convênio/plano ativo: {codigo_procedimento} - {descricao_procedimento}'
                        )
                    )
                    continue

                procedimento, criado = ProcedimentoProibidoPlano.objects.update_or_create(
                    plano=plano_atual,
                    codigo_procedimento=codigo_procedimento,
                    defaults={
                        'convenio': convenio_atual,
                        'descricao_procedimento': descricao_procedimento,
                        'ativo': True,
                    }
                )

                if criado:
                    total_criados += 1
                else:
                    total_atualizados += 1

                if (total_criados + total_atualizados) % 1000 == 0:
                    self.stdout.write(
                        f'Processados {total_criados + total_atualizados} procedimentos...'
                    )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Importação finalizada.'))
        self.stdout.write(f'Linhas lidas: {total_linhas}')
        self.stdout.write(f'Convênios criados: {total_convenios_criados}')
        self.stdout.write(f'Planos criados: {total_planos_criados}')
        self.stdout.write(f'Procedimentos proibidos criados: {total_criados}')
        self.stdout.write(f'Procedimentos proibidos atualizados: {total_atualizados}')
        self.stdout.write(f'Linhas com erro: {total_erros}')

        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            'Atenção: este arquivo indica procedimentos proibidos por plano. '
            'Se um procedimento aparecer aqui, ele deve ser tratado como não permitido para o plano.'
        ))