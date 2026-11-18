"""API da FornexIA para ser consumida por IAs de terceiros: três portas sobre o mesmo núcleo.

    A. REST      GET  /v1/...            dados estruturados (JSON), as mesmas consultas do agente
    B. MCP       POST /mcp               as mesmas consultas como tools MCP (Streamable HTTP, sem sessão)
    C. Pergunta  POST /v1/perguntar      pergunta em português, resposta pronta com as fontes (chama o agente, custa modelo)

Subir (demonstração, fora da internet aberta):

    python api/gerar_chave.py demo-cliente estado
    python api/servidor.py --host 127.0.0.1 --porta 8088

Regras que valem nas três portas:
  - O perfil de acesso sai da CHAVE (api/chaves.py), guardada no servidor. Nunca de um parâmetro: nem de URL, nem de corpo, nem de
    tool, nem de pergunta. Sem chave válida, 401. Chave de perfil com dado pessoal não existe (recusada ao carregar).
  - As consultas são as de consulta/mcp_transparencia.py, as mesmas do agente: perfil, validação de entrada, limite de linhas
    e registro por chamada. Esta API não escreve consulta nova ao grafo.
  - Limite por minuto (todas as portas) e teto diário de perguntas (porta C, que paga modelo).
  - Cada requisição vira uma linha em logs/api.jsonl (cliente, perfil, rota, status, duração; na pergunta, modelo, tokens e custo).
    Chave e texto da pergunta nunca vão para o log.
  - Erro interno nunca devolve detalhe do servidor (caminho de arquivo, pilha, mensagem do banco).
"""

import argparse
import asyncio
import contextlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for pasta in ("consulta", "chat", "api"):
    sys.path.insert(0, str(RAIZ / pasta))

import registro  # noqa: E402
import mcp_transparencia as nucleo  # noqa: E402
from mcp.server.transport_security import TransportSecuritySettings  # noqa: E402
from starlette.applications import Starlette  # noqa: E402
from starlette.concurrency import run_in_threadpool  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402
from starlette.routing import Mount, Route  # noqa: E402

from chaves import Chaves  # noqa: E402
from limites import Limites  # noqa: E402

VERSAO = "0.1.0-demo"
PERGUNTA_MAX = 500            # o mesmo limite do chat do site
HISTORICO_MAX = 6             # turnos anteriores aceitos
HISTORICO_TEXTO_MAX = 800
CORPO_MAX = 20_000
PERGUNTAS_DIA_TOTAL = int(os.environ.get("API_PERGUNTAS_DIA_TOTAL", "200"))
PERGUNTAS_SIMULTANEAS = int(os.environ.get("API_PERGUNTAS_SIMULTANEAS", "2"))
ESPERA_VAGA_S = 5


def _log(evento: str, nivel: str = "info", request_id: str | None = None, **campos) -> None:
    try:
        registro.registrar("api", evento, nivel, request_id=request_id, **campos)
    except Exception:  # noqa: BLE001  o log nunca derruba uma requisição
        pass


def _agora_ms() -> float:
    return time.perf_counter() * 1000


# ---------- rotas de dados (porta A): uma tabela, usada para registrar as rotas E para gerar o OpenAPI ----------

def _q(request, obrigatorio: bool) -> str:
    q = (request.query_params.get("q") or "").strip()
    if obrigatorio and not q:
        raise ValueError("informe o parâmetro q")
    return q


ROTAS_DE_DADOS = [
    # caminho, nome da tool no núcleo, resumo, parâmetros (nome, onde, obrigatório, descrição), como extrair os argumentos
    ("/v1/cobertura", "cobertura", "O que existe na base para o perfil da chave, de quando é e o que falta. Chame antes de dizer que algo não existe.",
     [], lambda r: ()),
    ("/v1/fornecedores", "buscar_fornecedor", "Busca fornecedor por parte do nome (razão social ou fantasia) ou por CNPJ. Devolve o id usado nas outras rotas.",
     [("q", "query", True, "Nome ou CNPJ (até 100 caracteres)")], lambda r: (_q(r, True),)),
    ("/v1/contratos", "buscar_contratos", "Sem q: os 50 maiores contratos do perfil. Com q: busca por parte do objeto ou do órgão.",
     [("q", "query", False, "Parte do objeto ou do órgão")], None),     # tratada à parte: duas tools
    ("/v1/fornecedores/{fornecedor_id}/contratos", "contratos_do_fornecedor", "Contratos do fornecedor, com a evidência de cada um.",
     [("fornecedor_id", "path", True, "Id devolvido por /v1/fornecedores, por exemplo cnpj:11111111000111")],
     lambda r: (r.path_params["fornecedor_id"],)),
    ("/v1/fornecedores/{fornecedor_id}/sancoes", "sancoes_do_fornecedor", "Sanções do fornecedor nos cadastros dos entes do perfil. Sanção em aberto não prova irregularidade.",
     [("fornecedor_id", "path", True, "Id do fornecedor")], lambda r: (r.path_params["fornecedor_id"],)),
    ("/v1/fornecedores/{fornecedor_id}/cadastro", "cadastro_do_fornecedor", "Cadastro de CNPJ da Receita, se foi coletado. Lista vazia = não coletado, não 'CNPJ inexistente'.",
     [("fornecedor_id", "path", True, "Id do fornecedor")], lambda r: (r.path_params["fornecedor_id"],)),
    ("/v1/fornecedores/{fornecedor_id}/execucao", "execucao_do_fornecedor", "Empenhado, liquidado, pago e restos a pagar por órgão e ano. Não se liga a um contrato.",
     [("fornecedor_id", "path", True, "Id do fornecedor"), ("ano", "query", False, "Quatro dígitos, por exemplo 2025")],
     lambda r: (r.path_params["fornecedor_id"], r.query_params.get("ano") or "")),
    ("/v1/evidencias/{evidencia_id}", "conferir_evidencia", "Abre a prova: trecho literal da fonte, endereço, data da captura e se o arquivo guardado ainda bate com o hash.",
     [("evidencia_id", "path", True, "Id da evidência devolvido pelas outras rotas")], lambda r: (r.path_params["evidencia_id"],)),
]


def _json(status: int, corpo: dict, rid: str | None = None, extra: dict | None = None) -> JSONResponse:
    cab = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", **(extra or {})}
    if rid:
        cab["X-Request-Id"] = rid
    return JSONResponse(corpo, status_code=status, headers=cab)


def _token(request) -> str:
    h = request.headers.get("authorization", "")
    return h[7:].strip() if h[:7].lower() == "bearer " else request.headers.get("x-api-key", "").strip()


def _entrada(request):
    """Chave válida e dentro do limite por minuto. Devolve (cliente, rid, None) ou (None, rid, resposta de erro)."""
    est = request.app.state.estado
    rid = f"api:{uuid.uuid4().hex[:10]}"
    cliente = est.chaves.autenticar(_token(request))
    if cliente is None:
        _log("recusada", "aviso", rid, motivo="chave ausente ou inválida", rota=request.url.path[:120])
        return None, rid, _json(401, {"erro": "chave de API ausente ou inválida"}, rid, {"WWW-Authenticate": 'Bearer realm="fornexia"'})
    request.scope["fx_cliente"] = cliente
    espera = est.limites.requisicao(cliente.id, cliente.limite_por_minuto)
    if espera:
        _log("limitada", "aviso", rid, cliente=cliente.id, rota=request.url.path[:120])
        return None, rid, _json(429, {"erro": "limite de requisições por minuto atingido", "tente_novamente_em_s": espera}, rid,
                                {"Retry-After": str(espera)})
    return cliente, rid, None


async def _executar(cliente, rid: str, funcao, *args):
    """Roda a consulta numa thread, com o perfil da chave. O perfil é posto DENTRO da thread, não herdado de fora."""
    def dentro():
        with nucleo.com_perfil(cliente.perfil, list(cliente.tenants), False, rid):
            return funcao(*args)
    return await run_in_threadpool(dentro)


def _publica(evidencia: dict) -> dict:
    """A prova sem caminho do servidor: `arquivo` vira só o nome, e CPF no trecho é mascarado."""
    d = dict(evidencia)
    if d.get("arquivo"):
        d["arquivo"] = Path(str(d["arquivo"]).replace("\\", "/")).name
    if d.get("trecho"):
        d["trecho"] = nucleo.CPF.sub("[CPF]", str(d["trecho"]))[:1500]
    return d


def _rota_de_dados(nome_tool: str, extrair):
    async def tratador(request):
        cliente, rid, erro = _entrada(request)
        if erro:
            return erro
        t0 = _agora_ms()
        status, corpo = 200, {}
        try:
            if nome_tool == "buscar_contratos":              # /v1/contratos: sem q lista, com q busca
                q = _q(request, False)
                dados = await _executar(cliente, rid, nucleo.buscar_contratos if q else nucleo.listar_contratos, *((q,) if q else ()))
            else:
                dados = await _executar(cliente, rid, getattr(nucleo, nome_tool), *extrair(request))
            if nome_tool == "conferir_evidencia":
                if "erro" in dados:
                    status, corpo = 404, {"erro": dados["erro"]}
                else:
                    corpo = {"perfil": cliente.perfil, "dados": _publica(dados)}
            else:
                corpo = {"perfil": cliente.perfil, "resultados": len(dados) if isinstance(dados, list) else 1, "dados": dados}
        except ValueError as e:                              # nossa validação de entrada: a mensagem é segura e ajuda quem chama
            status, corpo = 400, {"erro": str(e)}
        except Exception as e:  # noqa: BLE001
            _log("falha", "erro", rid, cliente=cliente.id, tool=nome_tool, tipo=type(e).__name__)
            status, corpo = 500, {"erro": "falha interna ao consultar"}
        _log("requisicao", "info" if status < 400 else "aviso", rid, cliente=cliente.id, perfil=cliente.perfil, porta="rest",
             tool=nome_tool, status=status, duracao_ms=round(_agora_ms() - t0))
        return _json(status, corpo, rid)
    return tratador


# ---------- porta C: pergunta em português ----------

def _historico(bruto) -> list[tuple[str, str]]:
    if bruto in (None, []):
        return []
    if not isinstance(bruto, list) or len(bruto) > HISTORICO_MAX:
        raise ValueError(f"historico: lista de até {HISTORICO_MAX} turnos")
    saida = []
    for t in bruto:
        if not (isinstance(t, dict) and isinstance(t.get("pergunta"), str) and isinstance(t.get("resposta"), str)):
            raise ValueError("historico: cada turno precisa de 'pergunta' e 'resposta' (textos)")
        if len(t["pergunta"]) > PERGUNTA_MAX or len(t["resposta"]) > HISTORICO_TEXTO_MAX:
            raise ValueError("historico: turno longo demais")
        saida.append((t["pergunta"], t["resposta"]))
    return saida


def _executar_pergunta(ag, cliente, rid: str, pergunta: str, historico):
    leitor = ag.Leitor()
    fontes, falha, trocas = [], None, 0
    for tipo, dados in ag.perguntar(pergunta, list(cliente.tenants), historico, leitor, request_id=rid):
        if tipo == "fonte":
            fontes.append(dados)
        elif tipo == "erro":
            falha = dados
        elif tipo == "fallback":
            trocas += 1
    return leitor, fontes, falha, trocas


async def perguntar(request):
    est = request.app.state.estado
    cliente, rid, erro = _entrada(request)
    if erro:
        return erro
    t0 = _agora_ms()
    corpo_bruto = await request.body()
    if len(corpo_bruto) > CORPO_MAX:
        return _json(413, {"erro": "corpo grande demais"}, rid)
    try:
        corpo = json.loads(corpo_bruto or b"{}")
        pergunta = corpo.get("pergunta") if isinstance(corpo, dict) else None
        if not isinstance(pergunta, str) or not pergunta.strip():
            raise ValueError("informe 'pergunta' (texto)")
        pergunta = pergunta.strip()
        if len(pergunta) > PERGUNTA_MAX:
            raise ValueError(f"pergunta longa demais (máximo {PERGUNTA_MAX} caracteres)")
        historico = _historico(corpo.get("historico"))
    except (ValueError, json.JSONDecodeError) as e:
        return _json(400, {"erro": str(e) if isinstance(e, ValueError) and not isinstance(e, json.JSONDecodeError) else "corpo não é JSON válido"}, rid)
    motivo = est.limites.reservar_pergunta(cliente.id, cliente.perguntas_por_dia, PERGUNTAS_DIA_TOTAL)
    if motivo:
        _log("limitada", "aviso", rid, cliente=cliente.id, motivo=motivo, rota="/v1/perguntar")
        return _json(429, {"erro": motivo}, rid)
    try:
        await asyncio.wait_for(est.vaga.acquire(), ESPERA_VAGA_S)
    except asyncio.TimeoutError:
        return _json(503, {"erro": "assistente ocupado, tente de novo em instantes"}, rid, {"Retry-After": "10"})
    try:
        leitor, fontes, falha, trocas = await run_in_threadpool(_executar_pergunta, est.agente(), cliente, rid, pergunta, historico)
    except Exception as e:  # noqa: BLE001
        _log("falha", "erro", rid, cliente=cliente.id, rota="/v1/perguntar", tipo=type(e).__name__)
        return _json(500, {"erro": "falha interna ao responder"}, rid)
    finally:
        est.vaga.release()
    uso = {k: leitor.uso[k] for k in ("entrada", "saida", "custo_usd") if k in (leitor.uso or {})}
    ms = round(_agora_ms() - t0)
    status = 200 if (falha is None and leitor.resposta) else 502
    _log("requisicao", "info" if status == 200 else "erro", rid, cliente=cliente.id, perfil=cliente.perfil, porta="pergunta",
         status=status, duracao_ms=ms, modelo=leitor.modelo, trocas=trocas, fontes=len(fontes), consultas=len(leitor.consultas),
         tokens_entrada=uso.get("entrada"), tokens_saida=uso.get("saida"), custo_usd=uso.get("custo_usd"))
    if status != 200:
        return _json(502, {"erro": "não consegui concluir agora", "motivo": str((falha or {}).get("motivo", ""))[:120]}, rid)
    return _json(200, {"perfil": cliente.perfil, "resposta": leitor.resposta, "fontes": fontes, "modelo": leitor.modelo,
                       "duracao_ms": ms, "uso": uso}, rid)


# ---------- demais rotas ----------

async def saude(request):
    try:
        await run_in_threadpool(nucleo.driver.verify_connectivity)
        return _json(200, {"ok": True, "versao": VERSAO, "grafo": "ok"})
    except Exception:  # noqa: BLE001
        return _json(503, {"ok": False, "versao": VERSAO, "grafo": "indisponível"})


async def eu(request):
    cliente, rid, erro = _entrada(request)
    if erro:
        return erro
    est = request.app.state.estado
    return _json(200, {"cliente": cliente.id, "perfil": cliente.perfil, "nome_do_perfil": cliente.nome_do_perfil,
                       "entes": list(cliente.tenants), "limite_por_minuto": cliente.limite_por_minuto,
                       "perguntas_por_dia": cliente.perguntas_por_dia,
                       "perguntas_restantes_hoje": est.limites.restantes_hoje(cliente.id, cliente.perguntas_por_dia)}, rid)


def especificacao() -> dict:
    """OpenAPI 3.1 gerado da mesma tabela que registra as rotas: documentação e código não se separam."""
    erro = {"description": "Erro", "content": {"application/json": {"schema": {"type": "object", "properties": {"erro": {"type": "string"}}}}}}
    resp = {"200": {"description": "Resultado", "content": {"application/json": {"schema": {"type": "object"}}}},
            "400": erro, "401": erro, "429": erro}
    caminhos: dict = {}
    for caminho, tool, resumo, params, _ in ROTAS_DE_DADOS:
        caminhos[caminho] = {"get": {
            "operationId": tool, "summary": resumo, "security": [{"chave": []}],
            "parameters": [{"name": n, "in": onde, "required": obrig, "description": d, "schema": {"type": "string"}} for n, onde, obrig, d in params],
            "responses": resp}}
    caminhos["/v1/perguntar"] = {"post": {
        "operationId": "perguntar", "summary": "Pergunta em português; devolve a resposta pronta com as fontes. Gasta modelo: tem teto diário.",
        "security": [{"chave": []}],
        "requestBody": {"required": True, "content": {"application/json": {"schema": {
            "type": "object", "required": ["pergunta"], "properties": {
                "pergunta": {"type": "string", "maxLength": PERGUNTA_MAX},
                "historico": {"type": "array", "maxItems": HISTORICO_MAX, "items": {
                    "type": "object", "required": ["pergunta", "resposta"],
                    "properties": {"pergunta": {"type": "string"}, "resposta": {"type": "string"}}}}}}}}},
        "responses": {**resp, "502": erro, "503": erro}}}
    caminhos["/v1/me"] = {"get": {"operationId": "eu", "summary": "Perfil, entes visíveis e limites desta chave.", "security": [{"chave": []}], "responses": resp}}
    caminhos["/v1/saude"] = {"get": {"operationId": "saude", "summary": "O serviço e o grafo estão no ar? (sem chave)", "responses": {"200": {"description": "ok"}}}}
    caminhos["/mcp"] = {"post": {"operationId": "mcp", "summary": "Servidor MCP (Streamable HTTP, sem sessão): as mesmas consultas como tools. Cabeçalho Authorization: Bearer.",
                                 "security": [{"chave": []}], "responses": {"200": {"description": "Resposta JSON-RPC"}, "401": erro}}}
    return {"openapi": "3.1.0",
            "info": {"title": "FornexIA API", "version": VERSAO,
                     "description": "Histórico de fornecedor com prova, para IAs de terceiros. Dados de demonstração. O perfil de acesso vem da chave."},
            "components": {"securitySchemes": {"chave": {"type": "http", "scheme": "bearer"}}},
            "paths": caminhos}


async def openapi(request):
    return _json(200, especificacao())


# ---------- porta B: MCP com a mesma chave ----------

class AutenticaMCP:
    """ASGI: chave válida e limite por minuto, depois roda a tool com o perfil da chave. Sem sessão (stateless): cada requisição é independente."""

    def __init__(self, app, estado):
        self.app, self.estado = app, estado

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        cab = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        h = cab.get("authorization", "")
        token = h[7:].strip() if h[:7].lower() == "bearer " else cab.get("x-api-key", "").strip()
        cliente = self.estado.chaves.autenticar(token)
        rid = f"api:{uuid.uuid4().hex[:10]}"
        if cliente is None:
            _log("recusada", "aviso", rid, motivo="chave ausente ou inválida", porta="mcp")
            resp = _json(401, {"erro": "chave de API ausente ou inválida"}, rid, {"WWW-Authenticate": 'Bearer realm="fornexia"'})
            return await resp(scope, receive, send)
        scope["fx_cliente"] = cliente
        espera = self.estado.limites.requisicao(cliente.id, cliente.limite_por_minuto)
        if espera:
            resp = _json(429, {"erro": "limite de requisições por minuto atingido", "tente_novamente_em_s": espera}, rid, {"Retry-After": str(espera)})
            return await resp(scope, receive, send)
        with nucleo.com_perfil(cliente.perfil, list(cliente.tenants), False, rid):
            await self.app(scope, receive, send)


class Medidor:
    """ASGI externo: uma linha em logs/api.jsonl por requisição que NÃO é das rotas de dados (que já se registram com a tool)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/mcp"):
            return await self.app(scope, receive, send)
        t0, status = _agora_ms(), [0]

        async def enviar(msg):
            if msg["type"] == "http.response.start":
                status[0] = msg["status"]
            await send(msg)
        try:
            await self.app(scope, receive, enviar)
        finally:
            c = scope.get("fx_cliente")
            _log("requisicao", "info" if status[0] < 400 else "aviso", cliente=getattr(c, "id", None), perfil=getattr(c, "perfil", None),
                 porta="mcp", status=status[0], duracao_ms=round(_agora_ms() - t0))


class Estado:
    def __init__(self, chaves: Chaves, limites: Limites, agente=None):
        self.chaves, self.limites = chaves, limites
        self.vaga = asyncio.Semaphore(PERGUNTAS_SIMULTANEAS)
        self._agente = agente

    def agente(self):
        if self._agente is None:                  # import tardio: o agente só é carregado quando alguém faz uma pergunta
            import agente as modulo
            self._agente = modulo
        return self._agente


def _hosts_permitidos() -> list[str]:
    return [h.strip() for h in os.environ.get("API_HOSTS_PERMITIDOS", "127.0.0.1:*,localhost:*").split(",") if h.strip()]


def criar_app(chaves: Chaves | None = None, limites: Limites | None = None, agente=None) -> Starlette:
    estado = Estado(chaves or Chaves(), limites or Limites(), agente)
    mcp_app = nucleo.mcp.streamable_http_app(
        stateless_http=True, json_response=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=_hosts_permitidos(),
                                                     allowed_origins=[]))

    @contextlib.asynccontextmanager
    async def ciclo(_app):
        async with mcp_app.router.lifespan_context(mcp_app):
            yield

    rotas = [Route("/v1/saude", saude), Route("/v1/me", eu), Route("/openapi.json", openapi),
             Route("/v1/perguntar", perguntar, methods=["POST"])]
    for caminho, tool, _resumo, _params, extrair in ROTAS_DE_DADOS:
        rotas.append(Route(caminho, _rota_de_dados(tool, extrair)))
    rotas.append(Mount("/", app=AutenticaMCP(mcp_app, estado)))      # /mcp e o que sobrar: tudo atrás da chave
    app = Starlette(routes=rotas, lifespan=ciclo)
    app.state.estado = estado
    app.add_middleware(Medidor)
    return app


def main() -> int:
    import uvicorn
    ap = argparse.ArgumentParser(description="API da FornexIA (demonstração)")
    ap.add_argument("--host", default="127.0.0.1", help="endereço onde escuta (padrão: só esta máquina; use o IP do Tailscale para a VM)")
    ap.add_argument("--porta", type=int, default=8088)
    a = ap.parse_args()
    if not Chaves().arquivo.exists():
        print("aviso: não há api/chaves.json: toda requisição será recusada (401). Gere uma chave: python api/gerar_chave.py <cliente> <perfil>",
              file=sys.stderr)
    uvicorn.run(criar_app(), host=a.host, port=a.porta, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
