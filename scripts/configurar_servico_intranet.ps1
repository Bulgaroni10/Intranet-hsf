#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$NomeServico = 'IntranetGSF',
    [string]$Projeto = 'C:\Projetos\intranet_gsf',
    [string]$Python = 'C:\Projetos\venv_intranet\Scripts\python.exe'
)

$ErrorActionPreference = 'Stop'
$servico = Get-CimInstance Win32_Service -Filter "Name='$NomeServico'"
if (-not $servico) { throw "Serviço $NomeServico não encontrado." }
if (-not (Test-Path -LiteralPath $Python)) { throw "Python não encontrado: $Python" }
if (-not (Test-Path -LiteralPath (Join-Path $Projeto 'manage.py'))) { throw "Projeto Django não encontrado: $Projeto" }

$nssm = $servico.PathName.Trim('"')
if (-not (Test-Path -LiteralPath $nssm)) { throw "NSSM não encontrado: $nssm" }

& $nssm set $NomeServico AppDirectory $Projeto
& $nssm set $NomeServico Application $Python
& $nssm set $NomeServico AppParameters 'manage.py runserver 127.0.0.1:8000 --noreload'

Restart-Service $NomeServico
Start-Sleep -Seconds 5

$porta = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $porta) { throw 'O serviço iniciou, mas a porta 8000 não está ouvindo.' }

$resposta = Invoke-WebRequest 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 10
[pscustomobject]@{
    Servico = $NomeServico
    Estado = (Get-Service $NomeServico).Status
    Endereco = '127.0.0.1:8000'
    HttpStatus = $resposta.StatusCode
    Recarregador = 'desativado'
}
