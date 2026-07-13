# Monitoramento de impressoras

O NOC consulta a frota Brother somente para leitura e não armazena senhas administrativas.

## Deploy

Após `manage.py migrate`, carregue a frota e faça a primeira consulta:

```powershell
C:\Projetos\venv_intranet\Scripts\python.exe manage.py cadastrar_impressoras_hsfos
C:\Projetos\venv_intranet\Scripts\python.exe manage.py monitorar_impressoras
```

Crie, como administrador, a coleta automática a cada cinco minutos usando o instalador versionado:

```powershell
powershell.exe -ExecutionPolicy Bypass -File C:\Projetos\intranet_gsf\scripts\instalar_monitoramento_impressoras.ps1
```

O instalador pode ser executado novamente: ele atualiza a tarefa existente sem duplicá-la, realiza uma coleta imediata e mostra o próximo horário agendado.

## Migration

- `inventario_ti.0006_impressoramonitorada`: cadastro e estado atual das impressoras.

## Comandos operacionais

- `monitorar_impressoras`: atualiza disponibilidade, modelo, diagnóstico e notificações.
- `cadastrar_impressoras_hsfos`: carga idempotente da frota inicial do HSFOS.
