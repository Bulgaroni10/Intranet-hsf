#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$Projeto = 'C:\Projetos\intranet_gsf',
    [string]$Python = 'C:\Projetos\venv_intranet\Scripts\python.exe',
    [string]$Destino = 'C:\Backups\GSF-Hub',
    [int]$RetencaoDias = 14,
    [string]$Horario = '02:00'
)

$ErrorActionPreference = 'Stop'
$nome = 'GSF-Backup-Diario'
$executor = Join-Path $Projeto 'scripts\executar_backup_gsf.ps1'
if (-not (Test-Path -LiteralPath $executor)) { throw "Executor não encontrado: $executor" }

$argumentos = "-NoProfile -ExecutionPolicy Bypass -File `"$executor`" -Projeto `"$Projeto`" -Python `"$Python`" -Destino `"$Destino`" -RetencaoDias $RetencaoDias"
$acao = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $argumentos -WorkingDirectory $Projeto
$gatilho = New-ScheduledTaskTrigger -Daily -At $Horario
$configuracoes = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $nome -Action $acao -Trigger $gatilho -Settings $configuracoes -User 'SYSTEM' -RunLevel Highest -Force | Out-Null

Start-ScheduledTask -TaskName $nome
Start-Sleep -Seconds 3
Get-ScheduledTaskInfo -TaskName $nome | Select-Object LastRunTime, LastTaskResult, NextRunTime
