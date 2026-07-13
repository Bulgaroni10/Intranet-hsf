# Monitoramento de impressoras

O NOC consulta a frota Brother somente para leitura e não armazena senhas administrativas.

## Deploy

Após `manage.py migrate`, carregue a frota e faça a primeira consulta:

```powershell
C:\Projetos\venv_intranet\Scripts\python.exe manage.py cadastrar_impressoras_hsfos
C:\Projetos\venv_intranet\Scripts\python.exe manage.py monitorar_impressoras
```

Crie, como administrador, a coleta automática a cada cinco minutos:

```powershell
$acao = New-ScheduledTaskAction -Execute 'C:\Projetos\venv_intranet\Scripts\python.exe' -Argument 'manage.py monitorar_impressoras' -WorkingDirectory 'C:\Projetos\intranet_gsf'
$gatilho = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName 'GSF-Monitorar-Impressoras' -Action $acao -Trigger $gatilho -User 'SYSTEM' -RunLevel Highest
```

## Migration

- `inventario_ti.0006_impressoramonitorada`: cadastro e estado atual das impressoras.

## Comandos operacionais

- `monitorar_impressoras`: atualiza disponibilidade, modelo, diagnóstico e notificações.
- `cadastrar_impressoras_hsfos`: carga idempotente da frota inicial do HSFOS.
