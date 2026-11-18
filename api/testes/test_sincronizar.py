"""Testes da ponte site -> chaves da API (api/sincronizar_tokens.py). Sem rede externa: o "site" é um servidor HTTP local."""
import hashlib
import http.server
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "api"))
sys.path.insert(0, str(RAIZ / "consulta"))
import perfis  # noqa: E402
import sincronizar_tokens as s  # noqa: E402
from chaves import Chaves  # noqa: E402

TODOS = perfis.carregar()
ENTES_ESTADO = TODOS["estado"]["tenants"]


def h(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class TestMontar(unittest.TestCase):
    def test_perfil_vem_dos_entes_do_plano(self):
        self.assertEqual(s.perfil_dos_entes(list(reversed(ENTES_ESTADO)), TODOS), "estado")
        self.assertIsNone(s.perfil_dos_entes(["ente-que-nao-existe"], TODOS))
        self.assertIsNone(s.perfil_dos_entes([], TODOS))

    def test_mantem_chave_manual_e_troca_as_do_site(self):
        manual = {"a" * 64: {"cliente": "demo", "perfil": "estado", "ativo": True}}
        antiga_site = {"b" * 64: {"cliente": "site-conta-1", "perfil": "estado", "ativo": True, "origem": "site"}}
        novo = s.montar([{"hash": "c" * 64, "usuario_id": 7, "tenants": ENTES_ESTADO}], {**manual, **antiga_site}, TODOS)
        self.assertIn("a" * 64, novo)                       # a manual fica
        self.assertNotIn("b" * 64, novo)                    # o token revogado no site sai
        self.assertEqual(novo["c" * 64]["perfil"], "estado")
        self.assertEqual(novo["c" * 64]["origem"], "site")
        self.assertEqual(novo["c" * 64]["cliente"], "site-conta-7")

    def test_recusa_hash_invalido_plano_sem_perfil_e_nao_sobrescreve_manual(self):
        manual = {"d" * 64: {"cliente": "demo", "perfil": "estado", "ativo": True}}
        tokens = [{"hash": "x" * 64, "usuario_id": 1, "tenants": ENTES_ESTADO},           # não é hexadecimal
                  {"hash": "e" * 63, "usuario_id": 1, "tenants": ENTES_ESTADO},           # curto
                  {"hash": "f" * 64, "usuario_id": 1, "tenants": ["ente-desconhecido"]},  # plano sem perfil
                  {"hash": "d" * 64, "usuario_id": 2, "tenants": ENTES_ESTADO},           # já é uma chave manual
                  "lixo"]
        novo = s.montar(tokens, manual, TODOS)
        self.assertEqual(novo, manual)

    def test_nunca_escolhe_perfil_com_dado_pessoal(self):
        for nome, p in TODOS.items():
            if p["ver_pessoal"]:
                self.assertNotEqual(s.perfil_dos_entes(p["tenants"], TODOS), nome)


class TestArquivoEChaves(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.arquivo = Path(self.pasta.name) / "chaves.json"

    def tearDown(self):
        self.pasta.cleanup()

    def test_grava_so_quando_muda_com_permissao_restrita(self):
        novo = s.montar([{"hash": h("fx_um"), "usuario_id": 3, "tenants": ENTES_ESTADO}], {}, TODOS)
        self.assertTrue(s.gravar_se_mudou(self.arquivo, novo))
        self.assertEqual(oct(self.arquivo.stat().st_mode & 0o777), "0o600")
        self.assertFalse(s.gravar_se_mudou(self.arquivo, novo))

    def test_a_api_aceita_o_token_do_site_e_esquece_o_revogado(self):
        token = "fx_" + "T" * 32
        s.gravar_se_mudou(self.arquivo, s.montar([{"hash": h(token), "usuario_id": 3, "tenants": ENTES_ESTADO}], {}, TODOS))
        chaves = Chaves(self.arquivo)
        cliente = chaves.autenticar(token)
        self.assertIsNotNone(cliente)
        self.assertEqual(cliente.perfil, "estado")
        self.assertIsNone(chaves.autenticar("fx_" + "U" * 32))
        os.utime(self.arquivo, ns=(1, 1))                    # garante mtime diferente na troca
        s.gravar_se_mudou(self.arquivo, s.montar([], json.loads(self.arquivo.read_text()), TODOS))
        self.assertIsNone(chaves.autenticar(token))


class TestBuscarNoSite(unittest.TestCase):
    """O "site" local confere a chave do worker, como a rota PHP faz."""

    @classmethod
    def setUpClass(cls):
        chave, resposta = "k" * 30, [{"hash": "a" * 64, "usuario_id": 1, "tenants": ENTES_ESTADO}]

        class Site(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                ok = self.path == "/api/worker/tokens" and self.headers.get("X-Worker-Key") == chave
                corpo = json.dumps(resposta if ok else {"erro": "Chave do worker inválida."}).encode()
                self.send_response(200 if ok else 401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(corpo)

            def log_message(self, *a):
                pass

        cls.servidor = http.server.HTTPServer(("127.0.0.1", 0), Site)
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()
        cls.api, cls.chave = f"http://127.0.0.1:{cls.servidor.server_port}/api", chave

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()

    def test_busca_com_a_chave(self):
        self.assertEqual(s.buscar(self.api, self.chave)[0]["hash"], "a" * 64)

    def test_chave_errada_falha_e_nao_apaga_o_arquivo(self):
        with tempfile.TemporaryDirectory() as d:
            arquivo = Path(d) / "chaves.json"
            arquivo.write_text(json.dumps({"a" * 64: {"cliente": "site-conta-1", "perfil": "estado", "ativo": True, "origem": "site"}}))
            antes = arquivo.read_text()
            with self.assertRaises(OSError):                  # HTTP 401 vira urllib.error.HTTPError (subclasse de OSError)
                s.rodada(arquivo, self.api, "chave-errada-mas-com-tamanho")
            self.assertEqual(arquivo.read_text(), antes)


if __name__ == "__main__":
    unittest.main()
