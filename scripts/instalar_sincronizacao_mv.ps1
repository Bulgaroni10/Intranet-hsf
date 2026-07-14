#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$Projeto = 'C:\Projetos\intranet_gsf',
    [string]$Python = 'C:\Projetos\venv_intranet\Scripts\python.exe',
    [string]$Unidade = 'HSFOS',
    [datetime]$Horario = '02:00'
)

$ErrorActionPreference = 'Stop'
$nomeTarefa = "GSF-Sincronizar-Convenios-MV-$Unidade"
$executor = Join-Path $Projeto 'scripts\executar_sincronizacao_mv.ps1'

if (-not (Test-Path -LiteralPath $executor)) {
    throw "Executor da sincronização não encontrado: $executor"
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python do ambiente virtual não encontrado: $Python"
}

$argumentos = @(
    '-NoProfile',
    '-ExecutionPolicy Bypass',
    "-File `"$executor`"",
    "-Projeto `"$Projeto`"",
    "-Python `"$Python`"",
    "-Unidade `"$Unidade`""
) -join ' '

$acao = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $argumentos
$gatilho = New-ScheduledTaskTrigger -Daily -At $Horario
$configuracoes = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
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

$tarefa = Get-ScheduledTask -TaskName $nomeTarefa
$info = Get-ScheduledTaskInfo -TaskName $nomeTarefa

[pscustomobject]@{
    Tarefa = $tarefa.TaskName
    Estado = $tarefa.State
    Unidade = $Unidade
    Horario = $Horario.ToString('HH:mm')
    ProximaExecucao = $info.NextRunTime
    Executor = $executor
}

