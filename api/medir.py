"""Resumo do uso da API, por porta, a partir de logs/api.jsonl: é com estes números que se decide entre REST, MCP e pergunta.

    python api/medir.py                       # tudo o que há no log
    python api/medir.py --desde 2026-11-18    # a partir de uma data
    python api/medir.py --cliente demo-lucas

Para cada porta (rest, mcp, pergunta): chamadas, taxa de erro (status 400 ou mais), tempo mediano e p95, e, na pergunta, tokens e
custo em dólar (só o que o provedor informou: nada é estimado). Lê também os arquivos girados (api.jsonl.1 ...).
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "consulta"))
import registro  # noqa: E402


def p95(valores: list[float]) -> float:
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int(0.95 * len(ordenados)))]


def ler(pasta: Path, desde: str | None, cliente: str | None) -> list[dict]:
    linhas = []
    for arquivo in sorted(pasta.glob("api.jsonl*")):
        for texto in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(texto)
            except ValueError:
                continue
            if r.get("evento") != "requisicao" or "porta" not in r:
                continue
            if desde and r.get("ts", "")[:10] < desde:
                continue
            if cliente and r.get("cliente") != cliente:
                continue
            linhas.append(r)
    return linhas


def resumo(linhas: list[dict]) -> list[dict]:
    saida = []
    for porta in ("rest", "mcp", "pergunta"):
        rs = [r for r in linhas if r["porta"] == porta]
        if not rs:
            continue
        ms = [r["duracao_ms"] for r in rs if isinstance(r.get("duracao_ms"), (int, float))]
        erros = sum(1 for r in rs if r.get("status", 0) >= 400)
        item = {"porta": porta, "chamadas": len(rs), "erros": erros, "taxa_de_erro": round(100 * erros / len(rs), 1),
                "mediana_ms": round(statistics.median(ms)) if ms else None, "p95_ms": round(p95(ms)) if ms else None}
        if porta == "pergunta":
            custos = [r["custo_usd"] for r in rs if isinstance(r.get("custo_usd"), (int, float))]
            item["custo_total_usd"] = round(sum(custos), 4)
            item["custo_medio_usd"] = round(sum(custos) / len(custos), 4) if custos else None
            item["perguntas_sem_custo_informado"] = len(rs) - len(custos)
            item["tokens_entrada_medio"] = round(statistics.mean(r["tokens_entrada"] for r in rs if r.get("tokens_entrada") is not None)) \
                if any(r.get("tokens_entrada") is not None for r in rs) else None
            item["fontes_medias"] = round(statistics.mean(r.get("fontes", 0) for r in rs), 1)
        saida.append(item)
    return saida


def main(argv: list[str]) -> int:
    for fluxo in (sys.stdout, sys.stderr):          # o console do Windows usa cp1252 e quebra a acentuação
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", help="AAAA-MM-DD")
    ap.add_argument("--cliente")
    ap.add_argument("--pasta", help="pasta dos logs (padrão: a do projeto)")
    a = ap.parse_args(argv)
    pasta = Path(a.pasta) if a.pasta else registro.pasta()
    linhas = ler(pasta, a.desde, a.cliente)
    if not linhas:
        print(f"nenhuma requisição registrada em {pasta / 'api.jsonl'}")
        return 0
    print(f"{'porta':10} {'chamadas':>9} {'erros':>6} {'erro %':>7} {'mediana':>9} {'p95':>9}")
    for r in resumo(linhas):
        print(f"{r['porta']:10} {r['chamadas']:>9} {r['erros']:>6} {r['taxa_de_erro']:>7} {str(r['mediana_ms']) + ' ms':>9} {str(r['p95_ms']) + ' ms':>9}")
        if r["porta"] == "pergunta":
            print(f"           custo total US$ {r['custo_total_usd']}, médio por pergunta US$ {r['custo_medio_usd']}, "
                  f"entrada média {r['tokens_entrada_medio']} tokens, fontes por resposta {r['fontes_medias']}"
                  + (f"  ({r['perguntas_sem_custo_informado']} sem custo informado)" if r["perguntas_sem_custo_informado"] else ""))
    por_tool: dict[str, list[float]] = {}
    for r in linhas:
        if r["porta"] == "rest" and r.get("tool") and isinstance(r.get("duracao_ms"), (int, float)):
            por_tool.setdefault(r["tool"], []).append(r["duracao_ms"])
    if por_tool:
        print("\nREST por consulta:")
        for tool, ms in sorted(por_tool.items(), key=lambda kv: -len(kv[1])):
            print(f"  {tool:26} {len(ms):>4} chamadas, mediana {round(statistics.median(ms))} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
