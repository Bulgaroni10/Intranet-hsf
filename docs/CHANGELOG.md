# 2026-07-10 — Correções e experiência individual

- Corrigida a rota de Convênios com URL canônica e redirects legados.
- Telas de Documentos, Base de Conhecimento, Ramais e Avisos vinculadas ao Design System GSF.
- Dashboard sem Solicitações Internas e com chamados TI filtrados por perfil/unidade.
- Notificações persistentes e individuais, com marcação de leitura protegida.
- Login seleciona automaticamente a única unidade vinculada ao usuário.
- Favoritos individuais no Dashboard e na Sidebar.
- Conversas com datas agrupadas, disponibilidade, anexos seguros e notificações por destinatário.
- Adicionados testes de regressão para isolamento de chamados, login/unidade, favoritos, notificações e anexos de conversa.
- Adicionado roteiro reproduzível de homologação funcional.

## Migrations

- `core.0001_initial`: notificações individuais.
- `core.0002_favoritomodulo`: favoritos por usuário e módulo.
- `conversas.0003_anexomensagem_statususuariochat`: anexos e disponibilidade no chat.
# 2026-07-10 — Fundação do catálogo TUSS

- Criado catálogo TUSS separado das regras de procedimentos proibidos por plano.
- Adicionadas pesquisa por código/descrição/código MV, filtro por grupo e paginação.
- Criadas permissões por módulo e acesso pela Sidebar.
- Adicionada importação CSV idempotente com modo `--simular`.
# 2026-07-10 — Busca Global

- Substituído o placeholder da topbar por busca funcional com atalho `Ctrl + K`.
- Pesquisa integrada em módulos, documentos, conhecimento, ramais, avisos e solicitações TI.
- Resultados respeitam grupos, usuário, setor e unidade no backend.
- Adicionados testes contra vazamento de ramais e chamados entre usuários/unidades.
# 2026-07-10 — Segurança de produção

- `DEBUG`, `SECRET_KEY` e `ALLOWED_HOSTS` passaram a ser configuráveis pelo ambiente do NSSM.
- Removida a chave fixa do código atual e documentada a rotação obrigatória no servidor.
- Configurado `STATIC_ROOT` para o fluxo real de `collectstatic`.
- Atualizado o procedimento de deploy com backup, migrations e check de produção.
# 2026-07-10 — Arquivos estáticos em produção

- Adicionado WhiteNoise para servir CSS e JavaScript com `DEBUG=False`.
- Criado `requirements.txt` na raiz e atualizado o deploy para instalar dependências.
- Corrigido o login inoperante causado por 404 em `/static/core/js/home.js`.
# 2026-07-10 — NOC 1.0

- Criada tela NOC restrita à TI, otimizada para monitor/TV e atualização a cada 30 segundos.
- Computadores usam heartbeat real de 90 segundos e respeitam a unidade do usuário TI.
- Sistemas exibem ocorrências ativas e distinguem “sem incidente registrado” de monitoramento confirmado.
- Reservados painéis de impressoras, AD e capacidade sem inventar telemetria inexistente.
- Adicionados testes de acesso, unidade e indicadores online.
