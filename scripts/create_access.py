"""Create a deployment-only htpasswd file without exposing passwords in arguments."""

import getpass
import os
from pathlib import Path
import re
import shutil
import subprocess


def main() -> None:
    username = input("Usuario autorizado: ").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", username):
        raise SystemExit(
            "Usa entre 3 y 64 letras, números, puntos, guiones o guiones bajos."
        )
    password = getpass.getpass("Contraseña (mínimo 16 caracteres): ")
    if len(password) < 16 or password != getpass.getpass("Repite la contraseña: "):
        raise SystemExit("La contraseña es corta o no coincide.")
    destination = Path(__file__).resolve().parents[1] / "secrets" / "payroll.htpasswd"
    if destination.exists():
        raise SystemExit(
            "El archivo ya existe. Administra usuarios con htpasswd; no se sobrescribió."
        )
    executable = shutil.which("htpasswd")
    if not executable:
        raise SystemExit("Instala htpasswd (apache2-utils en Debian/Ubuntu).")
    command = [executable, "-niB", username]
    try:
        result = subprocess.run(
            command, input=password + "\n", capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit(
            "No se pudo ejecutar htpasswd. Revisa su instalación y vuelve a intentarlo."
        ) from None
    hashed = result.stdout.strip()
    if not hashed.startswith(username + ":$2"):
        raise SystemExit("No se pudo generar un hash bcrypt válido.")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as output:
        output.write(hashed + "\n")
    if os.name == "posix":
        destination.parent.chmod(0o700)
        destination.chmod(0o600)
    print(
        "Credenciales guardadas en secrets/payroll.htpasswd. No las subas al repositorio."
    )


if __name__ == "__main__":
    main()
