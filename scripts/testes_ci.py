"""Executa os mesmos testes gratuitos no CI e no ensaio local, sem iniciar worker ou modelo.

Os bancos e a configuracao local devem estar preparados antes. O runner do GitHub
usa bancos descartaveis; localmente, pare o worker antes de executar este script.
"""

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SUITES = (
    ("Consulta", ("-m", "unittest", "discover", "-s", "consulta/testes")),
    ("Chat", ("-m", "unittest", "discover", "-s", "chat/testes")),
    ("API", ("site/dev/test_api.py",)),
    ("Pacote de prova", ("site/dev/test_prova.py",)),
)


def main() -> int:
    resultados = []
    ambiente = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    for nome, argumentos in SUITES:
        comando = [sys.executable, "-X", "utf8", *argumentos]
        print(f"\n=== {nome}: {' '.join(comando)} ===", flush=True)
        resultado = subprocess.run(comando, cwd=RAIZ, env=ambiente)
        resultados.append((nome, resultado.returncode))
        if resultado.returncode:
            break

    resumo = "| Suite | Resultado |\n|---|---|\n" + "\n".join(
        f"| {nome} | {'OK' if codigo == 0 else f'FALHOU (exit {codigo})'} |"
        for nome, codigo in resultados
    )
    if len(resultados) < len(SUITES):
        resumo += "\n\nSuites seguintes nao executadas apos a falha."
    print("\n" + resumo, flush=True)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as arquivo:
            arquivo.write("## Testes gratuitos\n\n" + resumo + "\n")
    return 1 if any(codigo for _, codigo in resultados) else 0


if __name__ == "__main__":
    sys.exit(main())
