from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from usuarios.models import Unidade, Setor


class Command(BaseCommand):
    help = 'Cria a base inicial da intranet: unidades, setores e grupos.'

    def handle(self, *args, **options):
        unidades = [
            ('HMSF', 'Hospital e Maternidade São Francisco'),
            ('HSFVF', 'Hospital Sagrada Família Vila Formosa'),
            ('HSFMA', 'Hospital Sagrada Família Mauá'),
            ('HSFSR', 'Hospital São Francisco São Roque'),
            ('HSFOS', 'Hospital São Francisco Osasco'),
            ('HSFCA', 'Hospital São Francisco Carapicuíba'),
            ('OPS', 'Operadora / Plano de Saúde'),
        ]

        setores = [
            'TI',
            'Recepção',
            'Agendamento',
            'Cadastro',
            'Farmácia',
            'Laboratório',
            'Enfermagem',
            'Corpo Clínico',
            'Fisioterapia',
            'RH',
            'Financeiro',
            'Faturamento',
            'Suprimentos',
            'Diretoria',
            'Gerência',
            'Qualidade',
            'Engenharia Clínica',
            'Manutenção',
        ]

        grupos = [
            'TI Administrador',
            'TI Suporte',
            'Diretoria',
            'Gerência',
            'Responsável Técnico',
            'Recepção',
            'Agendamento',
            'Médico',
            'Enfermagem',
            'Fisioterapia',
            'Farmácia',
            'Laboratório',
            'Cadastro',
            'RH',
            'Financeiro',
            'Faturamento',
            'Suprimentos',
            'Qualidade',
            'Engenharia Clínica',
            'Manutenção',
            'Colaborador',
        ]

        self.stdout.write(self.style.WARNING('Criando unidades...'))

        for sigla, nome in unidades:
            unidade, criado = Unidade.objects.get_or_create(
                sigla=sigla,
                defaults={
                    'nome': nome,
                    'ativo': True,
                }
            )

            if criado:
                self.stdout.write(self.style.SUCCESS(f'Unidade criada: {sigla} - {nome}'))
            else:
                self.stdout.write(f'Unidade já existe: {sigla} - {unidade.nome}')

        self.stdout.write(self.style.WARNING('Criando setores...'))

        for nome in setores:
            setor, criado = Setor.objects.get_or_create(
                nome=nome,
                defaults={
                    'ativo': True,
                }
            )

            if criado:
                self.stdout.write(self.style.SUCCESS(f'Setor criado: {nome}'))
            else:
                self.stdout.write(f'Setor já existe: {nome}')

        self.stdout.write(self.style.WARNING('Criando grupos...'))

        for nome in grupos:
            grupo, criado = Group.objects.get_or_create(name=nome)

            if criado:
                self.stdout.write(self.style.SUCCESS(f'Grupo criado: {nome}'))
            else:
                self.stdout.write(f'Grupo já existe: {nome}')

        self.stdout.write(self.style.SUCCESS('Base inicial criada com sucesso.'))