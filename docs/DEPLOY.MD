# Deploy — Windows Server

## Configuração inicial do NSSM

Gere uma chave fora do Git:

```powershell
C:\Projetos\venv_intranet\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Configure o serviço (substitua o valor da chave):

```powershell
nssm set IntranetGSF AppEnvironmentExtra "GSF_DEBUG=false" "GSF_SECRET_KEY=CHAVE_GERADA" "GSF_ALLOWED_HOSTS=intranet.osascohsf.hosp,SRV-INTRANET,SRV-INTRANET.osascohsf.hosp,127.0.0.1"
```

Nunca registre a chave em arquivo versionado, chamado ou captura de tela.

## Atualização

```powershell
cd C:\Projetos\intranet_gsf
Copy-Item .\db.sqlite3 .\db_backup_antes_deploy.sqlite3
git pull origin main
C:\Projetos\venv_intranet\Scripts\python.exe manage.py migrate
C:\Projetos\venv_intranet\Scripts\python.exe manage.py collectstatic --noinput
C:\Projetos\venv_intranet\Scripts\python.exe manage.py check --deploy
nssm restart IntranetGSF
```

Confirme depois que páginas de erro não exibem traceback e que `showmigrations` não apresenta migrations pendentes.
