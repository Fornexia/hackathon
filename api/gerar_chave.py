"""Gera uma chave de API para um cliente. A chave aparece UMA vez; o arquivo guarda só o hash.

    python api/gerar_chave.py demo-cliente estado
    python api/gerar_chave.py demo-cliente estado --por-minuto 30 --perguntas-dia 10
    python api/gerar_chave.py --perfis                      # perfis que a API aceita

Para revogar, ponha "ativo": false na entrada do cliente em api/chaves.json (vale sem reiniciar a API).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chaves  # noqa: E402


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):          # o console do Windows usa cp1252 e quebra a acentuação
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cliente", nargs="?")
    ap.add_argument("perfil", nargs="?")
    ap.add_argument("--por-minuto", type=int, default=chaves.LIMITE_MINUTO_PADRAO)
    ap.add_argument("--perguntas-dia", type=int, default=chaves.PERGUNTAS_DIA_PADRAO)
    ap.add_argument("--perfis", action="store_true", help="lista os perfis que a API aceita")
    a = ap.parse_args()
    todos = chaves.perfis.carregar()
    if a.perfis or not (a.cliente and a.perfil):
        for nome, p in todos.items():
            print(f"{nome:16} {', '.join(p['tenants'])}" + ("   (recusado: dado pessoal)" if p["ver_pessoal"] else ""))
        return 0 if a.perfis else 1
    try:
        chave = chaves.Chaves().gerar(a.cliente, a.perfil, a.por_minuto, a.perguntas_dia)
    except ValueError as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(f"Chave de '{a.cliente}' (perfil {a.perfil}). Guarde agora, ela não será mostrada de novo:\n\n  {chave}\n")
    print("Uso:  Authorization: Bearer <chave>   (ou o cabeçalho X-API-Key)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
