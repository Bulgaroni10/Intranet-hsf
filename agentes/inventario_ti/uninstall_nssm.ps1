param(
    [string]$ServiceName = "GSFAgent",
    [string]$NssmPath = "C:\Servicos\nssm\nssm-2.24\win64\nssm.exe"
)

$ErrorActionPreference = "Stop"

if (!(Test-Path -LiteralPath $NssmPath)) {
    throw "NSSM não encontrado em $NssmPath"
}

& $NssmPath stop $ServiceName
& $NssmPath remove $ServiceName confirm

Write-Host "Serviço $ServiceName removido."
