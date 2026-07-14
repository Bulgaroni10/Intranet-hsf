# Sincronização automática de convênios do MV

A GSF Hub consulta o Oracle MV e atualiza convênios, planos, regras de atendimento e procedimentos proibidos por unidade.

## Funcionamento

- a sincronização roda no servidor da intranet;
- a tarefa utiliza as variáveis Oracle já protegidas no ambiente do serviço `IntranetGSF`;
- nenhuma senha é gravada no script ou no log;
- a unidade é identificada pela sigla da GSF Hub e pelo código MV cadastrado nela;
- a operação é idempotente e não deve duplicar registros;
- a tarefa ignora uma nova execução quando a anterior ainda estiver ativa.
- uma falha gera notificação crítica para a TI vinculada à unidade;
- a próxima execução bem-sucedida encerra automaticamente a notificação de falha.

## Teste manual

Antes de instalar a automação:

```powershell
cd C:\Projetos\intranet_gsf
powershell.exe -ExecutionPolicy Bypass `
    -File .\scripts\executar_sincronizacao_mv.ps1 `
    -Unidade HSFOS
```

O resultado esperado informa as quantidades de convênios, planos, regras e procedimentos proibidos.

## Instalação da tarefa

Abra o PowerShell como administrador no servidor da intranet:

```powershell
cd C:\Projetos\intranet_gsf
powershell.exe -ExecutionPolicy Bypass `
    -File .\scripts\instalar_sincronizacao_mv.ps1 `
    -Unidade HSFOS `
    -Horario '02:00'
```

A tarefa criada será `GSF-Sincronizar-Convenios-MV-HSFOS` e executará diariamente às 02:00 como `SYSTEM`.

## Validação

```powershell
Get-ScheduledTask -TaskName 'GSF-Sincronizar-Convenios-MV-HSFOS' |
    Select-Object TaskName, State

Get-ScheduledTaskInfo -TaskName 'GSF-Sincronizar-Convenios-MV-HSFOS' |
    Select-Object LastRunTime, LastTaskResult, NextRunTime
```

Para testar imediatamente:

```powershell
Start-ScheduledTask -TaskName 'GSF-Sincronizar-Convenios-MV-HSFOS'
```

Depois consulte:

```powershell
Get-Content 'C:\ProgramData\GSF\logs\sincronizacao-mv-2026-07.log' -Tail 30
```

O arquivo muda mensalmente. `LastTaskResult` igual a `0` indica sucesso.

## Nova unidade

1. Cadastre o código da empresa MV na unidade.
2. Confirme que os dados Oracle dessa empresa estão disponíveis para o usuário de integração.
3. Execute o sincronizador manualmente usando a sigla da unidade.
4. Confira os totais e os filtros no portal.
5. Instale uma tarefa própria para a unidade.

Exemplo:

```powershell
powershell.exe -ExecutionPolicy Bypass `
    -File .\scripts\instalar_sincronizacao_mv.ps1 `
    -Unidade HSFVF `
    -Horario '02:30'
```

Use horários diferentes por unidade para evitar consultas simultâneas pesadas no Oracle.

## Diagnóstico

Se a tarefa falhar, execute manualmente o arquivo `executar_sincronizacao_mv.ps1` e consulte o log. Verifique:

- variáveis `GSF_MV_DB_USER`, `GSF_MV_DB_PASSWORD` e `GSF_MV_DB_DSN` no NSSM;
- caminho `GSF_MV_ORACLE_CLIENT_DIR` e Oracle Instant Client;
- conectividade com a porta 1521;
- código MV da unidade;
- permissões do usuário Oracle sobre as views utilizadas.

Não coloque a senha Oracle em comandos, documentação, commits ou capturas de tela.
