from django.core.management.base import BaseCommand

from status_sistemas.models import SistemaMonitorado


class Command(BaseCommand):
    help = 'Cria sistemas monitorados iniciais.'

    def handle(self, *args, **options):
        sistemas = [
            {
                'nome': 'MV / Sistema Hospitalar',
                'descricao': 'Sistema hospitalar principal.',
                'categoria': 'assistencial',
                'icone': '🏥',
                'ordem': 10,
            },
            {
                'nome': 'PEP / Prontuário Eletrônico',
                'descricao': 'Prontuário eletrônico do paciente.',
                'categoria': 'assistencial',
                'icone': '📋',
                'ordem': 20,
            },
            {
                'nome': 'IDCE / Laudos',
                'descricao': 'Sistema de laudos e exames.',
                'categoria': 'assistencial',
                'icone': '🩺',
                'ordem': 30,
            },
            {
                'nome': 'Doctor ID',
                'descricao': 'Escalas médicas e gestão do corpo clínico.',
                'categoria': 'assistencial',
                'icone': '👨‍⚕️',
                'ordem': 40,
            },
            {
                'nome': 'Internet / Links',
                'descricao': 'Links de internet e comunicação entre unidades.',
                'categoria': 'infraestrutura',
                'icone': '🌐',
                'ordem': 50,
            },
            {
                'nome': 'VPN',
                'descricao': 'Acesso remoto aos sistemas internos.',
                'categoria': 'infraestrutura',
                'icone': '🔐',
                'ordem': 60,
            },
            {
                'nome': 'Impressoras',
                'descricao': 'Serviços de impressão nas unidades.',
                'categoria': 'infraestrutura',
                'icone': '🖨️',
                'ordem': 70,
            },
            {
                'nome': 'Pastas de Rede',
                'descricao': 'Compartilhamentos e arquivos internos.',
                'categoria': 'infraestrutura',
                'icone': '📁',
                'ordem': 80,
            },
            {
                'nome': 'Agendamento',
                'descricao': 'Serviço de agendamento e atendimento.',
                'categoria': 'administrativo',
                'icone': '📅',
                'ordem': 90,
            },
        ]

        criados = 0
        atualizados = 0

        for item in sistemas:
            sistema, criado = SistemaMonitorado.objects.update_or_create(
                nome=item['nome'],
                defaults=item
            )

            if criado:
                criados += 1
                self.stdout.write(self.style.SUCCESS(f'Sistema criado: {sistema.nome}'))
            else:
                atualizados += 1
                self.stdout.write(f'Sistema atualizado: {sistema.nome}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Base inicial de status criada.'))
        self.stdout.write(f'Criados: {criados}')
        self.stdout.write(f'Atualizados: {atualizados}')