from django.core.management.base import BaseCommand

from modulos.models import Modulo


class Command(BaseCommand):
    help = 'Cria ou atualiza o módulo Ramais e Contatos.'

    def handle(self, *args, **options):
        modulo, criado = Modulo.objects.update_or_create(
            nome='Ramais e Contatos',
            defaults={
                'descricao': 'Central de ramais, telefones, e-mails e contatos internos por unidade e setor.',
                'categoria': 'administrativo',
                'icone': '☎️',
                'tag': 'Contatos',
                'link': '/portal/modulos/ramais-contatos/',
                'palavras_chave': (
                    'ramais contatos telefones email setores unidades recepcao ti '
                    'faturamento cadastro farmacia enfermagem centro cirurgico'
                ),
                'ativo': True,
                'ordem': 30,
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