"""Sincroniza os tokens MCP gerados na página da conta do site com as chaves da API (api/chaves.json).

O site guarda só o hash de cada token e sabe o plano de cada conta. Este processo busca a lista pela rota protegida do worker
(GET /api/worker/tokens, com X-Worker-Key, a mesma porta de saída que o worker usa para os telefones) e grava no arquivo de
chaves, que a API relê sozinha quando ele muda. Nenhuma porta é aberta neste computador para o site.

- O perfil sai dos entes do plano: o perfil de consulta/perfis.json com exatamente esses entes e sem dado pessoal.
  Plano sem perfil correspondente fica de fora (a API recusaria a chave inteira).
- Chaves criadas à mão (api/gerar_chave.py) ficam como estão; só as de origem "site" são trocadas a cada rodada.
- Se o site não responder, o arquivo atual é mantido: uma queda do site não derruba quem já usa o MCP.

    python api/sincronizar_tokens.py            # laço a cada 15 s
    python api/sincronizar_tokens.py --uma-vez  # uma rodada
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for linha in ((RAIZ / ".env").read_text(encoding="utf-8-sig").splitlines() if (RAIZ / ".env").exists() else []):
    linha = linha.strip()
    if linha and not linha.startswith("#") and "=" in linha:
        k, v = linha.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
sys.path.insert(0, str(RAIZ / "consulta"))
sys.path.insert(0, str(RAIZ / "api"))
import perfis  # noqa: E402
from chaves import ARQUIVO_PADRAO  # noqa: E402

INTERVALO_S = 15
LIMITE_POR_MINUTO = 60
PERGUNTAS_POR_DIA = 30
HEX = set("0123456789abcdef")


def perfil_dos_entes(tenants: list, todos: dict) -> str | None:
    alvo = set(tenants)
    for nome, p in todos.items():
        if not p["ver_pessoal"] and set(p["tenants"]) == alvo:
            return nome
    return None


def montar(tokens: list, atual: dict, todos: dict) -> dict:
    """As chaves que não vieram do site, mais uma entrada por token ativo do site com perfil conhecido."""
    novo = {h: e for h, e in atual.items() if e.get("origem") != "site"}
    for t in tokens:
        h = t.get("hash") if isinstance(t, dict) else None
        if not (isinstance(h, str) and len(h) == 64 and set(h) <= HEX) or h in novo:
            continue
        perfil = perfil_dos_entes(t.get("tenants") or [], todos)
        if perfil is None:
            continue
        novo[h] = {"cliente": f"site-conta-{int(t.get('usuario_id') or 0)}", "perfil": perfil, "limite_por_minuto": LIMITE_POR_MINUTO,
                   "perguntas_por_dia": PERGUNTAS_POR_DIA, "ativo": True, "origem": "site"}
    return novo


def buscar(api: str, chave: str) -> list:
    req = urllib.request.Request(api + "/worker/tokens", headers={"X-Worker-Key": chave, "User-Agent": "fornexia-tokens/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        dados = json.loads(r.read().decode("utf-8"))
    if not isinstance(dados, list):
        raise ValueError("resposta inesperada do site")
    return dados


def gravar_se_mudou(arquivo: Path, novo: dict) -> bool:
    try:
        atual = json.loads(arquivo.read_text(encoding="utf-8") or "{}") if arquivo.exists() else None
    except ValueError:
        atual = None
    if atual == novo:
        return False
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    tmp = arquivo.with_suffix(".tmp")
    tmp.write_text(json.dumps(novo, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, arquivo)
    return True


def rodada(arquivo: Path, api: str, chave: str) -> tuple[bool, int]:
    tokens = buscar(api, chave)
    atual = json.loads(arquivo.read_text(encoding="utf-8") or "{}") if arquivo.exists() else {}
    novo = montar(tokens, atual, perfis.carregar())
    return gravar_se_mudou(arquivo, novo), sum(1 for e in novo.values() if e.get("origem") == "site")


def main() -> int:
    arquivo = Path(os.environ.get("API_CHAVES") or ARQUIVO_PADRAO)
    api = os.environ.get("API_BASE", f"https://{os.environ.get('SITE', 'fornexia.figueiredo.dev')}") + "/api"
    chave = os.environ.get("WORKER_KEY", "")
    if len(chave) < 24:
        print("defina WORKER_KEY (a mesma do site) no .env", file=sys.stderr)
        return 1
    while True:
        try:
            mudou, n = rodada(arquivo, api, chave)
            if mudou:
                print(time.strftime("%H:%M:%S"), f"tokens do site atualizados: {n} ativos", flush=True)
        except (OSError, ValueError, urllib.error.URLError) as e:
            print(time.strftime("%H:%M:%S"), "tokens: rodada falhou, mantive o arquivo atual:", type(e).__name__, str(e)[:120], flush=True)
            if "--uma-vez" in sys.argv:
                return 1
        if "--uma-vez" in sys.argv:
            return 0
        time.sleep(INTERVALO_S)


if __name__ == "__main__":
    sys.exit(main())
