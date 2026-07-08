# GSF Agent

Agente Windows do inventário TI da GSF Hub.

## Configuração

Copie `config.example.json` para `config.json` no mesmo diretório do agente e ajuste quando necessário.

```json
{
  "server": "http://intranet.osascohsf.hosp",
  "endpoint": "/api/inventario/heartbeat/",
  "error_endpoint": "/api/inventario/agent-error/",
  "interval": 30,
  "agent_version": "2.1.0",
  "request_timeout": 8,
  "log_file": "C:\\ProgramData\\GSF\\Agent\\logs\\gsf-agent.log",
  "log_level": "INFO"
}
```

Não use IP fixo no código. Altere o servidor pelo `config.json`.

O agente registra logs locais e reporta falhas de coleta para a GSF Hub pelo `error_endpoint`.
Falhas de rede no heartbeat ficam apenas no log local para evitar repetição de erro quando a intranet estiver indisponível.

## Execução manual

```powershell
cd C:\Projetos\intranet_gsf\agentes\inventario_ti
python -m pip install -r requirements.txt
python agent.py --once
python agent.py
```

## Serviço com NSSM

```powershell
cd C:\Projetos\intranet_gsf\agentes\inventario_ti
.\install_nssm.ps1 -PythonPath "C:\Caminho\Python\python.exe"
```

Para remover:

```powershell
cd C:\Projetos\intranet_gsf\agentes\inventario_ti
.\uninstall_nssm.ps1
```

## Serviço com pywin32

```powershell
python agent.py --service install
python agent.py --service start
python agent.py --service stop
```

Para distribuição por GPO, empacote o diretório do agente com `config.json` apontando para o DNS interno.
