"""Google simulado localmente, com JWT RSA assinado; somente no executor descartável."""
import base64
import concurrent.futures
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import urllib.parse
import uuid
import unittest

import test_api as api
import test_auth as auth

setUpModule = api.setUpModule
tearDownModule = api.tearDownModule
CLIENT_ID = "fornex-test.apps.googleusercontent.com"


def b64(valor):
    return base64.urlsafe_b64encode(valor).decode().rstrip("=")


def php_json(codigo, dados=None, env=None):
    r = subprocess.run([api.PHP, "-r", codigo], input=json.dumps(dados).encode() if dados is not None else b"",
                       capture_output=True, env=env, timeout=15)
    if r.returncode:
        raise RuntimeError("Falha na criptografia do simulador local.")
    return json.loads(r.stdout)


class GoogleSimulado:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="fornex-google-test-")
        config = Path(self.tmp.name) / "openssl.cnf"
        config.write_text("[req]\ndistinguished_name=dn\n[dn]\n", encoding="ascii")
        self.chaves = php_json("$k=openssl_pkey_new(['private_key_bits'=>2048,'private_key_type'=>OPENSSL_KEYTYPE_RSA,'config'=>getenv('AUTH_TEST_OPENSSL')]);"
                               "openssl_pkey_export($k,$p,null,['config'=>getenv('AUTH_TEST_OPENSSL')]);"
                               "echo json_encode(['privada'=>$p,'publica'=>openssl_pkey_get_details($k)['key']]);",
                               env={**os.environ, "AUTH_TEST_OPENSSL": str(config)})
        simulado = self
        self.total = 0
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass  # Nunca registrar URL/credential.

            def do_GET(self):
                simulado.total += 1
                token = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("id_token", [""])[0]
                try:
                    partes = token.split(".")
                    assinatura = base64.urlsafe_b64decode(partes[2] + "=" * (-len(partes[2]) % 4))
                    ok = php_json("$d=json_decode(stream_get_contents(STDIN),true); echo json_encode(openssl_verify($d['texto'],base64_decode($d['assinatura']),$d['publica'],OPENSSL_ALGO_SHA256)===1);",
                                  {"texto": ".".join(partes[:2]), "assinatura": base64.b64encode(assinatura).decode(), "publica": simulado.chaves["publica"]})
                    if not ok:
                        raise ValueError("assinatura")
                    claims = json.loads(base64.urlsafe_b64decode(partes[1] + "=" * (-len(partes[1]) % 4)))
                    resposta, status = claims, 200
                except Exception:
                    resposta, status = {"error": "invalid_token"}, 400
                dados = json.dumps(resposta).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

        self.http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.http.server_port}/tokeninfo"

    def token(self, **extras):
        claims = {"aud": CLIENT_ID, "iss": "https://accounts.google.com", "exp": int(time.time()) + 600,
                  "email_verified": True, "sub": uuid.uuid4().hex,
                  "email": "fornextest." + uuid.uuid4().hex[:12] + "@gmail.com", "name": "Cliente Google", **extras}
        texto = b64(b'{"alg":"RS256","typ":"JWT"}') + "." + b64(json.dumps(claims).encode())
        assinatura = php_json("$d=json_decode(stream_get_contents(STDIN),true); openssl_sign($d['texto'],$s,$d['privada'],OPENSSL_ALGO_SHA256); echo json_encode(base64_encode($s));",
                              {"texto": texto, "privada": self.chaves["privada"]})
        return texto + "." + b64(base64.b64decode(assinatura))

    def close(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()


class TestGoogle(api.Base):
    servidor = auth.TestAuthPublica.servidor
    entregar = auth.TestAuthPublica.entregar

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.desabilitado = cls.base
        cls.google = GoogleSimulado()
        cls.contexto = auth.TestAuthPublica().servidor(GOOGLE_CLIENT_ID=CLIENT_ID, AUTH_TEST_GOOGLE_TOKENINFO=cls.google.url)
        cls.base = cls.contexto.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.contexto.__exit__(None, None, None)
        cls.google.close()

    def setUp(self):
        super().setUp()
        api.sql("DELETE FROM auth_emails; DELETE FROM auth_tokens")

    def entrar_google(self, token=None, cliente=None, **claims):
        c = cliente or api.Cliente(self.base)
        r = c.req("POST", "/api/login/google", {"credential": token or self.google.token(**claims)})
        return c, r

    def test_cria_conta_sem_senha_reutiliza_identidade_e_fluxo_existente(self):
        token = self.google.token()
        c = api.Cliente(self.base)
        antes = c.me()["csrf"]
        cookie = c.cookie_sessao()
        _, r = self.entrar_google(token, c)
        self.assertEqual(r.status, 200, r.corpo)
        uid = r["usuario"]["id"]
        self.assertEqual(r["usuario"]["papel"], "usuario")
        self.assertTrue(r["usuario"]["email_verificado"])
        self.assertNotEqual(r["csrf"], antes)
        self.assertNotEqual(c.cookie_sessao(), cookie)
        self.assertEqual(api.sql(f"SELECT senha_hash IS NULL,email_verificacao_exigida,google_sub IS NOT NULL FROM usuarios WHERE id={uid}"), "1\t0\t1")
        outro, segunda = self.entrar_google(token)
        self.assertEqual(segunda.status, 200)
        self.assertEqual(segunda["usuario"]["id"], uid)
        self.assertEqual(c.req("GET", "/api/admin/telefones").status, 403)
        c.assinar()
        self.assertEqual(c.perguntar().status, 201)
        self.assertEqual(api.worker(self.base, "POST", "/api/worker/proxima").status, 200)
        self.assertEqual(outro.me()["usuario"]["id"], uid)

    def test_recusa_claims_invalidas_com_resposta_generica(self):
        for claims in [{"aud": "outro-client"}, {"iss": "https://invalido.example"}, {"exp": int(time.time()) - 1},
                       {"email_verified": False}, {"email_verified": "false"}, {"email_verified": 1},
                       {"sub": ""}, {"email": "sem-arroba"}, {"exp": "invalido"}]:
            with self.subTest(claims=claims):
                c, r = self.entrar_google(**claims)
                self.assertEqual(r.status, 401)
                self.assertEqual(r["erro"], "Não foi possível entrar com Google.")
                self.assertIsNone(c.me()["usuario"])

    def test_assinatura_adulterada_e_credencial_malformada_recusadas(self):
        token = self.google.token()
        partes = token.split(".")
        assinatura = bytearray(base64.urlsafe_b64decode(partes[2] + "=" * (-len(partes[2]) % 4)))
        assinatura[0] ^= 1
        partes[2] = b64(assinatura)  # Claims continuam válidas; só a assinatura foi adulterada.
        antes = self.google.total
        _, r = self.entrar_google(".".join(partes))
        self.assertEqual(r.status, 401)
        self.assertGreater(self.google.total, antes)
        _, r = self.entrar_google("nao-e-um-jwt")
        self.assertEqual(r.status, 401)

    def test_vincula_conta_verificada_preservando_senha_permissoes_e_plano(self):
        c = api.Cliente(self.base)
        c.cadastrar()
        c.assinar()
        uid = c.me()["usuario"]["id"]
        antes = api.sql(f"SELECT senha_hash,auth_versao,papel,email_verificacao_exigida FROM usuarios WHERE id={uid}")
        _, r = self.entrar_google(email=c.email)
        self.assertEqual(r.status, 200, r.corpo)
        self.assertEqual(r["usuario"]["id"], uid)
        self.assertIsNotNone(r["plano"])
        self.assertEqual(api.sql(f"SELECT senha_hash,auth_versao,papel,email_verificacao_exigida FROM usuarios WHERE id={uid}"), antes)
        self.assertEqual(c.req("POST", "/api/login", {"email": c.email, "senha": c.senha}).status, 200)

    def test_conta_antiga_nao_verificada_perde_senha_sessoes_e_tokens(self):
        c = api.Cliente(self.base)
        c.cadastrar()
        uid = c.me()["usuario"]["id"]
        api.sql(f"UPDATE usuarios SET email_verificado_em=NULL,email_verificacao_exigida=0 WHERE id={uid}")
        self.assertEqual(c.req("POST", "/api/email/verificar-conta", {}).status, 202)
        verificacao = self.entregar(c.email, "verificar")
        self.assertEqual(c.req("POST", "/api/senha/recuperar", {"email": c.email}).status, 202)
        redefinicao = self.entregar(c.email, "redefinir")
        antes = int(api.sql(f"SELECT auth_versao FROM usuarios WHERE id={uid}"))
        novo, r = self.entrar_google(email=c.email)
        self.assertEqual(r.status, 200, r.corpo)
        self.assertEqual(r["usuario"]["id"], uid)
        self.assertEqual(api.sql(f"SELECT senha_hash IS NULL,auth_versao,email_verificacao_exigida FROM usuarios WHERE id={uid}"), f"1\t{antes+1}\t0")
        self.assertIsNone(c.me()["usuario"])
        self.assertTrue(novo.me()["usuario"]["email_verificado"])
        self.assertEqual(c.req("POST", "/api/login", {"email": c.email, "senha": c.senha}).status, 401)
        self.assertEqual(c.req("POST", "/api/email/verificar", {"token": verificacao}).status, 400)
        self.assertEqual(c.req("POST", "/api/senha/redefinir", {"token": redefinicao, "senha": "nova frase exclusiva FORNEX!", "confirmacao": "nova frase exclusiva FORNEX!"}).status, 400)
        self.assertEqual(api.sql(f"SELECT COUNT(*) FROM auth_tokens WHERE usuario_id={uid} AND usado_em IS NULL"), "0")
        self.assertEqual(api.sql(f"SELECT COUNT(*) FROM auth_emails e JOIN auth_tokens t ON t.id=e.token_id WHERE t.usuario_id={uid} AND e.conteudo IS NOT NULL"), "0")

    def test_pendente_vinculada_tem_senha_anulada_e_exigencia_preservada(self):
        c, _ = auth.TestAuthPublica.pendente(self)
        _, r = self.entrar_google(email=c.email)
        self.assertEqual(r.status, 200, r.corpo)
        uid = r["usuario"]["id"]
        self.assertEqual(api.sql(f"SELECT senha_hash IS NULL,email_verificacao_exigida,email_verificado_em IS NOT NULL FROM usuarios WHERE id={uid}"), "1\t1\t1")
        self.assertEqual(c.req("POST", "/api/login", {"email": c.email, "senha": c.senha}).status, 401)

    def test_admin_nao_e_vinculado_e_continua_entrando_por_senha(self):
        antes = api.sql("SELECT senha_hash,auth_versao,email_verificado_em,google_sub FROM usuarios WHERE papel='admin'")
        for _ in range(2):
            _, r = self.entrar_google(email="admin@example.invalid")
            self.assertEqual(r.status, 401)
        self.assertEqual(api.sql("SELECT senha_hash,auth_versao,email_verificado_em,google_sub FROM usuarios WHERE papel='admin'"), antes)
        c = api.Cliente(self.base)
        self.assertEqual(c.req("POST", "/api/login", {"email": "admin@example.invalid", "senha": "legado-seguro-123"}).status, 200)
        self.assertEqual(c.req("GET", "/api/admin/telefones").status, 200)

    def test_sem_configuracao_404_e_com_configuracao_exige_csrf(self):
        c = api.Cliente(self.desabilitado)
        self.assertIsNone(c.me()["google_client_id"])
        self.assertEqual(c.req("POST", "/api/login/google", {}).status, 404)
        c = api.Cliente(self.base)
        self.assertEqual(c.me()["google_client_id"], CLIENT_ID)
        antes = self.google.total
        self.assertEqual(c.req("POST", "/api/login/google", {"credential": self.google.token()}, csrf=False).status, 403)
        self.assertEqual(self.google.total, antes)

    def test_conta_so_google_nao_aceita_senha_nem_recuperacao(self):
        c, r = self.entrar_google()
        uid = r["usuario"]["id"]
        email = r["usuario"]["email"]
        self.assertEqual(c.req("POST", "/api/login", {"email": email, "senha": "qualquer frase exclusiva"}).status, 401)
        self.assertEqual(c.req("POST", "/api/senha/recuperar", {"email": email}).status, 202)
        self.assertEqual(api.sql(f"SELECT COUNT(*) FROM auth_tokens WHERE usuario_id={uid}"), "0")
        # Mesmo um token antigo preparado no banco isolado não cria senha na conta só-Google.
        token = "a" * 64
        import hashlib
        api.sql(f"INSERT INTO auth_tokens (usuario_id,finalidade,token_hash,expira_em) VALUES ({uid},'redefinir','{hashlib.sha256(token.encode()).hexdigest()}',NOW()+INTERVAL 10 MINUTE)")
        senha = "outra frase exclusiva FORNEX!"
        self.assertEqual(c.req("POST", "/api/senha/redefinir", {"token": token, "senha": senha, "confirmacao": senha}).status, 400)
        self.assertEqual(api.sql(f"SELECT senha_hash IS NULL FROM usuarios WHERE id={uid}"), "1")

    def test_vinculo_diferente_nao_e_sobrescrito_e_sub_nao_junta_duas_contas(self):
        sub = uuid.uuid4().hex
        _, r = self.entrar_google(sub=sub)
        email = r["usuario"]["email"]
        _, outra = self.entrar_google(email=email)
        self.assertEqual(outra.status, 401)
        c = api.Cliente(self.base)
        c.cadastrar()
        _, conflito = self.entrar_google(sub=sub, email=c.email)
        self.assertEqual(conflito.status, 401)
        _, mesmo = self.entrar_google(sub=sub, email="fornextest.novo@example.invalid")
        self.assertEqual(mesmo.status, 200)
        self.assertEqual(mesmo["usuario"]["id"], r["usuario"]["id"])

    def test_concorrencia_cria_uma_unica_conta(self):
        token = self.google.token()
        # Servidores PHP diferentes para exercitar as travas MariaDB, sem sessão compartilhada.
        with self.servidor(GOOGLE_CLIENT_ID=CLIENT_ID, AUTH_TEST_GOOGLE_TOKENINFO=self.google.url) as outro:
            clientes = [api.Cliente(self.base), api.Cliente(outro)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                resultados = list(pool.map(lambda c: self.entrar_google(token, c)[1], clientes))
        self.assertEqual([r.status for r in resultados], [200, 200])
        self.assertEqual(resultados[0]["usuario"]["id"], resultados[1]["usuario"]["id"])

    def test_limite_bloqueia_antes_de_chamar_google(self):
        token = self.google.token(aud="incorreto")
        c = api.Cliente(self.base)
        for _ in range(5):
            self.assertEqual(self.entrar_google(token, c)[1].status, 401)
        antes = self.google.total
        self.assertEqual(self.entrar_google(token, c)[1].status, 429)
        self.assertEqual(self.google.total, antes)

    def test_workspace_e_email_externo_verificado_seguem_regra_solicitada(self):
        for claims in [{"email": "fornextest.workspace@empresa.example", "hd": "empresa.example"},
                       {"email": "fornextest.externo@empresa.example", "email_verified": "true", "iss": "accounts.google.com"}]:
            _, r = self.entrar_google(**claims)
            self.assertEqual(r.status, 200, r.corpo)
            self.assertTrue(r["usuario"]["email_verificado"])

    def test_indisponibilidade_do_validador_recusa_sem_criar_conta(self):
        porta = api.porta_livre()
        token = self.google.token()
        antes = api.sql("SELECT COUNT(*) FROM usuarios")
        with self.servidor(GOOGLE_CLIENT_ID=CLIENT_ID, AUTH_TEST_GOOGLE_TOKENINFO=f"http://127.0.0.1:{porta}/tokeninfo") as base:
            c = api.Cliente(base)
            self.assertEqual(c.req("POST", "/api/login/google", {"credential": token}).status, 401)
            self.assertIsNone(c.me()["usuario"])
        self.assertEqual(api.sql("SELECT COUNT(*) FROM usuarios"), antes)

    def test_simulador_so_pode_ser_ativado_em_banco_descartavel(self):
        pasta = (api.RAIZ / "site/public_html/api").as_posix()
        oficial = "https://oauth2.googleapis.com/tokeninfo"
        for ambiente, banco, url, esperado in [
            ("production", "fornex_auth_test_falso", self.google.url, oficial),
            ("test", "banco_comum", self.google.url, oficial),
            ("test", "fornex_auth_test_falso", "http://outro.example/tokeninfo", oficial),
            ("test", "fornex_auth_test_falso", self.google.url, self.google.url),
        ]:
            with self.subTest(ambiente=ambiente, banco=banco):
                codigo = f"define('API',true); define('AMBIENTE','{ambiente}'); define('DB_NAME','{banco}'); require '{pasta}/lib_auth.php'; require '{pasta}/lib_google.php'; echo json_encode(google_tokeninfo_url());"
                self.assertEqual(php_json(codigo, env={**os.environ, "AUTH_TEST_GOOGLE_TOKENINFO": url}), esperado)

    def test_migracao_repetida_preserva_contas_senhas_e_vinculos(self):
        self.entrar_google()
        antes = api.sql("SELECT id,COALESCE(senha_hash,'NULL'),papel,auth_versao,COALESCE(google_sub,'NULL'),COALESCE(email_verificado_em,'NULL') FROM usuarios ORDER BY id")
        for _ in range(2):
            subprocess.run([api.PHP, str(api.RAIZ / "site/migrar-autenticacao.php")], check=True, capture_output=True)
        self.assertEqual(api.sql("SELECT id,COALESCE(senha_hash,'NULL'),papel,auth_versao,COALESCE(google_sub,'NULL'),COALESCE(email_verificado_em,'NULL') FROM usuarios ORDER BY id"), antes)
        self.assertEqual(api.sql("SELECT IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='usuarios' AND COLUMN_NAME='senha_hash'"), "YES")

    @unittest.skipUnless(os.environ.get("FORNEX_PLAYWRIGHT_MODULE"), "Playwright opcional: defina FORNEX_PLAYWRIGHT_MODULE")
    def test_interface_google_simulada_nas_duas_abas(self):
        r = subprocess.run(["node", str(api.RAIZ / "site/dev/test_auth_google_ui.cjs")],
                           env={**os.environ, "FORNEX_UI_BASE": self.base, "FORNEX_UI_DISABLED_BASE": self.desabilitado,
                                "FORNEX_GOOGLE_TEST_CREDENTIAL": self.google.token()},
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
