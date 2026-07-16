# Runbook de incidentes da GSF Hub

## Verificação rápida

No servidor, execute:

```powershell
Get-Service IntranetGSF
Invoke-WebRequest http://127.0.0.1:8000/health/ -UseBasicParsing -TimeoutSec 15
Get-Content C:\Projetos\intranet_gsf\logs\gsf-hub.log -Tail 100
```

O endpoint deve responder HTTP 200 com `{"status":"ok","database":"ok"}`.

### Quando o endereço público responde 200 e o loopback falha

Se `http://intranet.osascohsf.hosp/health/` responde 200, a intranet está funcionando de ponta a ponta naquele momento. Uma falha anterior em `127.0.0.1:8000` normalmente ocorreu durante a inicialização ou reinicialização do serviço. Confirme:

```powershell
Get-Service IntranetGSF
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
Test-NetConnection 127.0.0.1 -Port 8000
Start-Sleep -Seconds 3
Invoke-WebRequest http://127.0.0.1:8000/health/ -UseBasicParsing -TimeoutSec 15 |
    Select-Object StatusCode, Content
```

Execute um comando por vez. Não cole outro `Invoke-WebRequest` depois de `Select-Object StatusCode, Content`, pois o PowerShell tentará interpretá-lo como argumento do `Select-Object`. Se aparecer o prompt `>>` sem intenção, pressione `Ctrl+C` e refaça o comando.

## Erro 502 no IIS

1. Confirme se `IntranetGSF` está em execução.
2. Confirme se a porta 8000 está ouvindo.
3. Consulte `/health/` diretamente pelo loopback.
4. Leia as últimas linhas de `logs\gsf-hub.log`.
5. Reinicie o serviço somente depois de registrar a mensagem encontrada no log.

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
Restart-Service IntranetGSF
```

## Banco SQLite bloqueado

Não apague `db.sqlite3`, arquivos `-journal`, `-wal` ou `-shm` manualmente.

1. Identifique comandos Python longos.
2. Interrompa somente o processo responsável, após confirmar sua linha de comando.
3. Reinicie o serviço e valide `/health/`.
4. Preserve uma cópia do banco antes de qualquer reparo.

## Serviço não inicia

Confirme no ambiente do serviço:

- `GSF_DEBUG=false`;
- `GSF_SECRET_KEY` preenchida com chave longa e exclusiva;
- `GSF_ALLOWED_HOSTS` contendo os nomes usados para acessar a intranet;
- permissão de escrita na pasta configurada em `GSF_LOG_DIR`.

A aplicação recusa iniciar sem `GSF_SECRET_KEY` quando o debug está desligado.

## Sincronização MV

A sincronização automática permanece desativada. Não habilite tarefas ou a variável
`GSF_MV_SYNC_ENABLED` enquanto a aplicação usar SQLite.
