from django.urls import path

from . import views
from ramais_contatos import views as ramais_views
from avisos import views as avisos_views
from documentos import views as documentos_views
from auditoria import views as auditoria_views
from solicitacoes_ti import views as solicitacoes_ti_views
from conversas import views as conversas_views
from usuarios import views as usuarios_views
from convenios import views as convenios_views
from convenios import conteudos_mv_views
from convenios import tuss_views
from base_conhecimento import views as base_conhecimento_views


urlpatterns = [
    path('', views.home, name='home'),
    path('portal/', views.portal, name='portal'),
    path('portal/selecionar-empresa/', views.selecionar_unidade_ativa, name='selecionar_unidade_ativa'),
    path('portal/sidebar/', views.sidebar_global, name='sidebar_global'),
    path('portal/busca/', views.busca_global, name='busca_global'),
    path('portal/noc/', views.painel_noc, name='painel_noc'),

    # Notificações individuais
    path('api/notificacoes/', views.api_listar_notificacoes, name='api_listar_notificacoes'),
    path('api/notificacoes/<int:notificacao_id>/lida/', views.api_marcar_notificacao_lida, name='api_marcar_notificacao_lida'),
    path('api/notificacoes/marcar-todas-lidas/', views.api_marcar_todas_notificacoes_lidas, name='api_marcar_todas_notificacoes_lidas'),
    path('favoritos/<int:modulo_id>/alternar/', views.alternar_favorito_modulo, name='alternar_favorito_modulo'),

    # Conversas
    path('conversas/', conversas_views.conversas_home, name='conversas_home'),
    path('conversas/contador-nao-lidas/', conversas_views.contador_mensagens_nao_lidas, name='contador_mensagens_nao_lidas'),
    path('conversas/api/listar/', conversas_views.api_listar_conversas, name='api_listar_conversas'),
    path('conversas/api/iniciar/', conversas_views.api_iniciar_conversa, name='api_iniciar_conversa'),
    path('conversas/api/grupos/criar/', conversas_views.api_criar_grupo, name='api_criar_grupo_conversa'),
    path('conversas/api/grupos/<int:conversa_id>/detalhe/', conversas_views.api_detalhe_grupo, name='api_detalhe_grupo_conversa'),
    path('conversas/api/grupos/atualizar/', conversas_views.api_atualizar_grupo, name='api_atualizar_grupo_conversa'),
    path('conversas/api/grupos/sair/', conversas_views.api_sair_grupo, name='api_sair_grupo_conversa'),
    path('conversas/api/<int:conversa_id>/mensagens/', conversas_views.api_mensagens_conversa, name='api_mensagens_conversa'),
    path('conversas/api/enviar/', conversas_views.api_enviar_mensagem, name='api_enviar_mensagem'),
    path('conversas/api/status/', conversas_views.api_atualizar_status, name='api_atualizar_status'),
    path('conversas/anexos/<int:anexo_id>/', conversas_views.baixar_anexo_mensagem, name='baixar_anexo_mensagem'),

    # Administração
    path('portal/administracao/', usuarios_views.administracao_intranet, name='administracao_intranet'),

    path('portal/administracao/usuarios/', usuarios_views.administracao_usuarios, name='administracao_usuarios'),
    path('portal/administracao/usuarios/novo/', usuarios_views.novo_usuario, name='novo_usuario'),
    path('portal/administracao/usuarios/editar/<int:usuario_id>/', usuarios_views.editar_usuario, name='editar_usuario'),
    path('portal/administracao/usuarios/resetar-senha/<int:usuario_id>/', usuarios_views.resetar_senha_usuario, name='resetar_senha_usuario'),

    path('portal/administracao/unidades-setores/', usuarios_views.administracao_unidades_setores, name='administracao_unidades_setores'),
    path('portal/administracao/unidades-setores/unidade/nova/', usuarios_views.nova_unidade, name='nova_unidade'),
    path('portal/administracao/unidades-setores/unidade/editar/<int:unidade_id>/', usuarios_views.editar_unidade, name='editar_unidade'),
    path('portal/administracao/unidades-setores/setor/novo/', usuarios_views.novo_setor, name='novo_setor'),
    path('portal/administracao/unidades-setores/setor/editar/<int:setor_id>/', usuarios_views.editar_setor, name='editar_setor'),

    path('portal/administracao/permissoes-modulos/', usuarios_views.administracao_permissoes_modulos, name='administracao_permissoes_modulos'),
    path('portal/administracao/permissoes-modulos/editar/<int:modulo_id>/', usuarios_views.editar_permissao_modulo, name='editar_permissao_modulo'),

    path('portal/administracao/grupos/', usuarios_views.administracao_grupos, name='administracao_grupos'),
    path('portal/administracao/grupos/novo/', usuarios_views.novo_grupo, name='novo_grupo'),
    path('portal/administracao/grupos/editar/<int:grupo_id>/', usuarios_views.editar_grupo, name='editar_grupo'),

    # Base de Conhecimento
    path('portal/modulos/base-conhecimento/', base_conhecimento_views.base_conhecimento, name='base_conhecimento'),
    path('portal/modulos/base-conhecimento/relatorio-leituras/', base_conhecimento_views.relatorio_leituras_conhecimento, name='relatorio_leituras_conhecimento'),
    path('portal/modulos/base-conhecimento/relatorio-leituras/exportar-csv/', base_conhecimento_views.exportar_leituras_conhecimento_csv, name='exportar_leituras_conhecimento_csv'),
    path('portal/modulos/base-conhecimento/categorias/nova/', base_conhecimento_views.nova_categoria_conhecimento, name='nova_categoria_conhecimento'),
    path('portal/modulos/base-conhecimento/categorias/editar/<int:categoria_id>/', base_conhecimento_views.editar_categoria_conhecimento, name='editar_categoria_conhecimento'),
    path('portal/modulos/base-conhecimento/documentos/novo/', base_conhecimento_views.novo_documento_conhecimento, name='novo_documento_conhecimento'),
    path('portal/modulos/base-conhecimento/documentos/confirmar-leitura/<int:documento_id>/', base_conhecimento_views.confirmar_leitura_documento, name='confirmar_leitura_documento'),
    path('portal/modulos/base-conhecimento/documentos/editar/<int:documento_id>/', base_conhecimento_views.editar_documento_conhecimento, name='editar_documento_conhecimento'),
    path('portal/modulos/base-conhecimento/documentos/inativar/<int:documento_id>/', base_conhecimento_views.inativar_documento_conhecimento, name='inativar_documento_conhecimento'),
    path('portal/modulos/base-conhecimento/documentos/reativar/<int:documento_id>/', base_conhecimento_views.reativar_documento_conhecimento, name='reativar_documento_conhecimento'),

    # MV
    path('portal/modulos/mv/', views.modulo_mv, name='modulo_mv'),
    path('portal/modulos/mv/manuais/', views.mv_manuais, name='mv_manuais'),
    path('portal/modulos/mv/convenios/', views.mv_convenios, name='mv_convenios'),
    path('portal/modulos/tuss/', tuss_views.catalogo_tuss, name='catalogo_tuss'),
    path('portal/modulos/convenios/', views.redirect_convenios_legacy, name='convenios_legacy'),
    path('portal/convenios/', views.redirect_convenios_legacy, name='convenios_legacy_curta'),

    path('portal/modulos/mv/contingencia/', convenios_views.mv_contingencia, name='mv_contingencia'),
    path('portal/modulos/mv/chamados/', convenios_views.mv_chamados, name='mv_chamados'),
    path('portal/modulos/mv/links/', convenios_views.mv_links, name='mv_links'),
    path('portal/modulos/mv/observacoes/', convenios_views.mv_observacoes, name='mv_observacoes'),

    path('portal/modulos/mv/conteudos/novo/<str:tipo>/', conteudos_mv_views.novo_conteudo_mv, name='novo_conteudo_mv'),
    path('portal/modulos/mv/conteudos/editar/<int:conteudo_id>/', conteudos_mv_views.editar_conteudo_mv, name='editar_conteudo_mv'),
    path('portal/modulos/mv/conteudos/inativar/<int:conteudo_id>/', conteudos_mv_views.inativar_conteudo_mv, name='inativar_conteudo_mv'),
    path('portal/modulos/mv/conteudos/reativar/<int:conteudo_id>/', conteudos_mv_views.reativar_conteudo_mv, name='reativar_conteudo_mv'),

    path('portal/modulos/mv/importacoes/', convenios_views.importacoes_mv, name='importacoes_mv'),
    path('portal/modulos/mv/importacoes/nova/', convenios_views.nova_importacao_mv, name='nova_importacao_mv'),
    path('portal/modulos/mv/importacoes/<int:importacao_id>/', convenios_views.detalhe_importacao_mv, name='detalhe_importacao_mv'),
    path('portal/modulos/mv/importacoes/modelo/<str:tipo>/', convenios_views.baixar_modelo_importacao_mv, name='baixar_modelo_importacao_mv'),

    path('portal/modulos/mv/convenios/novo/', views.novo_convenio_mv, name='novo_convenio_mv'),
    path('portal/modulos/mv/convenios/editar/<int:convenio_id>/', views.editar_convenio_mv, name='editar_convenio_mv'),
    path('portal/modulos/mv/convenios/inativar/<int:convenio_id>/', views.inativar_convenio_mv, name='inativar_convenio_mv'),
    path('portal/modulos/mv/convenios/reativar/<int:convenio_id>/', views.reativar_convenio_mv, name='reativar_convenio_mv'),

    path('portal/modulos/mv/planos/novo/', views.novo_plano_mv, name='novo_plano_mv'),
    path('portal/modulos/mv/planos/editar/<int:plano_id>/', views.editar_plano_mv, name='editar_plano_mv'),
    path('portal/modulos/mv/planos/inativar/<int:plano_id>/', views.inativar_plano_mv, name='inativar_plano_mv'),
    path('portal/modulos/mv/planos/reativar/<int:plano_id>/', views.reativar_plano_mv, name='reativar_plano_mv'),

    path('portal/modulos/mv/especialidades/nova/', views.nova_especialidade_mv, name='nova_especialidade_mv'),
    path('portal/modulos/mv/especialidades/editar/<int:especialidade_id>/', views.editar_especialidade_mv, name='editar_especialidade_mv'),
    path('portal/modulos/mv/especialidades/inativar/<int:especialidade_id>/', views.inativar_especialidade_mv, name='inativar_especialidade_mv'),
    path('portal/modulos/mv/especialidades/reativar/<int:especialidade_id>/', views.reativar_especialidade_mv, name='reativar_especialidade_mv'),

    path('portal/modulos/mv/regras/nova/', views.nova_regra_convenio_mv, name='nova_regra_convenio_mv'),
    path('portal/modulos/mv/regras/editar/<int:regra_id>/', views.editar_regra_convenio_mv, name='editar_regra_convenio_mv'),
    path('portal/modulos/mv/regras/inativar/<int:regra_id>/', views.inativar_regra_convenio_mv, name='inativar_regra_convenio_mv'),
    path('portal/modulos/mv/regras/reativar/<int:regra_id>/', views.reativar_regra_convenio_mv, name='reativar_regra_convenio_mv'),

    path('portal/modulos/mv/procedimentos-proibidos/novo/', views.novo_procedimento_proibido_mv, name='novo_procedimento_proibido_mv'),
    path('portal/modulos/mv/procedimentos-proibidos/editar/<int:procedimento_id>/', views.editar_procedimento_proibido_mv, name='editar_procedimento_proibido_mv'),
    path('portal/modulos/mv/procedimentos-proibidos/inativar/<int:procedimento_id>/', views.inativar_procedimento_proibido_mv, name='inativar_procedimento_proibido_mv'),
    path('portal/modulos/mv/procedimentos-proibidos/reativar/<int:procedimento_id>/', views.reativar_procedimento_proibido_mv, name='reativar_procedimento_proibido_mv'),

    # Status dos Sistemas
    path('portal/modulos/status-sistemas/', views.status_sistemas, name='status_sistemas'),
    path('portal/modulos/status-sistemas/sistema/novo/', views.novo_sistema_monitorado, name='novo_sistema_monitorado'),
    path('portal/modulos/status-sistemas/sistema/editar/<int:sistema_id>/', views.editar_sistema_monitorado, name='editar_sistema_monitorado'),
    path('portal/modulos/status-sistemas/sistema/inativar/<int:sistema_id>/', views.inativar_sistema_monitorado, name='inativar_sistema_monitorado'),
    path('portal/modulos/status-sistemas/sistema/reativar/<int:sistema_id>/', views.reativar_sistema_monitorado, name='reativar_sistema_monitorado'),
    path('portal/modulos/status-sistemas/nova/', views.nova_ocorrencia_status, name='nova_ocorrencia_status'),
    path('portal/modulos/status-sistemas/historico/', views.historico_ocorrencias_status, name='historico_ocorrencias_status'),
    path('portal/modulos/status-sistemas/historico/exportar-csv/', views.exportar_historico_ocorrencias_csv, name='exportar_historico_ocorrencias_csv'),
    path('portal/modulos/status-sistemas/encerrar/<int:ocorrencia_id>/', views.encerrar_ocorrencia_status, name='encerrar_ocorrencia_status'),

    # Manuais e Procedimentos
    path('portal/modulos/manuais-procedimentos/', views.manuais_procedimentos, name='manuais_procedimentos'),
    path('portal/modulos/manuais-procedimentos/novo/', views.novo_manual_procedimento, name='novo_manual_procedimento'),
    path('portal/modulos/manuais-procedimentos/editar/<int:conteudo_id>/', views.editar_manual_procedimento, name='editar_manual_procedimento'),
    path('portal/modulos/manuais-procedimentos/inativar/<int:conteudo_id>/', views.inativar_manual_procedimento, name='inativar_manual_procedimento'),
    path('portal/modulos/manuais-procedimentos/reativar/<int:conteudo_id>/', views.reativar_manual_procedimento, name='reativar_manual_procedimento'),

    # Links úteis
    path('portal/modulos/links-uteis/', views.links_uteis, name='links_uteis'),
    path('portal/modulos/links-uteis/novo/', views.novo_link_util, name='novo_link_util'),
    path('portal/modulos/links-uteis/editar/<int:link_id>/', views.editar_link_util, name='editar_link_util'),
    path('portal/modulos/links-uteis/inativar/<int:link_id>/', views.inativar_link_util, name='inativar_link_util'),
    path('portal/modulos/links-uteis/reativar/<int:link_id>/', views.reativar_link_util, name='reativar_link_util'),

    # Ramais e Contatos
    path('portal/modulos/ramais-contatos/', ramais_views.ramais_contatos, name='ramais_contatos'),
    path('portal/modulos/ramais-contatos/exportar-csv/', ramais_views.exportar_ramais_csv, name='exportar_ramais_csv'),
    path('portal/modulos/ramais-contatos/novo/', ramais_views.novo_ramal_contato, name='novo_ramal_contato'),
    path('portal/modulos/ramais-contatos/editar/<int:contato_id>/', ramais_views.editar_ramal_contato, name='editar_ramal_contato'),
    path('portal/modulos/ramais-contatos/inativar/<int:contato_id>/', ramais_views.inativar_ramal_contato, name='inativar_ramal_contato'),
    path('portal/modulos/ramais-contatos/reativar/<int:contato_id>/', ramais_views.reativar_ramal_contato, name='reativar_ramal_contato'),

    # Avisos
    path('portal/modulos/avisos/', avisos_views.avisos_comunicados, name='avisos_comunicados'),
    path('portal/modulos/avisos/novo/', avisos_views.novo_aviso_comunicado, name='novo_aviso_comunicado'),
    path('portal/modulos/avisos/editar/<int:aviso_id>/', avisos_views.editar_aviso_comunicado, name='editar_aviso_comunicado'),
    path('portal/modulos/avisos/inativar/<int:aviso_id>/', avisos_views.inativar_aviso_comunicado, name='inativar_aviso_comunicado'),
    path('portal/modulos/avisos/reativar/<int:aviso_id>/', avisos_views.reativar_aviso_comunicado, name='reativar_aviso_comunicado'),

    # Documentos
    path('portal/modulos/documentos/', documentos_views.documentos_protocolos, name='documentos_protocolos'),
    path('portal/modulos/documentos/novo/', documentos_views.novo_documento_protocolo, name='novo_documento_protocolo'),
    path('portal/modulos/documentos/editar/<int:documento_id>/', documentos_views.editar_documento_protocolo, name='editar_documento_protocolo'),
    path('portal/modulos/documentos/inativar/<int:documento_id>/', documentos_views.inativar_documento_protocolo, name='inativar_documento_protocolo'),
    path('portal/modulos/documentos/reativar/<int:documento_id>/', documentos_views.reativar_documento_protocolo, name='reativar_documento_protocolo'),

    # Auditoria
    path('portal/modulos/auditoria/', auditoria_views.auditoria_registros, name='auditoria_registros'),

    # Solicitações de TI
    path('portal/modulos/solicitacoes-ti/', solicitacoes_ti_views.solicitacoes_ti, name='solicitacoes_ti'),
    path('portal/modulos/solicitacoes-ti/nova/', solicitacoes_ti_views.nova_solicitacao_ti, name='nova_solicitacao_ti'),
    path('portal/modulos/solicitacoes-ti/detalhe/<int:solicitacao_id>/', solicitacoes_ti_views.detalhe_solicitacao_ti, name='detalhe_solicitacao_ti'),
    path('portal/modulos/solicitacoes-ti/atender/<int:solicitacao_id>/', solicitacoes_ti_views.atender_solicitacao_ti, name='atender_solicitacao_ti'),
    path('portal/modulos/solicitacoes-ti/exportar-csv/', solicitacoes_ti_views.exportar_solicitacoes_ti_csv, name='exportar_solicitacoes_ti_csv'),

    # Login / Logout
    path('login/', views.login_intranet, name='login_intranet'),
    path('logout/', views.logout_intranet, name='logout_intranet'),
]
