import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import platform
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psutil
import requests


AGENT_VERSION = "2.1.0"
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = {
    "server": "http://intranet.osascohsf.hosp",
    "endpoint": "/api/inventario/heartbeat/",
    "interval": 30,
    "agent_version": AGENT_VERSION,
    "request_timeout": 8,
    "log_file": str(BASE_DIR / "logs" / "gsf-agent.log"),
    "log_level": "INFO",
}


def carregar_config(caminho_config=None):
    caminho = Path(caminho_config) if caminho_config else BASE_DIR / "config.json"
    config = DEFAULT_CONFIG.copy()

    if caminho.exists():
        with caminho.open("r", encoding="utf-8") as arquivo:
            config.update(json.load(arquivo))

    config["server"] = str(config["server"]).rstrip("/")
    config["endpoint"] = "/" + str(config["endpoint"]).strip("/") + "/"
    config["interval"] = max(5, int(config.get("interval", 30)))
    config["request_timeout"] = max(3, int(config.get("request_timeout", 8)))
    config["agent_version"] = str(config.get("agent_version") or AGENT_VERSION)

    return config


def configurar_logging(config):
    log_file = Path(config["log_file"])
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("gsf_agent")
    logger.setLevel(getattr(logging, config.get("log_level", "INFO").upper(), logging.INFO))
    logger.handlers.clear()

    formato = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    arquivo_handler = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    arquivo_handler.setFormatter(formato)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formato)

    logger.addHandler(arquivo_handler)
    logger.addHandler(console_handler)

    return logger


def montar_url_heartbeat(config):
    return f"{config['server']}{config['endpoint']}"


def executar_powershell(comando):
    try:
        resultado = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                comando,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        saida = resultado.stdout.strip()
        return saida or "-"

    except Exception:
        return "-"


def get_hostname():
    try:
        hostname = socket.gethostname()
        return hostname.split(".")[0].upper()
    except Exception:
        return "-"


def get_usuario_logado():
    try:
        usuario = executar_powershell("(Get-CimInstance Win32_ComputerSystem).UserName")

        if not usuario or usuario == "-" or usuario.endswith("$"):
            return "-"

        return usuario.replace("\\", "/")

    except Exception:
        return "-"


def get_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "-"


def get_mac():
    try:
        mac = uuid.getnode()
        return ":".join(
            ["{:02x}".format((mac >> ele) & 0xff) for ele in range(40, -1, -8)]
        ).upper()
    except Exception:
        return "-"


def get_disco():
    try:
        disco = psutil.disk_usage("C:\\")
        total = round(disco.total / 1024**3, 2)
        livre = round(disco.free / 1024**3, 2)
        usado_percentual = disco.percent

        return total, livre, usado_percentual
    except Exception:
        return 0, 0, 0


def get_cpu():
    try:
        cpu = executar_powershell("(Get-CimInstance Win32_Processor | Select-Object -First 1).Name")

        if cpu and cpu != "-":
            return cpu

        return platform.processor() or "-"

    except Exception:
        return "-"


def coletar_dados(config):
    disco_total, disco_livre, disco_percentual = get_disco()

    fabricante = executar_powershell("(Get-CimInstance Win32_ComputerSystem).Manufacturer")
    modelo = executar_powershell("(Get-CimInstance Win32_ComputerSystem).Model")
    serial = executar_powershell("(Get-CimInstance Win32_BIOS).SerialNumber")
    sistema = executar_powershell("(Get-CimInstance Win32_OperatingSystem).Caption")

    return {
        "hostname": get_hostname(),
        "usuario": get_usuario_logado(),
        "ip_local": get_ip(),
        "mac": get_mac(),
        "sistema": sistema,
        "cpu": get_cpu(),
        "ram": f"{round(psutil.virtual_memory().total / 1024**3, 2)} GB",
        "disco_total": f"{disco_total} GB",
        "disco_livre": f"{disco_livre} GB",
        "disco_percentual": f"{disco_percentual}%",
        "fabricante": fabricante,
        "modelo": modelo,
        "serial": serial,
        "agent_version": config["agent_version"],
    }


def enviar_heartbeat(config, logger):
    dados = coletar_dados(config)
    url = montar_url_heartbeat(config)

    try:
        resposta = requests.post(
            url,
            json=dados,
            timeout=config["request_timeout"],
        )
        resposta.raise_for_status()
        logger.info(
            "%s -> %s | %s",
            dados["hostname"],
            resposta.status_code,
            resposta.text[:500],
        )
        return True

    except Exception as erro:
        logger.exception("Falha ao enviar heartbeat para %s: %s", url, erro)
        return False


def executar_loop(config, logger, stop_event=None):
    logger.info(
        "GSF Agent %s iniciado. Servidor: %s | Intervalo: %ss",
        config["agent_version"],
        montar_url_heartbeat(config),
        config["interval"],
    )

    while True:
        enviar_heartbeat(config, logger)

        if stop_event and stop_event.wait(config["interval"]):
            break

        if not stop_event:
            time.sleep(config["interval"])

    logger.info("GSF Agent encerrado.")


def instalar_servico_windows(config_path=None):
    try:
        import win32serviceutil
    except ImportError:
        print("pywin32 não está instalado. Instale com: pip install pywin32")
        return 1

    args = ["install"]

    if config_path:
        args.extend(["--startup", "auto", "--config", config_path])
    else:
        args.extend(["--startup", "auto"])

    win32serviceutil.HandleCommandLine(GSFAgentService, argv=[sys.argv[0], *args])
    return 0


try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil

    class GSFAgentService(win32serviceutil.ServiceFramework):
        _svc_name_ = "GSFAgent"
        _svc_display_name_ = "GSF Agent"
        _svc_description_ = "Agente de inventário e heartbeat da GSF Hub."

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.config = carregar_config()
            self.logger = configurar_logging(self.config)

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):
            servicemanager.LogInfoMsg("GSF Agent iniciado.")
            executar_loop(self.config, self.logger, stop_event=_Win32StopEvent(self.stop_event))

    class _Win32StopEvent:
        def __init__(self, stop_event):
            self.stop_event = stop_event

        def wait(self, timeout):
            resultado = win32event.WaitForSingleObject(self.stop_event, int(timeout * 1000))
            return resultado == win32event.WAIT_OBJECT_0

except ImportError:
    GSFAgentService = None


def main():
    parser = argparse.ArgumentParser(description="GSF Agent")
    parser.add_argument("--config", help="Caminho do config.json")
    parser.add_argument("--once", action="store_true", help="Executa um heartbeat e encerra")
    parser.add_argument("--service", action="store_true", help="Executa como serviço Windows via pywin32")
    parser.add_argument("--install-service", action="store_true", help="Instala o serviço Windows via pywin32")
    args, service_args = parser.parse_known_args()

    if args.install_service:
        return instalar_servico_windows(args.config)

    if args.service:
        if GSFAgentService is None:
            print("pywin32 não está instalado. Use modo console ou instale pywin32.")
            return 1

        import win32serviceutil
        win32serviceutil.HandleCommandLine(GSFAgentService, argv=[sys.argv[0], *service_args])
        return 0

    config = carregar_config(args.config)
    logger = configurar_logging(config)

    if args.once:
        return 0 if enviar_heartbeat(config, logger) else 1

    try:
        executar_loop(config, logger)
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
