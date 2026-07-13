#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$Projeto = 'C:\Projetos\intranet_gsf',
    [string]$Python = 'C:\Projetos\venv_intranet\Scripts\python.exe',
    [int]$IntervaloMinutos = 5
)

$ErrorActionPreference = 'Stop'
$nomeTarefa = 'GSF-Monitorar-Impressoras'
$managePy = Join-Path $Projeto 'manage.py'

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python do ambiente virtual não encontrado: $Python"
}

if (-not (Test-Path -LiteralPath $managePy)) {
    throw "Projeto Django não encontrado: $managePy"
}

if ($IntervaloMinutos -lt 1) {
    throw 'O intervalo deve ser de pelo menos 1 minuto.'
}

$acao = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument 'manage.py monitorar_noc' `
    -WorkingDirectory $Projeto

$gatilho = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervaloMinutos)

$configuracoes = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 4) `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $nomeTarefa `
    -Action $acao `
    -Trigger $gatilho `
    -Settings $configuracoes `
    -User 'SYSTEM' `
    -RunLevel Highest `
    -Force | Out-Null

Write-Host 'Executando a primeira coleta...' -ForegroundColor Cyan
& $Python $managePy monitorar_noc
if ($LASTEXITCODE -ne 0) {
    throw "A coleta inicial terminou com código $LASTEXITCODE."
}

Start-ScheduledTask -TaskName $nomeTarefa
Start-Sleep -Seconds 2

$tarefa = Get-ScheduledTask -TaskName $nomeTarefa
$info = Get-ScheduledTaskInfo -TaskName $nomeTarefa

[pscustomobject]@{
    Tarefa = $tarefa.TaskName
    Estado = $tarefa.State
    UltimaExecucao = $info.LastRunTime
    UltimoResultado = $info.LastTaskResult
    ProximaExecucao = $info.NextRunTime
    IntervaloMinutos = $IntervaloMinutos
}
