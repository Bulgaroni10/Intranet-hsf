# Arquitetura da GSF Hub

```text
Usuários das unidades
        |
        v
IIS / intranet.osascohsf.hosp
        |
        v
Waitress em 127.0.0.1:8000 (serviço Windows IntranetGSF/NSSM)
        |
        +-- Django: autenticação, unidade ativa, permissões e módulos
        +-- Banco principal: SQLite atual / PostgreSQL planejado
        +-- media/: anexos enviados pelos usuários
        +-- staticfiles/: arquivos coletados e servidos pelo WhiteNoise/IIS
        +-- integrações: agentes, impressoras, AD, rede e Oracle MV controlado
```

## Regras estruturais

1. A unidade ativa é definida no login e validada pelo middleware de usuários.
2. A autorização do módulo e o escopo da unidade devem ser aplicados no backend, não apenas ocultados na interface.
3. Views recebem a requisição; forms validam entradas; services concentram regras de negócio; models persistem dados.
4. Processos longos de monitoramento não devem rodar dentro da requisição web. Use comandos de gerenciamento e tarefas agendadas.
5. O endpoint `/health/` verifica aplicação e banco sem exigir autenticação.

O mapa detalhado de módulos, arquivos e operação está no `README.md` da raiz.
