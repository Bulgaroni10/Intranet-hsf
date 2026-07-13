#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Origem,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$UnitCode,
    [string]$Servidor = 'http://intranet.osascohsf.hosp',
    [string]$Destino = 'C:\ProgramData\GSF\Agent'
)

$ErrorActionPreference = 'Stop'
$nomeTarefa = 'GSF-Agent-Inventario'
$exeOrigem = Join-Path $Origem 'GSFAgent.exe'
$hashOrigem = "$exeOrigem.sha256"
$exeDestino = Join-Path $Destino 'GSFAgent.exe'

if (-not (Test-Path -LiteralPath $exeOrigem)) { throw "Executável não encontrado: $exeOrigem" }
if (-not (Test-Path -LiteralPath $hashOrigem)) { throw "Hash não encontrado: $hashOrigem" }

$esperado = (Get-Content -LiteralPath $hashOrigem -Raw).Trim().ToLowerInvariant()
$recebido = (Get-FileHash -Algorithm SHA256 -LiteralPath $exeOrigem).Hash.ToLowerInvariant()
if ($esperado -ne $recebido) { throw 'SHA-256 do GSFAgent.exe não confere.' }

Stop-ScheduledTask -TaskName $nomeTarefa -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $Destino, (Join-Path $Destino 'logs') | Out-Null
Copy-Item -LiteralPath $exeOrigem -Destination $exeDestino -Force

$config = [ordered]@{
    server = $Servidor.TrimEnd('/')
    unit_code = $UnitCode.Trim().ToUpperInvariant()
    endpoint = '/api/inventario/heartbeat/'
    error_endpoint = '/api/inventario/agent-error/'
    interval = 30
    request_timeout = 8
    log_file = (Join-Path $Destino 'logs\gsf-agent.log')
    log_level = 'INFO'
}
$config | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Destino 'config.json') -Encoding utf8

$acao = New-ScheduledTaskAction -Execute $exeDestino -WorkingDirectory $Destino
$gatilho = New-ScheduledTaskTrigger -AtStartup
$configuracoes = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $nomeTarefa -Action $acao -Trigger $gatilho -Settings $configuracoes -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
Start-ScheduledTask -TaskName $nomeTarefa
Start-Sleep -Seconds 3

[pscustomobject]@{
    Tarefa = $nomeTarefa
    Estado = (Get-ScheduledTask -TaskName $nomeTarefa).State
    Unidade = $config.unit_code
    Executavel = $exeDestino
    SHA256 = $recebido
}
