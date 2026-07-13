import os
from collections import OrderedDict

from django.db import transaction

from .models import (
    Convenio,
    PlanoConvenio,
    ProcedimentoProibidoPlano,
    RegraAtendimentoConvenio,
)


class IntegracaoMVErro(Exception):
    """Erro seguro e apresentável da integração com o MV."""


SQL_CONVENIOS_PLANOS = """
    SELECT DISTINCT
        cd_convenio,
        nm_convenio,
        cd_con_pla,
        ds_con_pla,
        sn_permite_ambulatorio,
        sn_permite_externo,
        sn_permite_homecare,
        sn_permite_urgencia,
        sn_permite_internacao
    FROM DBAMV.V_HSF_DADOS_CONV_PLANO
    WHERE cd_multi_empresa = :cd_multi_empresa
    ORDER BY nm_convenio, ds_con_pla
"""

SQL_PROCEDIMENTOS_PROIBIDOS = """
    SELECT DISTINCT
        cd_pro_fat,
        ds_pro_fat,
        cd_convenio,
        cd_con_pla,
        tp_proibicao,
        tp_atendimento,
        dt_inicial_proibicao,
        dt_fim_proibicao
    FROM DBAMV.V_HSF_DADOS_PROIB_PROCED
    WHERE cd_multi_empresa = :cd_multi_empresa
      AND (dt_inicial_proibicao IS NULL OR dt_inicial_proibicao <= SYSDATE)
      AND (dt_fim_proibicao IS NULL OR dt_fim_proibicao >= TRUNC(SYSDATE))
    ORDER BY cd_convenio, cd_con_pla, cd_pro_fat
"""


MAPA_ATENDIMENTOS = {
    'sn_permite_ambulatorio': ('consulta', 'exame'),
    'sn_permite_externo': ('exame',),
    'sn_permite_homecare': ('terapia',),
    'sn_permite_urgencia': ('pronto_atendimento',),
    'sn_permite_internacao': ('internacao', 'cirurgia'),
}


def _configuracao():
    valores = {
        'user': os.environ.get('GSF_MV_DB_USER', '').strip(),
        'password': os.environ.get('GSF_MV_DB_PASSWORD', ''),
        'dsn': os.environ.get('GSF_MV_DB_DSN', '').strip(),
    }
    ausentes = [chave for chave, valor in valores.items() if not valor]
    if ausentes:
        nomes = ', '.join(f'GSF_MV_DB_{chave.upper()}' for chave in ausentes)
        raise IntegracaoMVErro(f'Configuração Oracle ausente: {nomes}.')
    return valores


def conectar_oracle():
    try:
        import oracledb
    except ImportError as exc:
        raise IntegracaoMVErro('Dependência oracledb não instalada.') from exc

    client_dir = os.environ.get('GSF_MV_ORACLE_CLIENT_DIR', '').strip()
    if client_dir:
        try:
            oracledb.init_oracle_client(lib_dir=client_dir)
        except Exception as exc:
            if 'already been initialized' not in str(exc).lower():
                raise IntegracaoMVErro(f'Não foi possível carregar o Oracle Client: {exc}') from exc

    try:
        return oracledb.connect(**_configuracao())
    except Exception as exc:
        raise IntegracaoMVErro(f'Falha ao conectar ao banco do MV: {exc}') from exc


def consultar_convenios_planos(codigo_empresa, connection_factory=conectar_oracle):
    if not codigo_empresa:
        raise IntegracaoMVErro('A unidade ativa não possui código da empresa no MV.')

    try:
        with connection_factory() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(SQL_CONVENIOS_PLANOS, cd_multi_empresa=int(codigo_empresa))
                colunas = [item[0].lower() for item in cursor.description]
                linhas = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    except IntegracaoMVErro:
        raise
    except Exception as exc:
        raise IntegracaoMVErro(f'Falha ao consultar convênios no MV: {exc}') from exc

    dados = OrderedDict()
    for linha in linhas:
        codigo_convenio = str(linha.get('cd_convenio') or '').strip()
        codigo_plano = str(linha.get('cd_con_pla') or '').strip()
        nome_convenio = str(linha.get('nm_convenio') or '').strip()
        nome_plano = str(linha.get('ds_con_pla') or '').strip()
        if not all((codigo_convenio, codigo_plano, nome_convenio, nome_plano)):
            continue
        chave = (codigo_convenio, codigo_plano)
        dados[chave] = {
            'codigo_convenio': codigo_convenio,
            'nome_convenio': nome_convenio,
            'codigo_plano': codigo_plano,
            'nome_plano': nome_plano,
            'permissoes': {
                campo: str(linha.get(campo) or '').strip().upper() in {'S', 'SIM', '1', 'Y'}
                for campo in MAPA_ATENDIMENTOS
            },
        }

    if not dados:
        raise IntegracaoMVErro(
            'O MV não retornou convênios válidos. Os dados atuais não foram alterados.'
        )
    return list(dados.values())


def consultar_procedimentos_proibidos(codigo_empresa, connection_factory=conectar_oracle):
    try:
        with connection_factory() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(SQL_PROCEDIMENTOS_PROIBIDOS, cd_multi_empresa=int(codigo_empresa))
                colunas = [item[0].lower() for item in cursor.description]
                linhas = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    except IntegracaoMVErro:
        raise
    except Exception as exc:
        raise IntegracaoMVErro(f'Falha ao consultar procedimentos proibidos no MV: {exc}') from exc

    resultado = []
    for linha in linhas:
        codigo = str(linha.get('cd_pro_fat') or '').strip()
        descricao = str(linha.get('ds_pro_fat') or '').strip()
        codigo_convenio = str(linha.get('cd_convenio') or '').strip()
        codigo_plano = str(linha.get('cd_con_pla') or '').strip()
        if not all((codigo, descricao, codigo_convenio, codigo_plano)):
            continue
        resultado.append({
            'codigo': codigo,
            'descricao': descricao,
            'codigo_convenio': codigo_convenio,
            'codigo_plano': codigo_plano,
            'tipo_proibicao': str(linha.get('tp_proibicao') or '').strip(),
            'tipo_atendimento': str(linha.get('tp_atendimento') or '').strip(),
            'inicio_vigencia': linha.get('dt_inicial_proibicao'),
            'fim_vigencia': linha.get('dt_fim_proibicao'),
        })
    return resultado


@transaction.atomic
def aplicar_convenios_planos(unidade, dados):
    if not dados:
        raise IntegracaoMVErro('Sincronização vazia recusada.')

    RegraAtendimentoConvenio.objects.filter(unidade=unidade).delete()
    Convenio.objects.filter(unidades=unidade).update(ativo=False)
    unidade.convenios_mv.clear()

    convenios_processados = {}
    planos_por_convenio = {}
    planos_processados = 0
    regras_processadas = 0
    regras_novas = []

    for item in dados:
        codigo_convenio = item['codigo_convenio']
        convenio_por_codigo = Convenio.objects.filter(codigo_mv=codigo_convenio).first()
        convenio_por_nome = Convenio.objects.filter(nome__iexact=item['nome_convenio']).first()

        # Cadastros manuais antigos podem ter o código em um registro e o nome
        # correto em outro. O nome é único no modelo, portanto consolidamos no
        # registro identificado pelo nome e retiramos a unidade do registro obsoleto.
        if (
            convenio_por_codigo
            and convenio_por_nome
            and convenio_por_codigo.pk != convenio_por_nome.pk
        ):
            convenio_por_codigo.unidades.remove(unidade)
            if not convenio_por_codigo.unidades.exists():
                convenio_por_codigo.delete()
            convenio = convenio_por_nome
        else:
            convenio = convenio_por_nome or convenio_por_codigo

        if convenio is None:
            convenio = Convenio(codigo_mv=codigo_convenio, nome=item['nome_convenio'])
        convenio.codigo_mv = codigo_convenio
        convenio.nome = item['nome_convenio']
        convenio.tipo_mv = 'CONVENIO'
        convenio.ativo = True
        convenio.save()
        convenio.unidades.add(unidade)
        convenios_processados[convenio.pk] = convenio

        plano, _ = PlanoConvenio.objects.update_or_create(
            convenio=convenio,
            codigo_mv=item['codigo_plano'],
            defaults={'nome': item['nome_plano'], 'ativo': True},
        )
        planos_por_convenio.setdefault(convenio.pk, set()).add(plano.pk)
        planos_processados += 1

        permissao_por_tipo = {
            tipo: False
            for tipos_campo in MAPA_ATENDIMENTOS.values()
            for tipo in tipos_campo
        }
        for campo, permitido in item['permissoes'].items():
            if permitido:
                for tipo in MAPA_ATENDIMENTOS[campo]:
                    permissao_por_tipo[tipo] = True
        for tipo, permitido in permissao_por_tipo.items():
            regras_novas.append(RegraAtendimentoConvenio(
                unidade=unidade,
                convenio=convenio,
                plano=plano,
                tipo_atendimento=tipo,
                status='aceito' if permitido else 'nao_aceito',
                observacao='Sincronizado automaticamente com o MV.',
            ))
            regras_processadas += 1

    for convenio_id, planos_atuais in planos_por_convenio.items():
        convenio = convenios_processados[convenio_id]
        if convenio.unidades.exclude(pk=unidade.pk).exists():
            continue
        PlanoConvenio.objects.filter(convenio=convenio).exclude(pk__in=planos_atuais).delete()

    RegraAtendimentoConvenio.objects.bulk_create(regras_novas, batch_size=500)

    # Remove somente cadastros antigos que não pertencem mais a unidade alguma.
    Convenio.objects.filter(unidades__isnull=True).delete()
    return {
        'convenios': len(convenios_processados),
        'planos': planos_processados,
        'regras': regras_processadas,
    }


def aplicar_procedimentos_proibidos(unidade, dados):
    ProcedimentoProibidoPlano.objects.filter(unidade=unidade).delete()
    # Remove a carga legada sem unidade na primeira sincronização real.
    ProcedimentoProibidoPlano.objects.filter(unidade__isnull=True).delete()

    convenios = {
        item.codigo_mv: item
        for item in Convenio.objects.filter(unidades=unidade).exclude(codigo_mv='')
    }
    planos = {
        (item.convenio.codigo_mv, item.codigo_mv): item
        for item in PlanoConvenio.objects.select_related('convenio').filter(
            convenio__unidades=unidade,
        ).exclude(codigo_mv='')
    }
    novos = []
    ignorados = 0
    vistos = set()
    for item in dados:
        plano = planos.get((item['codigo_convenio'], item['codigo_plano']))
        convenio = convenios.get(item['codigo_convenio'])
        chave = (getattr(plano, 'pk', None), item['codigo'])
        if not convenio or not plano or chave in vistos:
            ignorados += 1
            continue
        vistos.add(chave)
        novos.append(ProcedimentoProibidoPlano(
            unidade=unidade,
            convenio=convenio,
            plano=plano,
            codigo_procedimento=item['codigo'],
            descricao_procedimento=item['descricao'],
            tipo_proibicao=item['tipo_proibicao'],
            tipo_atendimento=item['tipo_atendimento'],
            inicio_vigencia=item['inicio_vigencia'],
            fim_vigencia=item['fim_vigencia'],
            ativo=True,
        ))
    ProcedimentoProibidoPlano.objects.bulk_create(novos, batch_size=500)
    return {'procedimentos': len(novos), 'procedimentos_ignorados': ignorados}


def sincronizar_unidade(unidade, connection_factory=conectar_oracle):
    dados = consultar_convenios_planos(unidade.codigo_mv, connection_factory)
    proibicoes = consultar_procedimentos_proibidos(unidade.codigo_mv, connection_factory)
    try:
        with transaction.atomic():
            resultado = aplicar_convenios_planos(unidade, dados)
            resultado.update(aplicar_procedimentos_proibidos(unidade, proibicoes))
            return resultado
    except IntegracaoMVErro:
        raise
    except Exception as exc:
        raise IntegracaoMVErro(f'Falha ao gravar os dados do MV: {exc}') from exc
