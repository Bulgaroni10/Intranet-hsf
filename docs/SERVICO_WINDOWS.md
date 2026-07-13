# Serviço Windows da intranet

O Django é executado pelo NSSM no serviço `IntranetGSF`. O `runserver` deve usar loopback e estar sem o recarregador automático, pois o processo filho do autoreload não permanece estável sob o NSSM.

Configuração esperada:

```text
Application: C:\Projetos\venv_intranet\Scripts\python.exe
AppDirectory: C:\Projetos\intranet_gsf
AppParameters: manage.py runserver 127.0.0.1:8000 --noreload
```

Para aplicar ou reparar a configuração, execute como administrador:

```powershell
powershell.exe -ExecutionPolicy Bypass -File C:\Projetos\intranet_gsf\scripts\configurar_servico_intranet.ps1
```

O instalador reinicia o serviço e valida a porta `8000` e uma resposta HTTP local.
