# Serviço Windows da intranet

O Django é executado pelo NSSM no serviço `IntranetGSF`, usando Waitress como servidor WSGI de produção e escutando apenas no loopback usado pelo IIS.

Configuração esperada:

```text
Application: C:\Projetos\venv_intranet\Scripts\python.exe
AppDirectory: C:\Projetos\intranet_gsf
AppParameters: -m waitress --listen=127.0.0.1:8000 --threads=8 --channel-timeout=120 intranet_gsf.wsgi:application
```

Para aplicar ou reparar a configuração, execute como administrador:

```powershell
powershell.exe -ExecutionPolicy Bypass -File C:\Projetos\intranet_gsf\scripts\configurar_servico_intranet.ps1
```

O instalador reinicia o serviço e valida a porta `8000` e uma resposta HTTP local. Se o Waitress não iniciar, restaura automaticamente o `runserver --noreload` para manter a intranet disponível.
