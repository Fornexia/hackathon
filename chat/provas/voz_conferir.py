"""Mostra o que o bot faria com uma nota de voz, SEM WhatsApp e SEM chamar modelo (nenhum token gasto).

    python chat/provas/voz_conferir.py caminho/do/audio.ogg [outro.ogg ...]

Transcreve com o mesmo caminho do worker (inferencia/.venv, Whisper) e aplica a mesma conferência do CNPJ falado (chat/voz.py). Imprime, para cada arquivo:
o que foi ouvido, quanto tempo levou e se o bot CONSULTARIA (com o eco "Entendi") ou pediria para DIGITAR o CNPJ.

As notas que o gateway recebe ficam na pasta `midia/` do estado do WhatsApp (fora do repositório; `python chat/provas/whatsapp_preparar.py` mostra o caminho).
"""
import sys
import time
from pathlib import Path

CHAT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CHAT))
import voz  # noqa: E402
import worker  # noqa: E402


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")      # o console do Windows (cp1252) não imprime o emoji do eco
    if not argv:
        print(__doc__)
        return 1
    if not worker.PYTHON_AUDIO.exists():
        print("inferencia/.venv não existe: python -m venv inferencia/.venv e pip install -r inferencia/requirements-voz.txt")
        return 1
    saida = 0
    for caminho in argv:
        if not Path(caminho).is_file():
            print(f"{caminho}: arquivo não existe")
            saida = 1
            continue
        t = time.monotonic()
        texto = worker.transcrever(caminho)
        segundos = time.monotonic() - t
        print(f"\n{caminho}  ({segundos:.1f} s)")
        if not texto:
            print("  OUVI:  (nada: a transcrição falhou)")
            print("  BOT:   \"Não consegui entender o áudio. Pode mandar por texto?\"")
            saida = 1
            continue
        print(f"  OUVI:  {texto}")
        problema = voz.conferir_cnpj_falado(texto)
        if problema:
            print(f"  BOT:   NÃO consulta. {problema}; pede para digitar o CNPJ")
        else:
            print(f"  BOT:   CONSULTA e responde começando por: {voz.eco(texto).strip()}")
    return saida


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
