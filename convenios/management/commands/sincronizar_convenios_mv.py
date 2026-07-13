from django.core.management.base import BaseCommand, CommandError

from convenios.mv_oracle import IntegracaoMVErro, sincronizar_unidade
from usuarios.models import Unidade


class Command(BaseCommand):
    help = 'Sincroniza convênios e planos do Oracle MV para uma unidade.'

    def add_arguments(self, parser):
        parser.add_argument('--unidade', required=True, help='Sigla da unidade na GSF Hub.')

    def handle(self, *args, **options):
        try:
            unidade = Unidade.objects.get(sigla__iexact=options['unidade'], ativo=True)
        except Unidade.DoesNotExist as exc:
            raise CommandError('Unidade ativa não encontrada.') from exc
        try:
            resultado = sincronizar_unidade(unidade)
        except IntegracaoMVErro as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f'{unidade.sigla}: {resultado["convenios"]} convênios, '
            f'{resultado["planos"]} planos, {resultado["regras"]} regras e '
            f'{resultado["procedimentos"]} procedimentos proibidos.'
        ))
