[CmdletBinding()]
param(
    [string]$PythonPath = 'C:\Projetos\venv_intranet\Scripts\python.exe'
)

$ErrorActionPreference = 'Stop'
$raiz = $PSScriptRoot
$saida = Join-Path $raiz 'dist'
$agente = Join-Path $raiz 'agent.py'

if (-not (Test-Path -LiteralPath $PythonPath)) { throw "Python não encontrado: $PythonPath" }
if (-not (Test-Path -LiteralPath $agente)) { throw "Agente não encontrado: $agente" }

& $PythonPath -m pip install -r (Join-Path $raiz 'requirements.txt') -r (Join-Path $raiz 'requirements-build.txt')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências de build.' }

& $PythonPath -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name GSFAgent `
    --distpath $saida `
    --workpath (Join-Path $raiz 'build') `
    --specpath $raiz `
    $agente
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar GSFAgent.exe.' }

$exe = Join-Path $saida 'GSFAgent.exe'
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$exe.sha256" -Value $hash -Encoding ascii

[pscustomobject]@{
    Executavel = $exe
    TamanhoMB = [math]::Round((Get-Item -LiteralPath $exe).Length / 1MB, 2)
    SHA256 = $hash
}
