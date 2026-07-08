param(
    [string]$ServiceName = "GSFAgent",
    [string]$NssmPath = "C:\Servicos\nssm\nssm-2.24\win64\nssm.exe",
    [string]$PythonPath = "python",
    [string]$InstallDir = $PSScriptRoot
)

$ErrorActionPreference = "Stop"

$AgentPath = Join-Path $InstallDir "agent.py"
$ConfigPath = Join-Path $InstallDir "config.json"
$ConfigExamplePath = Join-Path $InstallDir "config.example.json"
$LogDir = Join-Path $InstallDir "logs"

if (!(Test-Path -LiteralPath $NssmPath)) {
    throw "NSSM não encontrado em $NssmPath"
}

if (!(Test-Path -LiteralPath $AgentPath)) {
    throw "agent.py não encontrado em $AgentPath"
}

if (!(Test-Path -LiteralPath $ConfigPath) -and (Test-Path -LiteralPath $ConfigExamplePath)) {
    Copy-Item -LiteralPath $ConfigExamplePath -Destination $ConfigPath
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

& $NssmPath install $ServiceName $PythonPath $AgentPath
& $NssmPath set $ServiceName AppDirectory $InstallDir
& $NssmPath set $ServiceName AppParameters $AgentPath
& $NssmPath set $ServiceName AppStdout (Join-Path $LogDir "service-stdout.log")
& $NssmPath set $ServiceName AppStderr (Join-Path $LogDir "service-stderr.log")
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateOnline 1
& $NssmPath set $ServiceName AppRotateBytes 1048576
& $NssmPath set $ServiceName Start SERVICE_AUTO_START
& $NssmPath start $ServiceName

Write-Host "Serviço $ServiceName instalado e iniciado."
