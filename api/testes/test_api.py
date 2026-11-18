"""Testes da API (api/servidor.py): chaves, limites, as três portas e, contra um Neo4j de verdade, o isolamento entre perfis.

    docker compose --env-file .env -f infra/docker-compose.yml up -d neo4j
    python coleta/carregar_neo4j.py --zerar --exemplo
    python -m unittest discover -s api/testes -v

Sem o banco no ar (ou sem os dados de exemplo), os testes que precisam dele são pulados e dizem por quê. Os demais não precisam de banco
nem de modelo: o agente é trocado por um falso, então nenhum teste gasta crédito.

O servidor sobe de verdade (uvicorn, numa porta livre) e é chamado por urllib, como site/dev/test_api.py faz com o PHP.
"""

import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
for k in ("TRANSPARENCIA_PERFIL", "TRANSPARENCIA_TENANTS", "TRANSPARENCIA_VER_PESSOAL"):
    os.environ.pop(k, None)             # o processo da API nunca nasce com um perfil: quem dá o perfil é a chave
os.environ["TRANSPARENCIA_LOG"] = str(Path(tempfile.gettempdir()) / "transparencia-testes-api.jsonl")
for pasta in ("api", "consulta", "chat"):
    sys.path.insert(0, str(RAIZ / pasta))

import uvicorn  # noqa: E402

import chaves as ch  # noqa: E402
import limites as lm  # noqa: E402
import servidor  # noqa: E402
import registro  # noqa: E402

C = "cnpj:33333333000133"      # Obras Exemplares: só existe no ente ex-estado (perfil estado-exemplo)
A = "cnpj:11111111000111"      # Construtora Exemplo: aparece em pe-garanhuns, pe-estado e ex-estado


def banco_disponivel() -> str | None:
    try:
        with servidor.nucleo.driver.session() as s:
            n = s.run("MATCH (e:Evidencia {id: 'g1'}) RETURN count(e) AS n").single()["n"]
    except Exception as erro:  # noqa: BLE001
        return f"Neo4j indisponível ({type(erro).__name__}). Suba o banco e rode coleta/carregar_neo4j.py --zerar --exemplo"
    return None if n else "Neo4j no ar, mas sem os dados de exemplo. Rode coleta/carregar_neo4j.py --zerar --exemplo"


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Servidor:
    def __init__(self, app):
        self.porta = porta_livre()
        self.base = f"http://127.0.0.1:{self.porta}"
        self.srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=self.porta, log_level="error"))
        self.t = threading.Thread(target=self.srv.run, daemon=True)
        self.t.start()
        for _ in range(100):
            if self.srv.started:
                return
            time.sleep(0.1)
        raise RuntimeError("o servidor da API não subiu")

    def parar(self):
        self.srv.should_exit = True
        self.t.join(timeout=10)


def chamar(base, caminho, chave=None, corpo=None, metodo=None, cabecalhos=None, bruto=None):
    """(status, json ou texto, cabeçalhos em minúsculas). `corpo` vira JSON; `bruto` vai como está."""
    h = dict(cabecalhos or {})
    if chave:
        h.setdefault("Authorization", f"Bearer {chave}")
    dados = None
    if bruto is not None:
        dados = bruto
        h["Content-Type"] = "application/json"
    elif corpo is not None:
        dados = json.dumps(corpo).encode()
        h["Content-Type"] = "application/json"
    if caminho.startswith("/mcp"):
        h["Accept"] = "application/json, text/event-stream"
    url = base + urllib.parse.quote(caminho, safe="/?=&:%$")          # espaço e acento vão como o navegador mandaria
    req = urllib.request.Request(url, data=dados, headers=h, method=metodo or ("POST" if dados is not None else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, texto, cab = r.status, r.read().decode("utf-8"), {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        try:
            status, texto, cab = e.code, e.read().decode("utf-8"), {k.lower(): v for k, v in e.headers.items()}
        finally:
            e.close()
    try:
        return status, json.loads(texto), cab
    except ValueError:
        return status, texto, cab


def mcp(base, chave, ferramenta, argumentos=None):
    """Uma chamada de tool pela porta MCP (JSON-RPC, sem sessão). Devolve o resultado já decodificado."""
    corpo = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": ferramenta, "arguments": argumentos or {}}}
    status, dados, _ = chamar(base, "/mcp", chave, corpo)
    assert status == 200, (status, dados)
    assert "error" not in dados, dados
    res = dados["result"]
    assert not res.get("isError"), res
    sc = res.get("structuredContent")                 # lista devolve {"result": [...]} (vazia não tem blocos de texto)
    if sc is not None:
        return sc["result"] if list(sc) == ["result"] else sc
    return json.loads(res["content"][0]["text"])      # dict devolve o JSON como texto


class AgenteFalso:
    """Troca o agente de verdade: registra o que recebeu e devolve eventos fixos. Nenhum teste chama modelo."""

    class Leitor:
        def __init__(self):
            self.resposta, self.uso, self.modelo, self.consultas = "", {}, None, []

    def __init__(self, resposta="Resposta de teste.", falha=None, dorme=0):
        self.resposta, self.falha, self.dorme, self.chamadas = resposta, falha, dorme, []

    def perguntar(self, texto, tenants, historico=None, leitor=None, request_id=None, **_):
        self.chamadas.append({"texto": texto, "tenants": list(tenants), "historico": historico, "request_id": request_id})
        if self.dorme:
            time.sleep(self.dorme)
        if self.falha:
            yield ("erro", {"motivo": self.falha})
            return
        leitor.resposta, leitor.modelo, leitor.uso = self.resposta, "modelo-falso", {"entrada": 100, "saida": 20, "custo_usd": 0.0012}
        yield ("fonte", {"evidencia": "g1", "trecho": "trecho de teste", "hash_confere": True})
        yield ("fim", {"duracao_ms": 5})


# ---------------------------------------------------------------------------------------------------- chaves e limites

class TestChaves(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.arq = Path(self.dir.name) / "chaves.json"
        self.c = ch.Chaves(self.arq)

    def tearDown(self):
        self.dir.cleanup()

    def test_o_arquivo_guarda_so_o_hash_nunca_a_chave(self):
        chave = self.c.gerar("cli", "estado")
        texto = self.arq.read_text(encoding="utf-8")
        self.assertNotIn(chave, texto)
        self.assertIn(ch.hash_da_chave(chave), texto)
        self.assertTrue(chave.startswith("fx_"))

    def test_chave_valida_devolve_o_perfil_e_os_entes_do_servidor(self):
        chave = self.c.gerar("cli", "estado")
        cli = self.c.autenticar(chave)
        self.assertEqual((cli.id, cli.perfil), ("cli", "estado"))
        self.assertEqual(set(cli.tenants), {"pe-estado", "pe-garanhuns"})

    def test_chave_invalida_vazia_ou_gigante_nao_autentica(self):
        self.c.gerar("cli", "estado")
        for ruim in ("", "fx_errada", "x" * 500, " "):
            self.assertIsNone(self.c.autenticar(ruim), ruim[:10])

    def test_sem_arquivo_ninguem_entra(self):
        self.assertIsNone(self.c.autenticar("fx_qualquer"))

    def test_perfil_desconhecido_e_recusado_ao_gerar(self):
        with self.assertRaisesRegex(ValueError, "perfil desconhecido"):
            self.c.gerar("cli", "nao-existe")
        self.assertFalse(self.arq.exists())

    def test_perfil_com_dado_pessoal_e_recusado(self):
        todos = {"interno": {"nome": "Interno", "tenants": ["pe-estado"], "ver_pessoal": True}}
        with self.assertRaisesRegex(ValueError, "dado pessoal"):
            ch._cliente({"cliente": "cli", "perfil": "interno"}, todos)

    def test_arquivo_com_perfil_invalido_falha_alto_em_vez_de_cair_num_padrao(self):
        self.arq.write_text(json.dumps({ch.hash_da_chave("fx_x"): {"cliente": "cli", "perfil": "inventado"}}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "perfil desconhecido"):
            self.c.autenticar("fx_x")

    def test_limites_fora_da_faixa_sao_recusados(self):
        with self.assertRaises(ValueError):
            self.c.gerar("cli", "estado", limite_por_minuto=0)
        with self.assertRaises(ValueError):
            self.c.gerar("cli", "estado", perguntas_por_dia=-1)

    def test_chave_revogada_para_de_valer_sem_reiniciar(self):
        chave = self.c.gerar("cli", "estado")
        self.assertIsNotNone(self.c.autenticar(chave))
        dados = json.loads(self.arq.read_text(encoding="utf-8"))
        dados[ch.hash_da_chave(chave)]["ativo"] = False
        time.sleep(0.01)
        self.arq.write_text(json.dumps(dados, indent=2), encoding="utf-8")
        self.assertIsNone(self.c.autenticar(chave))

    def test_chave_nova_vale_sem_reiniciar(self):
        outra = ch.Chaves(self.arq)
        k1 = self.c.gerar("um", "estado")
        self.assertIsNotNone(outra.autenticar(k1))
        k2 = self.c.gerar("dois", "municipio")
        self.assertEqual(outra.autenticar(k2).perfil, "municipio")


class TestLimites(unittest.TestCase):
    def test_limite_por_minuto_e_janela_deslizante(self):
        t = [1000.0]
        lim = lm.Limites(relogio=lambda: t[0])
        self.assertTrue(all(lim.requisicao("a", 3) is None for _ in range(3)))
        espera = lim.requisicao("a", 3)
        self.assertIsNotNone(espera)
        self.assertTrue(1 <= espera <= 61)
        self.assertIsNone(lim.requisicao("b", 3), "o limite é por cliente")
        t[0] += 61
        self.assertIsNone(lim.requisicao("a", 3), "passou a janela")

    def test_teto_diario_por_cliente_e_no_total(self):
        lim = lm.Limites()
        self.assertIsNone(lim.reservar_pergunta("a", 2, 10))
        self.assertIsNone(lim.reservar_pergunta("a", 2, 10))
        self.assertIn("deste cliente", lim.reservar_pergunta("a", 2, 10))
        self.assertEqual(lim.restantes_hoje("a", 2), 0)
        lim2 = lm.Limites()
        self.assertIsNone(lim2.reservar_pergunta("a", 5, 1))
        self.assertIn("do serviço", lim2.reservar_pergunta("b", 5, 1))

    def test_o_dia_vira_a_meia_noite(self):
        t = [time.mktime((2026, 11, 15, 23, 59, 0, 0, 0, -1))]
        lim = lm.Limites(relogio=lambda: t[0])
        self.assertIsNone(lim.reservar_pergunta("a", 1, 10))
        self.assertIsNotNone(lim.reservar_pergunta("a", 1, 10))
        t[0] += 120
        self.assertIsNone(lim.reservar_pergunta("a", 1, 10))


class TestPerfilPorChamada(unittest.TestCase):
    def test_sem_entes_e_recusado(self):
        for tenants in ([], [""], [None]):
            with self.assertRaises(ValueError):
                with servidor.nucleo.com_perfil("x", tenants):
                    pass

    def test_o_contexto_acaba_com_o_bloco(self):
        antes = servidor.nucleo._ctx()
        with servidor.nucleo.com_perfil("estado", ["pe-estado"], False, "s1"):
            self.assertEqual(servidor.nucleo._ctx()["tenants"], ["pe-estado"])
            self.assertEqual(servidor.nucleo._ctx()["sensibilidades"], ["publico"])
        self.assertEqual(servidor.nucleo._ctx(), antes)
        self.assertEqual(antes["tenants"], [], "o processo da API não tem perfil próprio: sem contexto, sem entes")


# ---------------------------------------------------------------------------------------------------- HTTP, sem banco

class TestHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.chaves = ch.Chaves(Path(cls.dir.name) / "chaves.json")
        cls.k_estado = cls.chaves.gerar("cli-estado", "estado", perguntas_por_dia=3)
        cls.k_mun = cls.chaves.gerar("cli-mun", "municipio")
        cls.agente = AgenteFalso()
        cls.app = servidor.criar_app(cls.chaves, lm.Limites(), cls.agente)
        cls.srv = Servidor(cls.app)
        cls.b = cls.srv.base

    @classmethod
    def tearDownClass(cls):
        cls.srv.parar()
        cls.dir.cleanup()

    def setUp(self):
        self.agente.chamadas.clear()
        self.agente.resposta, self.agente.falha, self.agente.dorme = "Resposta de teste.", None, 0

    # --- chave
    def test_todas_as_portas_exigem_chave(self):
        for metodo, caminho, corpo in (("GET", "/v1/me", None), ("GET", "/v1/cobertura", None), ("GET", "/v1/fornecedores?q=a", None),
                                       ("GET", f"/v1/fornecedores/{A}/contratos", None), ("GET", "/v1/evidencias/g1", None),
                                       ("POST", "/v1/perguntar", {"pergunta": "oi"}),
                                       ("POST", "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}),
                                       ("GET", "/qualquer-outra-coisa", None)):
            status, dados, cab = chamar(self.b, caminho, None, corpo, metodo)
            self.assertEqual(status, 401, caminho)
            self.assertIn("Bearer", cab.get("www-authenticate", ""), caminho)
        self.assertEqual(self.agente.chamadas, [], "pergunta sem chave não chega ao agente")

    def test_chave_errada_e_401_nas_tres_portas(self):
        self.assertEqual(chamar(self.b, "/v1/me", "fx_errada")[0], 401)
        self.assertEqual(chamar(self.b, "/v1/perguntar", "fx_errada", {"pergunta": "oi"})[0], 401)
        self.assertEqual(chamar(self.b, "/mcp", "fx_errada", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})[0], 401)

    def test_cabecalho_x_api_key_tambem_vale(self):
        status, dados, _ = chamar(self.b, "/v1/me", cabecalhos={"X-API-Key": self.k_estado})
        self.assertEqual((status, dados["perfil"]), (200, "estado"))

    def test_saude_e_openapi_sao_publicos(self):
        self.assertEqual(chamar(self.b, "/openapi.json")[0], 200)
        self.assertIn(chamar(self.b, "/v1/saude")[0], (200, 503))

    def test_me_mostra_so_o_que_a_chave_tem_sem_expor_a_chave(self):
        status, dados, _ = chamar(self.b, "/v1/me", self.k_mun)
        self.assertEqual(status, 200)
        self.assertEqual(dados["entes"], ["pe-garanhuns"])
        self.assertNotIn(self.k_mun, json.dumps(dados))

    def test_resposta_tem_request_id_e_nao_e_guardada_em_cache(self):
        _, _, cab = chamar(self.b, "/v1/me", self.k_mun)
        self.assertTrue(cab["x-request-id"].startswith("api:"))
        self.assertEqual(cab["cache-control"], "no-store")

    # --- openapi
    def test_openapi_descreve_todas_as_rotas_e_a_chave(self):
        _, spec, _ = chamar(self.b, "/openapi.json")
        self.assertEqual(spec["openapi"], "3.1.0")
        esperado = {c for c, *_ in servidor.ROTAS_DE_DADOS} | {"/v1/perguntar", "/v1/me", "/v1/saude", "/mcp"}
        self.assertEqual(set(spec["paths"]), esperado)
        self.assertIn("chave", spec["components"]["securitySchemes"])
        self.assertEqual(spec["paths"]["/v1/perguntar"]["post"]["requestBody"]["content"]["application/json"]["schema"]["required"], ["pergunta"])

    # --- pergunta em português (agente falso)
    def test_pergunta_devolve_resposta_fontes_modelo_e_uso(self):
        status, d, _ = chamar(self.b, "/v1/perguntar", self.k_estado, {"pergunta": "Quais contratos temos?"})
        self.assertEqual(status, 200, d)
        self.assertEqual((d["resposta"], d["modelo"], d["perfil"]), ("Resposta de teste.", "modelo-falso", "estado"))
        self.assertEqual(d["fontes"][0]["evidencia"], "g1")
        self.assertEqual(d["uso"], {"entrada": 100, "saida": 20, "custo_usd": 0.0012})

    def test_o_perfil_vem_da_chave_nunca_do_corpo(self):
        corpo = {"pergunta": "oi", "perfil": "estado-uniao", "tenants": ["br-uniao"], "ver_pessoal": True, "sensibilidade": "pessoal"}
        status, _, _ = chamar(self.b, "/v1/perguntar", self.k_mun, corpo)
        self.assertEqual(status, 200)
        self.assertEqual(self.agente.chamadas[0]["tenants"], ["pe-garanhuns"], "o agente recebeu os entes da CHAVE, não os do corpo")

    def test_o_perfil_vem_da_chave_nunca_da_url(self):
        chamar(self.b, "/v1/perguntar?perfil=estado-uniao&tenants=br-uniao", self.k_mun, {"pergunta": "oi"})
        self.assertEqual(self.agente.chamadas[0]["tenants"], ["pe-garanhuns"])

    def test_validacao_da_pergunta(self):
        casos = [({}, "pergunta"), ({"pergunta": ""}, "pergunta"), ({"pergunta": "   "}, "pergunta"), ({"pergunta": 123}, "pergunta"),
                 ({"pergunta": "x" * 501}, "longa demais"), ([1, 2], "pergunta"),
                 ({"pergunta": "oi", "historico": "nao-lista"}, "historico"),
                 ({"pergunta": "oi", "historico": [{"pergunta": "a"}]}, "historico"),
                 ({"pergunta": "oi", "historico": [{"pergunta": "a", "resposta": "b"}] * 7}, "historico"),
                 ({"pergunta": "oi", "historico": [{"pergunta": "a", "resposta": "x" * 801}]}, "longo demais")]
        for corpo, trecho in casos:
            status, d, _ = chamar(self.b, "/v1/perguntar", self.k_estado, corpo)
            self.assertEqual(status, 400, corpo)
            self.assertIn(trecho, d["erro"], corpo)
        self.assertEqual(self.agente.chamadas, [], "pergunta inválida nunca chega ao agente")

    def test_corpo_que_nao_e_json_e_corpo_grande_demais(self):
        self.assertEqual(chamar(self.b, "/v1/perguntar", self.k_estado, bruto=b"{isto nao e json")[0], 400)
        status, d, _ = chamar(self.b, "/v1/perguntar", self.k_estado, bruto=json.dumps({"pergunta": "oi", "lixo": "x" * 30000}).encode())
        self.assertEqual(status, 413)

    def test_historico_valido_chega_ao_agente_como_tuplas(self):
        chamar(self.b, "/v1/perguntar", self.k_mun, {"pergunta": "e o segundo?", "historico": [{"pergunta": "a", "resposta": "b"}]})
        self.assertEqual(self.agente.chamadas[0]["historico"], [("a", "b")])

    def test_falha_do_agente_vira_502_sem_vazar_detalhe(self):
        self.agente.falha = "A consulta demorou mais que o esperado."
        status, d, _ = chamar(self.b, "/v1/perguntar", self.k_mun, {"pergunta": "oi"})
        self.assertEqual(status, 502)
        self.assertEqual(d["erro"], "não consegui concluir agora")
        self.assertIn("demorou", d["motivo"])

    def test_excecao_no_agente_vira_500_generico(self):
        class Quebra(AgenteFalso):
            def perguntar(self, *a, **k):
                raise RuntimeError("C:\\caminho\\secreto\\arquivo.py: senha=abc")
                yield  # pragma: no cover
        antigo = self.app.state.estado._agente
        self.app.state.estado._agente = Quebra()
        try:
            status, d, _ = chamar(self.b, "/v1/perguntar", self.k_mun, {"pergunta": "oi"})
        finally:
            self.app.state.estado._agente = antigo
        self.assertEqual(status, 500)
        self.assertNotIn("secreto", json.dumps(d))
        self.assertNotIn("senha", json.dumps(d))

    def test_teto_diario_de_perguntas_por_cliente(self):
        chave = self.chaves.gerar("cli-teto", "municipio", perguntas_por_dia=2)
        self.assertEqual([chamar(self.b, "/v1/perguntar", chave, {"pergunta": "oi"})[0] for _ in range(2)], [200, 200])
        status, d, _ = chamar(self.b, "/v1/perguntar", chave, {"pergunta": "oi"})
        self.assertEqual(status, 429)
        self.assertIn("limite diário", d["erro"])
        self.assertEqual(len(self.agente.chamadas), 2, "a terceira não chamou o modelo")
        self.assertEqual(chamar(self.b, "/v1/me", chave)[1]["perguntas_restantes_hoje"], 0)

    def test_pergunta_invalida_nao_gasta_o_teto(self):
        chave = self.chaves.gerar("cli-teto2", "municipio", perguntas_por_dia=1)
        self.assertEqual(chamar(self.b, "/v1/perguntar", chave, {"pergunta": ""})[0], 400)
        self.assertEqual(chamar(self.b, "/v1/perguntar", chave, {"pergunta": "oi"})[0], 200)

    def test_limite_por_minuto_responde_429_com_retry_after(self):
        chave = self.chaves.gerar("cli-minuto", "municipio", limite_por_minuto=3)
        self.assertEqual([chamar(self.b, "/v1/me", chave)[0] for _ in range(3)], [200, 200, 200])
        status, d, cab = chamar(self.b, "/v1/me", chave)
        self.assertEqual(status, 429)
        self.assertGreaterEqual(int(cab["retry-after"]), 1)
        self.assertEqual(chamar(self.b, "/v1/me", self.k_mun)[0], 200, "outro cliente não é afetado")

    def test_o_log_da_api_nao_guarda_chave_nem_o_texto_da_pergunta(self):
        pergunta = "pergunta-secreta-do-teste-98765"
        chamar(self.b, "/v1/perguntar", self.k_mun, {"pergunta": pergunta})
        arquivo = registro.pasta() / "api.jsonl"
        texto = arquivo.read_text(encoding="utf-8")
        self.assertNotIn(pergunta, texto)
        self.assertNotIn(self.k_mun, texto)
        self.assertIn('"porta": "pergunta"', texto)
        ultima = [json.loads(l) for l in texto.splitlines() if '"porta": "pergunta"' in l][-1]
        self.assertEqual((ultima["cliente"], ultima["status"], ultima["modelo"], ultima["custo_usd"]), ("cli-mun", 200, "modelo-falso", 0.0012))


# ---------------------------------------------------------------------------------------------------- HTTP, com Neo4j de verdade

class TestIsolamentoComBanco(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        motivo = banco_disponivel()
        if motivo:
            raise unittest.SkipTest(motivo)
        cls.dir = tempfile.TemporaryDirectory()
        cls.chaves = ch.Chaves(Path(cls.dir.name) / "chaves.json")
        cls.k_mun = cls.chaves.gerar("cli-mun", "municipio", limite_por_minuto=1000)
        cls.k_ex = cls.chaves.gerar("cli-ex", "estado-exemplo", limite_por_minuto=1000)
        cls.k_est = cls.chaves.gerar("cli-est", "estado", limite_por_minuto=1000)
        cls.srv = Servidor(servidor.criar_app(cls.chaves, lm.Limites(), AgenteFalso()))
        cls.b = cls.srv.base

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "srv"):
            cls.srv.parar()
            cls.dir.cleanup()

    def rest(self, caminho, chave):
        status, d, _ = chamar(self.b, caminho, chave)
        return status, d

    def test_cada_chave_ve_so_os_entes_do_seu_perfil(self):
        _, a = self.rest("/v1/cobertura", self.k_mun)
        _, b = self.rest("/v1/cobertura", self.k_ex)
        self.assertEqual(a["dados"]["tenants_do_perfil"], ["pe-garanhuns"])
        self.assertEqual(b["dados"]["tenants_do_perfil"], ["ex-estado"])
        self.assertEqual(a["dados"]["perfil"], "municipio")
        self.assertEqual(b["dados"]["perfil"], "estado-exemplo")

    def test_fornecedor_de_outro_ente_nao_existe_para_quem_nao_tem_o_ente(self):
        s1, mun = self.rest(f"/v1/fornecedores/{C}/contratos", self.k_mun)
        s2, ex = self.rest(f"/v1/fornecedores/{C}/contratos", self.k_ex)
        self.assertEqual((s1, mun["resultados"]), (200, 0))
        self.assertEqual((s2, ex["resultados"]), (200, 1))
        self.assertEqual(self.rest("/v1/fornecedores?q=Obras Exemplares", self.k_mun)[1]["resultados"], 0)
        self.assertEqual(self.rest("/v1/fornecedores?q=Obras Exemplares", self.k_ex)[1]["resultados"], 1)

    def test_o_perfil_nao_muda_por_parametro_de_url(self):
        _, d = self.rest("/v1/cobertura?perfil=estado-exemplo&tenants=ex-estado&ver_pessoal=sim", self.k_mun)
        self.assertEqual(d["dados"]["tenants_do_perfil"], ["pe-garanhuns"])

    def test_evidencia_de_outro_ente_da_404_e_a_propria_abre_sem_caminho_do_servidor(self):
        _, contratos = self.rest(f"/v1/fornecedores/{C}/contratos", self.k_ex)
        evidencia = contratos["dados"][0]["evidencia"]
        self.assertEqual(self.rest(f"/v1/evidencias/{evidencia}", self.k_mun)[0], 404)
        status, ok = self.rest(f"/v1/evidencias/{evidencia}", self.k_ex)
        self.assertEqual(status, 200)
        self.assertNotIn("/", ok["dados"]["arquivo"])
        self.assertNotIn("\\", ok["dados"]["arquivo"])
        self.assertIn("hash_confere", ok["dados"])

    def test_entrada_invalida_e_400_com_mensagem_clara(self):
        for caminho in ("/v1/fornecedores", "/v1/fornecedores/id-ruim/contratos", f"/v1/fornecedores/{A}/execucao?ano=20x5",
                        "/v1/evidencias/a$b", "/v1/fornecedores?q=" + "x" * 101):
            status, d = self.rest(caminho, self.k_est)
            self.assertEqual(status, 400, caminho)
            self.assertIn("erro", d)
            self.assertNotIn("Traceback", json.dumps(d))

    def test_a_mesma_consulta_da_o_mesmo_resultado_que_o_nucleo_direto(self):
        _, via_api = self.rest("/v1/contratos", self.k_est)
        with servidor.nucleo.com_perfil("estado", ["pe-estado", "pe-garanhuns"], False, "teste"):
            direto = servidor.nucleo.listar_contratos()
        self.assertEqual(via_api["dados"], direto)

    def test_mcp_lista_as_nove_tools_do_agente(self):
        status, d, _ = chamar(self.b, "/mcp", self.k_mun, {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        self.assertEqual(status, 200)
        nomes = {t["name"] for t in d["result"]["tools"]}
        self.assertEqual(nomes, {"cobertura", "buscar_fornecedor", "listar_contratos", "buscar_contratos", "contratos_do_fornecedor",
                                 "sancoes_do_fornecedor", "cadastro_do_fornecedor", "execucao_do_fornecedor", "conferir_evidencia"})

    def test_mcp_respeita_o_perfil_da_chave(self):
        self.assertEqual(mcp(self.b, self.k_mun, "cobertura")["tenants_do_perfil"], ["pe-garanhuns"])
        self.assertEqual(mcp(self.b, self.k_ex, "cobertura")["tenants_do_perfil"], ["ex-estado"])
        self.assertEqual(mcp(self.b, self.k_mun, "contratos_do_fornecedor", {"fornecedor_id": C}), [])
        self.assertEqual(len(mcp(self.b, self.k_ex, "contratos_do_fornecedor", {"fornecedor_id": C})), 1)

    def test_mcp_nao_aceita_perfil_como_argumento(self):
        """Perfil e entes no argumento da tool: ou são recusados, ou ignorados. Nunca valem."""
        corpo = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                 "params": {"name": "cobertura", "arguments": {"perfil": "estado-uniao", "tenants": ["br-uniao"], "ver_pessoal": True}}}
        status, d, _ = chamar(self.b, "/mcp", self.k_mun, corpo)
        self.assertEqual(status, 200)
        res = d.get("result", {})
        if not res.get("isError") and "structuredContent" in res:
            self.assertEqual(res["structuredContent"]["tenants_do_perfil"], ["pe-garanhuns"])
            self.assertEqual(res["structuredContent"]["perfil"], "municipio")

    def test_concorrencia_um_perfil_nunca_vaza_para_o_outro(self):
        """O risco real de um servidor que atende vários perfis num processo só: a chamada de um perfil enxergar o contexto de outra.
        Muitas chamadas ao mesmo tempo, alternando as chaves, pelas duas portas: cada resposta precisa ser do perfil da SUA chave."""
        esperado = {self.k_mun: ["pe-garanhuns"], self.k_ex: ["ex-estado"], self.k_est: ["pe-estado", "pe-garanhuns"]}
        trabalhos = []
        for i in range(60):
            chave = (self.k_mun, self.k_ex, self.k_est)[i % 3]
            trabalhos.append((chave, "rest" if i % 2 == 0 else "mcp"))

        def executar(t):
            chave, porta = t
            if porta == "rest":
                _, d, _ = chamar(self.b, "/v1/cobertura", chave)
                return chave, d["dados"]["tenants_do_perfil"]
            return chave, mcp(self.b, chave, "cobertura")["tenants_do_perfil"]

        with ThreadPoolExecutor(max_workers=12) as pool:
            resultados = list(pool.map(executar, trabalhos))
        erradas = [(chave[:6], got, esperado[chave]) for chave, got in resultados if got != esperado[chave]]
        self.assertEqual(erradas, [], "uma resposta veio com os entes de outro perfil")
        self.assertEqual(len(resultados), 60)

    def test_o_log_das_tools_leva_o_perfil_e_o_cliente_da_chave(self):
        arquivo = Path(os.environ["TRANSPARENCIA_LOG"])
        antes = arquivo.read_text(encoding="utf-8").count("\n") if arquivo.exists() else 0
        self.rest("/v1/cobertura", self.k_ex)
        linhas = arquivo.read_text(encoding="utf-8").splitlines()[antes:]
        ultima = json.loads(linhas[-1])
        self.assertEqual((ultima["perfil"], ultima["tenants"], ultima["tool"]), ("estado-exemplo", ["ex-estado"], "cobertura"))
        self.assertTrue(ultima["sessao"].startswith("api:"))

    def test_fora_de_uma_requisicao_o_nucleo_falha_fechado(self):
        """Sem contexto, o processo da API não tem entes: a consulta devolve vazio, nunca 'tudo'."""
        self.assertEqual(servidor.nucleo.cobertura()["contratos"], 0)
        self.assertEqual(servidor.nucleo.listar_contratos(), [])


if __name__ == "__main__":
    unittest.main()
