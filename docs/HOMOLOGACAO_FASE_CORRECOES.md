# Homologação — fase de correções

Execute em ambiente de homologação ou com usuários de teste. Não use dados sensíveis.

## Perfis necessários

- um usuário comum da unidade A;
- outro usuário comum da unidade A;
- um usuário da TI da unidade A;
- um usuário da unidade B;
- um superusuário.

## Roteiro

1. Acesse Convênios pela Sidebar e pelo Dashboard; confirme que as URLs antigas redirecionam.
2. Confira Documentos, Base de Conhecimento, Ramais e Avisos em desktop e celular.
3. Em Ramais, pesquise por nome, setor e ramal; teste **Copiar ramal**.
4. No Dashboard, confirme que Solicitações Internas não aparece.
5. Com usuário comum, confirme que só aparecem seus chamados TI.
6. Com TI, confirme chamados da mesma unidade e ausência de chamados da unidade B.
7. Gere notificações para dois usuários; confira contagens diferentes e marque uma/todas como lidas.
8. Entre sem selecionar unidade; confirme a unidade vinculada no topo do portal.
9. Favorite e desfavorite um módulo; confira persistência no Dashboard e na Sidebar após novo login.
10. Em Conversas, envie mensagens entre dois usuários e confira Hoje/Ontem/data e não lidas.
11. Envie imagem, PDF e documento de até 10 MB; confirme preview/link.
12. Tente baixar o anexo com um usuário que não participa da conversa; o acesso deve ser negado.
13. Tente enviar `.exe`, arquivo acima de 10 MB e arquivo com MIME incompatível; todos devem ser bloqueados.
14. Altere disponibilidade para ocupado, ausente e não perturbe; confira lista e cabeçalho.

## Critério de saída

Registre usuário, unidade, horário, tela e evidência de qualquer falha. A fase está homologada quando todos os itens passam sem vazamento entre usuários ou unidades.
