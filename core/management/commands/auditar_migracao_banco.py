import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Lista a quantidade de registros de cada modelo para validar uma migração de banco.'

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true', dest='como_json')
        parser.add_argument(
            '--output',
            help='Salva o resultado em UTF-8 no caminho informado.',
        )
        parser.add_argument(
            '--exclude',
            action='append',
            default=[],
            metavar='APP.MODEL',
            help='Ignora um modelo na auditoria. Pode ser repetido.',
        )

    def handle(self, *args, **options):
        contagens = {}
        excluidos = {item.strip().lower() for item in options['exclude']}
        for model in apps.get_models():
            if model._meta.proxy or not model._meta.managed:
                continue
            chave = f'{model._meta.app_label}.{model._meta.model_name}'
            if chave.lower() in excluidos:
                continue
            contagens[chave] = model._default_manager.count()

        contagens = dict(sorted(contagens.items()))
        if options['como_json']:
            resultado = json.dumps(contagens, ensure_ascii=False, indent=2)
        else:
            resultado = '\n'.join(
                f'{modelo}: {quantidade}'
                for modelo, quantidade in contagens.items()
            )

        if options['output']:
            destino = Path(options['output']).expanduser().resolve()
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(resultado + '\n', encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f'Auditoria salva em {destino}'))
            return

        self.stdout.write(resultado)
