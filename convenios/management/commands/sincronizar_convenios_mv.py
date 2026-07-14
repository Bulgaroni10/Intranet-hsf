from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from convenios.mv_oracle import IntegracaoMVErro, sincronizar_unidade
from convenios.models import SincronizacaoMVExecucao
from core.models import NotificacaoUsuario
from core.services.permissions import PERFIS_TI
from usuarios.models import Unidade


ORIGEM_NOTIFICACAO = 'sincronizacao_mv'


def _usuarios_ti_da_unidade(unidade):
    return get_user_model().objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(groups__name__in=PERFIS_TI),
    ).filter(
        Q(unidade=unidade) | Q(unidades_permitidas=unidade),
    ).distinct()


def _notificar_falha(unidade, erro):
    for usuario in _usuarios_ti_da_unidade(unidade):
        notificacao, _ = NotificacaoUsuario.objects.get_or_create(
            usuario=usuario,
            origem=ORIGEM_NOTIFICACAO,
            objeto_id=str(unidade.pk),
            defaults={
                'titulo': f'Falha na sincronização MV · {unidade.sigla}',
                'descricao': str(erro)[:1000],
                'tipo': 'danger',
                'icone': '🏥',
                'link': '/portal/modulos/mv/convenios/',
            },
        )
        notificacao.titulo = f'Falha na sincronização MV · {unidade.sigla}'
        notificacao.descricao = str(erro)[:1000]
        notificacao.tipo = 'danger'
        notificacao.lida = False
        notificacao.lida_em = None
        notificacao.save(update_fields=['titulo', 'descricao', 'tipo', 'lida', 'lida_em'])


def _resolver_alerta(unidade):
    NotificacaoUsuario.objects.filter(
        origem=ORIGEM_NOTIFICACAO,
        objeto_id=str(unidade.pk),
        lida=False,
    ).update(lida=True, lida_em=timezone.now())


class Command(BaseCommand):
    help = 'Sincroniza convênios e planos do Oracle MV para uma unidade.'

    def add_arguments(self, parser):
        parser.add_argument('--unidade', required=True, help='Sigla da unidade na GSF Hub.')

    def handle(self, *args, **options):
        try:
            unidade = Unidade.objects.get(sigla__iexact=options['unidade'], ativo=True)
        except Unidade.DoesNotExist as exc:
            raise CommandError('Unidade ativa não encontrada.') from exc
        execucao = SincronizacaoMVExecucao.objects.create(unidade=unidade)
        try:
            resultado = sincronizar_unidade(unidade)
        except IntegracaoMVErro as exc:
            execucao.status = 'erro'
            execucao.mensagem = str(exc)[:4000]
            execucao.finalizado_em = timezone.now()
            execucao.save(update_fields=['status', 'mensagem', 'finalizado_em'])
            _notificar_falha(unidade, exc)
            raise CommandError(str(exc)) from exc
        execucao.status = 'sucesso'
        execucao.convenios = resultado['convenios']
        execucao.planos = resultado['planos']
        execucao.regras = resultado['regras']
        execucao.procedimentos = resultado['procedimentos']
        execucao.finalizado_em = timezone.now()
        execucao.save(update_fields=[
            'status', 'convenios', 'planos', 'regras', 'procedimentos', 'finalizado_em',
        ])
        _resolver_alerta(unidade)
        self.stdout.write(self.style.SUCCESS(
            f'{unidade.sigla}: {resultado["convenios"]} convênios, '
            f'{resultado["planos"]} planos, {resultado["regras"]} regras e '
            f'{resultado["procedimentos"]} procedimentos proibidos.'
        ))
