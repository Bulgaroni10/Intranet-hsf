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
