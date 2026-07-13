# Checklist de padronização visual — GSF Hub

Padrão-alvo: tema escuro corporativo, sidebar/topbar únicas, cards `gsf-*`, formulários responsivos, tabelas alinhadas e estados vazios padronizados.

## Base global

- [x] Carregar `theme.css` depois do CSS específico das páginas.
- [x] Unificar variáveis de cores antigas e atuais.
- [x] Padronizar inputs, selects, textareas, foco e botões.
- [x] Padronizar tabelas, cards, grids e alinhamento vertical.
- [x] Remover fundos brancos dos cards de indicadores compartilhados.
- [x] Fazer o tema global chegar às telas legadas que carregam apenas `home.css`.
- [x] Cobrir cards, listas, modais, formulários e áreas administrativas antigas.
- [x] Aplicar sidebar e topbar únicas a todas as telas autenticadas legadas.
- [ ] Revisar visualmente desktop e resolução 1366×768 no servidor.
- [ ] Revisar responsividade em telas menores.

## Módulos

- [x] Dashboard / Portal — estrutura nova já utiliza componentes GSF.
- [x] Avisos e comunicados.
- [x] Base de conhecimento.
- [x] Conversas.
- [x] Documentos e protocolos.
- [x] Ramais e contatos — tema escuro e exportação CSV com filtros.
- [ ] Solicitações TI.
- [ ] Inventário TI — visão geral, patrimônio, máquinas e suprimentos.
- [ ] Estoque Setorial.
- [ ] NOC.
- [ ] Status de sistemas.
- [ ] Links úteis e manuais.
- [ ] MV, convênios e importações.
- [ ] Código TUSS.
- [ ] Administração de usuários, grupos, unidades, setores e permissões.
- [ ] Auditoria.

## Critérios por tela

- [ ] Usa `base/base.html` quando não for uma tela especial (login, etiqueta ou NOC).
- [ ] Sem fundo branco ou texto escuro incompatível.
- [ ] Cabeçalho com título, subtítulo e ações alinhadas.
- [ ] Cards com espaçamento, raio e borda padrão.
- [ ] Formulários com labels e campos alinhados em grid responsivo.
- [ ] Tabelas com cabeçalhos, células e ações centralizadas verticalmente.
- [ ] Botões seguem hierarquia primário/secundário/perigo.
- [ ] Estado vazio e mensagens de erro seguem componentes comuns.
- [ ] Permissões e escopo por unidade/setor preservados.
