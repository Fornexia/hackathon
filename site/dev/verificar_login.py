"""Diagnóstico de cadastro, login e perfis em um ambiente descartável.

    python site/dev/verificar_login.py

Usa PHP, Docker e MariaDB reais. Não cria contas no site atual nem envia e-mails externos.
O cadastro agora exige verificação; a antiga conta comum fixa deixou de ser criada por este script.
"""
from pathlib import Path
import subprocess
import sys


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print("Este diagnóstico usa somente um banco descartável; não recebe mais URL do site.")
        sys.exit(2)
    sys.exit(subprocess.call([sys.executable, "-X", "utf8", str(Path(__file__).with_name("test_auth.py")),
                              "test_auth", "test_api.TestA03Login", "test_api.TestA09Admin"]))
