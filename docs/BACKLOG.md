# Backlog — Intranet GSF

## NOC Operacional

Visão inicial registrada em `docs/NOC_VISAO_INICIAL.md`. Implementação deve começar somente após a conclusão e homologação das entregas atuais.

## Código TUSS Inteligente

### Objetivo
Permitir que a recepção escaneie uma guia de exames e o sistema identifique os exames solicitados, localize os códigos TUSS no MV e gere códigos de barras para bipagem.

### Fluxo esperado
1. Recepção escaneia a folha.
2. Sistema faz leitura OCR.
3. IA identifica os exames.
4. Sistema consulta base/API do MV.
5. Sistema retorna código TUSS.
6. Usuário confere.
7. Sistema gera código de barras.
8. Recepção bipa no MV.

### Benefício
Reduzir tempo operacional da recepção e diminuir erros de digitação.

### Complexidade
Alta.

### Dependências
- OCR
- Integração com MV
- Base de códigos TUSS
- Validação humana
- Auditoria
- Geração de código de barras

### Status
Backlog futuro.

### Dependência externa — 10/07/2026

Implementação pausada até definição formal com a MV sobre APIs para procedimentos TUSS e exames, incluindo autenticação, escopo dos dados, limites, ambiente de homologação e licenciamento. Não avançar com OCR ou códigos de barras antes dessa validação.
