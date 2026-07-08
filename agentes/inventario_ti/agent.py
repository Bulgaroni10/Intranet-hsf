import requests
import socket
import platform
import psutil
import time
import uuid
import subprocess

SERVER = "http://127.0.0.1:8000/api/heartbeat/"
AGENT_VERSION = "2.0.0"


def executar_powershell(comando):
    try:
        resultado = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                comando
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        saida = resultado.stdout.strip()

        if saida:
            return saida

        return "-"

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
        usuario = executar_powershell(
            "(Get-CimInstance Win32_ComputerSystem).UserName"
        )

        if not usuario or usuario == "-":
            return "-"

        if usuario.endswith("$"):
            return "-"

        usuario = usuario.replace("\\", "/")

        return usuario

    except Exception:
        return "-"


def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
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
        cpu = executar_powershell(
            "(Get-CimInstance Win32_Processor | Select-Object -First 1).Name"
        )

        if cpu and cpu != "-":
            return cpu

        return platform.processor()

    except Exception:
        return "-"


def coletar_dados():
    disco_total, disco_livre, disco_percentual = get_disco()

    fabricante = executar_powershell(
        "(Get-CimInstance Win32_ComputerSystem).Manufacturer"
    )

    modelo = executar_powershell(
        "(Get-CimInstance Win32_ComputerSystem).Model"
    )

    serial = executar_powershell(
        "(Get-CimInstance Win32_BIOS).SerialNumber"
    )

    sistema = executar_powershell(
        "(Get-CimInstance Win32_OperatingSystem).Caption"
    )

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
        "agent_version": AGENT_VERSION
    }


def enviar():
    dados = coletar_dados()

    try:
        resposta = requests.post(
            SERVER,
            json=dados,
            timeout=8
        )

        print(
            f"[OK] {dados['hostname']} -> {resposta.status_code} | {resposta.text}"
        )

    except Exception as erro:
        print(f"[ERRO] Falha ao enviar heartbeat: {erro}")


if __name__ == "__main__":
    while True:
        enviar()
        time.sleep(30)