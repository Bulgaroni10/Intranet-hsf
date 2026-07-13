# Checklist de padronização visual — GSF Hub

Padrão-alvo: tema escuro corporativo, sidebar/topbar únicas, cards `gsf-*`, formulários responsivos, tabelas alinhadas e estados vazios padronizados.

## Base global

- [x] Carregar `theme.css` depois do CSS específico das páginas.
- [x] Unificar variáveis de cores antigas e atuais.
- [x] Padronizar inputs, selects, textareas, foco e botões.
- [x] Padronizar tabelas, cards, grids e alinhamento vertical.
- [ ] Revisar visualmente desktop e resolução 1366×768 no servidor.
- [ ] Revisar responsividade em telas menores.

## Módulos

- [x] Dashboard / Portal — estrutura nova já utiliza componentes GSF.
- [ ] Avisos e comunicados.
- [ ] Base de conhecimento.
- [ ] Conversas.
- [ ] Documentos e protocolos.
- [ ] Ramais e contatos.
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
