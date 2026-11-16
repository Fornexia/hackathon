"""Login público com PHP e MariaDB reais, sem e-mails ou serviços pagos.

Execute: python site/dev/test_auth.py
Cria e remove seu próprio contêiner, banco e configuração temporária. Não lê o .env.
"""
import base64
import concurrent.futures
import contextlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid


def executar_isolado():
    raiz = Path(__file__).resolve().parents[2]
    php = os.environ.get("PHP_BIN") or shutil.which("php")
    if not php:
        raise RuntimeError("PHP 8.2+ com pdo_mysql, mbstring, openssl e Argon2id é necessário.")
    sufixo = uuid.uuid4().hex[:12]
    container = "fornex-auth-test-" + sufixo
    banco = "fornex_auth_test_" + sufixo
    senha = secrets.token_urlsafe(32)
    env = {**os.environ, "MARIADB_ROOT_PASSWORD": senha, "DB_TEST_ROOT_PASSWORD": senha,
           "DB_CONTAINER": container, "DB_TEST_DATABASE": banco}
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        porta = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="fornex-auth-test-") as tmp:
        privado = Path(tmp)
        (privado / "sessions").mkdir()
        config = privado / "config.php"
        env.update(FORNEX_CONFIG=str(config), AUTH_MAIL_CAPTURE=str(privado / "emails.jsonl"),
                   AUTH_TEST_SESSION_PATH=str(privado / "sessions"), AUTH_SESSION_PATH=str(privado / "sessions"), MAIL_TRANSPORT="capture",
                   AUTH_MAIL_KEY=base64.b64encode(secrets.token_bytes(32)).decode(), APP_URL="http://127.0.0.1", TRUSTED_PROXIES="")
        def executar(args, **kw):
            return subprocess.run(args, env=env, check=True, capture_output=True, text=True, encoding="utf-8", **kw)
        iniciado = False
        try:
            executar(["docker", "run", "--detach", "--rm", "--name", container, "--label", "fornex.auth-test=true",
                      "-e", "MARIADB_ROOT_PASSWORD", "-e", "MARIADB_DATABASE=" + banco,
                      "-p", f"127.0.0.1:{porta}:3306", "mariadb:10.11"])
            iniciado = True
            for _ in range(120):
                pronto = subprocess.run(["docker", "exec", container, "healthcheck.sh", "--connect", "--innodb_initialized"],
                                       capture_output=True, env=env)
                if pronto.returncode == 0:
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("MariaDB de teste não iniciou.")
            valores = {"AMBIENTE": "test", "DB_HOST": "127.0.0.1", "DB_PORT": porta, "DB_NAME": banco,
                       "DB_USER": "root", "DB_PASS": senha, "WORKER_KEY": secrets.token_hex(24)}
            def php_val(v):
                return str(v) if isinstance(v, int) else "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"
            config.write_text("<?php\n" + "\n".join(f"const {k} = {php_val(v)};" for k, v in valores.items()), encoding="utf-8")
            # Banco antigo mínimo: prova que a migração não muda os acessos existentes.
            php_hash = executar([php, "-r", "echo password_hash('legado-seguro-123', PASSWORD_BCRYPT);"]).stdout
            sql = ("CREATE TABLE usuarios (id INT AUTO_INCREMENT PRIMARY KEY, nome VARCHAR(120) NOT NULL, "
                   "email VARCHAR(190) NOT NULL UNIQUE, senha_hash VARCHAR(255) NOT NULL, "
                   "papel ENUM('admin','usuario') NOT NULL DEFAULT 'usuario', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP) "
                   "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; "
                   f"INSERT INTO usuarios (nome,email,senha_hash,papel) VALUES ('Admin legado','admin@example.invalid','{php_hash}','admin'), "
                   f"('Cliente legado','cliente@example.invalid','{php_hash}','usuario');")
            # A senha vai pelo ambiente do cliente Docker, não por argumentos.
            env["MYSQL_PWD"] = senha
            executar(["docker", "exec", "-e", "MYSQL_PWD", container, "mariadb", "-uroot", banco, "-e", sql])
            executar([php, str(raiz / "site/migrar-autenticacao.php")])
            executar([php, str(raiz / "site/setup.php")])
            suites = sys.argv[1:] or ["test_auth", "test_api", "test_prova", "test_auth_regressoes", "test_auth_ajustes"]
            resultado = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest", "-v", *suites],
                                      cwd=raiz / "site/dev", env=env)
            return resultado.returncode
        finally:
            if iniciado:
                subprocess.run(["docker", "stop", "--time", "5", container], env=env, capture_output=True)


if __name__ == "__main__":
    sys.exit(executar_isolado())

import test_api as api
setUpModule = api.setUpModule
tearDownModule = api.tearDownModule


class TestAuthPublica(api.Base):
    def setUp(self):
        super().setUp()
        api.sql("DELETE FROM auth_emails; DELETE FROM auth_tokens")

    @contextlib.contextmanager
    def servidor(self, **variaveis):
        porta = api.porta_livre()
        ambiente = {**os.environ, **variaveis}
        p = subprocess.Popen([api.PHP, "-S", f"127.0.0.1:{porta}", "-t", str(api.RAIZ / "site/public_html"), str(api.RAIZ / "site/dev/router.php")],
                             env=ambiente, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f"http://127.0.0.1:{porta}"
        try:
            for _ in range(60):
                try:
                    if api.chamar(base, "GET", "/api/saude").status == 200:
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                self.fail("Servidor adicional não iniciou.")
            yield base
        finally:
            p.terminate()
            p.wait(timeout=10)

    def pendente(self, senha="uma frase exclusiva FORNEX!", **extra):
        c = api.Cliente(self.base)
        email = "fornextest." + uuid.uuid4().hex[:12] + "@gmail.com"
        dados = {"nome": "Cliente", "email": email, "senha": senha, "confirmacao": senha, **extra}
        r = c.req("POST", "/api/cadastro", dados)
        self.assertEqual(r.status, 202, r.corpo)
        self.assertNotIn("usuario", r.corpo)
        c.email, c.senha = email, senha
        return c, r

    def entregar(self, email, finalidade):
        r = subprocess.run([api.PHP, str(api.RAIZ / "site/enviar-emails.php")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        arquivo = Path(os.environ["AUTH_MAIL_CAPTURE"])
        mensagens = [json.loads(l) for l in arquivo.read_text(encoding="utf-8").splitlines()]
        for m in reversed(mensagens):
            if m["email"] == email and (link := re.search(r"#" + finalidade + r"=([a-f0-9]{64})", m["texto"])):
                self.assertNotIn(email, r.stdout + r.stderr)
                return link[1]
        self.fail("Mensagem de teste não capturada.")

    def verificar(self, c):
        token = self.entregar(c.email, "verificar")
        self.assertEqual(c.req("POST", "/api/email/verificar", {"token": token}).status, 200)
        return token

    def logar(self, c):
        return c.req("POST", "/api/login", {"email": c.email, "senha": c.senha})

    def test_cadastro_verificacao_login_plano_consulta_e_worker(self):
        c, _ = self.pendente(papel="admin")
        self.assertIsNone(c.me()["usuario"])
        self.assertEqual(self.logar(c).status, 403)
        for caminho in ["/api/telefones", "/api/admin/telefones", "/api/provas", "/api/perguntas/aberta"]:
            self.assertEqual(c.req("GET", caminho).status, 401)
        token = self.verificar(c)
        self.assertIsNone(c.me()["usuario"])
        self.assertEqual(c.req("POST", "/api/email/verificar", {"token": token}).status, 400)
        cookie = c.cookie_sessao()
        self.assertEqual(self.logar(c).status, 200)
        self.assertNotEqual(cookie, c.cookie_sessao())
        self.assertEqual(c.me()["usuario"]["papel"], "usuario")
        self.assertEqual(c.req("GET", "/api/admin/telefones").status, 403)
        c.assinar()
        p = c.perguntar()
        self.assertEqual(p.status, 201)
        self.assertEqual(api.worker(self.base, "POST", "/api/worker/proxima").status, 200)

    def test_migracao_repetida_preserva_admin_e_cliente_legados(self):
        antes = api.sql("SELECT id,email,senha_hash,papel,email_verificacao_exigida,email_verificado_em FROM usuarios WHERE email LIKE '%@example.invalid' ORDER BY id")
        for _ in range(2):
            subprocess.run([api.PHP, str(api.RAIZ / "site/migrar-autenticacao.php")], check=True, capture_output=True)
        self.assertEqual(antes, api.sql("SELECT id,email,senha_hash,papel,email_verificacao_exigida,email_verificado_em FROM usuarios WHERE email LIKE '%@example.invalid' ORDER BY id"))
        for email, papel in [("admin@example.invalid", "admin"), ("cliente@example.invalid", "usuario")]:
            c = api.Cliente(self.base)
            r = c.req("POST", "/api/login", {"email": email, "senha": "legado-seguro-123"})
            self.assertEqual(r.status, 200)
            self.assertEqual(r["usuario"]["papel"], papel)
            self.assertEqual(c.req("GET", "/api/admin/telefones").status, 200 if papel == "admin" else 403)

    def test_validacao_email_confirmacao_senha_unicode_longa(self):
        c = api.Cliente(self.base)
        base = {"nome": "Nome", "email": "fornextest.valido@gmail.com", "senha": "minha senha exclusiva", "confirmacao": "minha senha exclusiva"}
        for extra in [{"email": "sem-arroba"}, {"email": "x@@gmail.com"}, {"email": "x@"},
                      {"senha": "curta", "confirmacao": "curta"}, {"senha": "s" * 129, "confirmacao": "s" * 129},
                      {"confirmacao": "diferente"}, {"confirmacao": None}]:
            self.assertEqual(c.req("POST", "/api/cadastro", {**base, **extra}).status, 400)
        senha = "á 🚀 especial & # ' " * 5
        novo, _ = self.pendente(senha)
        self.verificar(novo)
        self.assertEqual(self.logar(novo).status, 200)

    def test_duplicado_nao_troca_senha_nem_perfil_nem_revela_conta(self):
        c, original = self.pendente()
        antes = api.sql(f"SELECT senha_hash,papel FROM usuarios WHERE email='{c.email}'")
        outro = api.Cliente(self.base)
        resposta = outro.req("POST", "/api/cadastro", {"nome": "Alterado", "email": c.email.upper(), "senha": "outra senha exclusiva", "confirmacao": "outra senha exclusiva", "papel": "admin"})
        self.assertEqual((resposta.status, resposta.corpo), (original.status, original.corpo))
        self.assertEqual(antes, api.sql(f"SELECT senha_hash,papel FROM usuarios WHERE email='{c.email}'"))
        for caminho in ["/api/email/reenviar", "/api/senha/recuperar"]:
            a = outro.req("POST", caminho, {"email": c.email})
            b = outro.req("POST", caminho, {"email": "fornextest.inexistente@gmail.com"})
            self.assertEqual((a.status, a.corpo), (b.status, b.corpo))

    def test_token_sem_texto_aberto_no_banco_e_fila_apaga_conteudo(self):
        c, resposta = self.pendente()
        antes = api.sql("SELECT conteudo FROM auth_emails")
        self.assertNotIn(c.email, antes)
        token = self.entregar(c.email, "verificar")
        for texto in [antes, api.sql("SELECT token_hash FROM auth_tokens"), json.dumps(resposta.corpo), json.dumps(c.me().corpo)]:
            self.assertNotIn(token, texto)
        self.assertEqual(api.sql("SELECT COUNT(*) FROM auth_emails WHERE conteudo IS NOT NULL"), "0")

    def test_reenvio_invalida_link_anterior_e_link_expirado_nao_funciona(self):
        c, _ = self.pendente()
        antigo = self.entregar(c.email, "verificar")
        self.assertEqual(c.req("POST", "/api/email/reenviar", {"email": c.email}).status, 202)
        novo = self.entregar(c.email, "verificar")
        self.assertNotEqual(antigo, novo)
        self.assertEqual(c.req("POST", "/api/email/verificar", {"token": antigo}).status, 400)
        api.sql("UPDATE auth_tokens SET expira_em=NOW()-INTERVAL 1 SECOND WHERE usado_em IS NULL")
        self.assertEqual(c.req("POST", "/api/email/verificar", {"token": novo}).status, 400)
        self.assertEqual(c.req("POST", "/api/email/verificar", {"token": "0" * 64}).status, 400)

    def test_recuperacao_troca_senha_e_invalida_todas_as_sessoes(self):
        c, _ = self.pendente()
        self.verificar(c)
        self.assertEqual(self.logar(c).status, 200)
        outro = api.Cliente(self.base)
        self.assertEqual(outro.req("POST", "/api/login", {"email": c.email, "senha": c.senha}).status, 200)
        rec = api.Cliente(self.base)
        self.assertEqual(rec.req("POST", "/api/senha/recuperar", {"email": c.email}).status, 202)
        token = self.entregar(c.email, "redefinir")
        dados = {"token": token, "senha": "nova senha exclusiva do FORNEX", "confirmacao": "nova senha exclusiva do FORNEX"}
        self.assertEqual(rec.req("POST", "/api/email/verificar", {"token": token}).status, 400)
        self.assertEqual(rec.req("POST", "/api/senha/redefinir", {**dados, "confirmacao": "diferente"}).status, 400)
        self.assertEqual(rec.req("POST", "/api/senha/redefinir", dados).status, 200)
        for cliente in [c, outro, rec]:
            self.assertIsNone(cliente.me()["usuario"])
            self.assertEqual(cliente.req("GET", "/api/telefones").status, 401)
        self.assertEqual(rec.req("POST", "/api/senha/redefinir", dados).status, 400)
        self.assertEqual(self.logar(c).status, 401)
        c.senha = dados["senha"]
        self.assertEqual(self.logar(c).status, 200)
        self.assertEqual(c.me()["usuario"]["papel"], "usuario")

    def test_token_consumido_uma_vez_com_pedidos_concorrentes(self):
        c, _ = self.pendente()
        token = self.entregar(c.email, "verificar")
        clientes = [api.Cliente(base) for _, base in api.SERVIDORES]
        for cliente in clientes:
            cliente.me()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            resultados = list(pool.map(lambda cliente: cliente.req("POST", "/api/email/verificar", {"token": token}).status, clientes))
        self.assertEqual(sorted(resultados), [200, 400, 400])

    def test_recuperacao_preserva_perfil_administrativo(self):
        c = api.Cliente(self.base)
        c.cadastrar()
        api.sql(f"UPDATE usuarios SET papel='admin' WHERE email='{c.email}'")
        self.assertEqual(c.req("POST", "/api/senha/recuperar", {"email": c.email}).status, 202)
        token = self.entregar(c.email, "redefinir")
        dados = {"token": token, "senha": "nova senha exclusiva do admin", "confirmacao": "nova senha exclusiva do admin"}
        self.assertEqual(c.req("POST", "/api/senha/redefinir", dados).status, 200)
        self.assertIsNone(c.me()["usuario"])
        c.senha = dados["senha"]
        self.assertEqual(self.logar(c).status, 200)
        self.assertEqual(c.me()["usuario"]["papel"], "admin")
        self.assertEqual(c.req("GET", "/api/admin/telefones").status, 200)

    def test_csrf_em_todos_os_novos_endpoints_e_sem_consumo_por_get(self):
        c, _ = self.pendente()
        token = self.entregar(c.email, "verificar")
        for caminho in ["email/reenviar", "email/verificar", "senha/recuperar", "senha/redefinir", "sessao/atividade"]:
            self.assertEqual(c.req("POST", "/api/" + caminho, {"token": token, "email": c.email}, csrf=False).status, 401 if caminho == "sessao/atividade" else 403)
            self.assertEqual(c.req("GET", "/api/" + caminho).status, 405)
        self.assertEqual(api.chamar(self.base, "GET", "/acesso.html").status, 200)
        self.assertEqual(api.sql("SELECT COUNT(*) FROM auth_tokens WHERE usado_em IS NULL"), "1")

    def test_limites_atomicamente_impedem_envio_abusivo(self):
        c = api.Cliente(self.base)
        for _ in range(5):
            self.assertEqual(c.req("POST", "/api/senha/recuperar", {"email": "fornextest.inexistente@gmail.com"}).status, 202)
        r = c.req("POST", "/api/senha/recuperar", {"email": "fornextest.inexistente@gmail.com"})
        self.assertEqual(r.status, 429)
        self.assertEqual(r.cabecalhos["Retry-After"], "900")
        self.assertEqual(api.sql("SELECT COUNT(*) FROM auth_emails"), "0")

    def test_sem_configuracao_de_email_nao_cria_conta_e_preserva_login_existente(self):
        antes = api.sql("SELECT COUNT(*) FROM usuarios")
        with self.servidor(AUTH_MAIL_KEY="") as base:
            c = api.Cliente(base)
            dados = {"nome": "Teste", "email": "fornextest.semcorreio@gmail.com", "senha": "minha frase exclusiva", "confirmacao": "minha frase exclusiva"}
            self.assertEqual(c.req("POST", "/api/cadastro", dados).status, 503)
            self.assertEqual(c.req("POST", "/api/senha/recuperar", {"email": dados["email"]}).status, 503)
            self.assertEqual(c.req("POST", "/api/login", {"email": "admin@example.invalid", "senha": "legado-seguro-123"}).status, 200)
        self.assertEqual(api.sql("SELECT COUNT(*) FROM usuarios"), antes)

    def test_cookie_secure_em_producao_e_captura_desabilitada(self):
        with tempfile.TemporaryDirectory(prefix="fornex-auth-prod-test-") as tmp:
            config = Path(tmp) / "config.php"
            config.write_text(Path(os.environ["FORNEX_CONFIG"]).read_text(encoding="utf-8").replace("const AMBIENTE = 'test'", "const AMBIENTE = 'prod'"), encoding="utf-8")
            with self.servidor(FORNEX_CONFIG=str(config)) as base:
                r = api.chamar(base, "GET", "/api/me")
                self.assertTrue(any("secure" in h.lower() and "httponly" in h.lower() and "SameSite=Lax" in h for h in r.cabecalhos.get_all("Set-Cookie")))
            r = subprocess.run([api.PHP, str(api.RAIZ / "site/enviar-emails.php")], env={**os.environ, "FORNEX_CONFIG": str(config)}, capture_output=True)
            self.assertEqual(r.returncode, 1)

    def test_falha_no_envio_reagenda_sem_expor_destinatario_ou_token(self):
        c, _ = self.pendente()
        with tempfile.TemporaryDirectory(prefix="fornex-auth-falha-test-") as tmp:
            r = subprocess.run([api.PHP, str(api.RAIZ / "site/enviar-emails.php")],
                               env={**os.environ, "AUTH_MAIL_CAPTURE": str(Path(tmp) / "ausente" / "email.jsonl")},
                               capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn(c.email, r.stdout + r.stderr)
        self.assertEqual(api.sql("SELECT tentativas FROM auth_emails"), "1")
        self.assertEqual(api.sql("SELECT COUNT(*) FROM auth_emails WHERE reserva IS NULL AND enviado_em IS NULL AND conteudo IS NOT NULL AND disponivel_em > NOW()"), "1")
        api.sql("UPDATE auth_emails SET disponivel_em=NOW()")
        self.verificar(c)

    def test_smtp_com_tls_e_autenticacao_sem_servidor_externo(self):
        c, _ = self.pendente()
        with tempfile.TemporaryDirectory(prefix="fornex-auth-tls-test-") as tmp:
            pasta = Path(tmp)
            certificado, chave = pasta / "cert.pem", pasta / "key.pem"
            cfg = pasta / "openssl.cnf"
            cfg.write_text("[req]\ndistinguished_name=dn\nx509_extensions=v3\n[dn]\n[v3]\nsubjectAltName=IP:127.0.0.1\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,digitalSignature,keyEncipherment,keyCertSign\n", encoding="ascii")
            ambiente = {**os.environ, "AUTH_TLS_CONFIG": str(cfg), "AUTH_TLS_CERT": str(certificado), "AUTH_TLS_KEY": str(chave)}
            codigo = """<?php
            $op = ['config' => getenv('AUTH_TLS_CONFIG'), 'digest_alg' => 'sha256', 'private_key_bits' => 2048];
            $key = openssl_pkey_new($op);
            $csr = openssl_csr_new(['commonName' => '127.0.0.1'], $key, $op);
            $crt = openssl_csr_sign($csr, null, $key, 1, $op);
            if (!$crt || !openssl_x509_export_to_file($crt, getenv('AUTH_TLS_CERT'))
                || !openssl_pkey_export_to_file($key, getenv('AUTH_TLS_KEY'), null, $op)) exit(1);
            """
            r = subprocess.run([api.PHP], input=codigo, env=ambiente, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "Não foi possível criar certificado TLS temporário.")
            contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            contexto.load_cert_chain(str(certificado), str(chave))
            recebido = []
            falhas = []
            autenticou = []
            comandos = []
            with socket.socket() as escuta:
                escuta.bind(("127.0.0.1", 0))
                escuta.listen(1)
                escuta.settimeout(15)
                porta = escuta.getsockname()[1]
                def smtp():
                    try:
                        conn, _ = escuta.accept()
                        with contexto.wrap_socket(conn, server_side=True) as tls:
                            tls.settimeout(15)
                            fluxo = tls.makefile("rwb")
                            def enviar(linha):
                                fluxo.write(linha + b"\r\n")
                                fluxo.flush()
                            enviar(b"220 localhost teste")
                            while linha := fluxo.readline():
                                comando = linha.split(b" ", 1)[0].strip().upper()
                                comandos.append(comando.decode('ascii', errors='replace'))
                                if comando == b"EHLO":
                                    enviar(b"250-localhost\r\n250 AUTH PLAIN")
                                elif comando == b"AUTH":
                                    if len(linha.split()) < 3:
                                        enviar(b"334 ")
                                        fluxo.readline()  # resposta SASL do cliente, nunca registrada
                                    autenticou.append(True)
                                    enviar(b"235 autenticado")
                                elif comando in [b"MAIL", b"RCPT", b"RSET"]:
                                    enviar(b"250 ok")
                                elif comando == b"DATA":
                                    enviar(b"354 mensagem")
                                    corpo = bytearray()
                                    while (parte := fluxo.readline()) and parte != b".\r\n":
                                        corpo.extend(parte)
                                    recebido.append(bytes(corpo))
                                    enviar(b"250 recebido")
                                elif comando == b"QUIT":
                                    enviar(b"221 fim")
                                    break
                                else:
                                    enviar(b"500 comando desconhecido")
                    except Exception as e:
                        falhas.append(type(e).__name__)
                thread = threading.Thread(target=smtp, daemon=True)
                thread.start()
                ambiente.update(MAIL_TRANSPORT="smtp", SMTP_HOST="127.0.0.1", SMTP_PORT=str(porta), SMTP_SECURITY="ssl",
                                SMTP_USER="teste-local", SMTP_PASS="credencial-ficticia", MAIL_FROM="fornex@example.invalid", APP_URL="https://fornex.example.invalid")
                r = subprocess.run([api.PHP, "-d", "openssl.cafile=" + str(certificado), str(api.RAIZ / "site/enviar-emails.php")],
                                   env=ambiente, capture_output=True, text=True, timeout=30)
                thread.join(timeout=16)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr + repr([falhas, comandos]))
            self.assertEqual(falhas, [])
            self.assertEqual(autenticou, [True])
            self.assertEqual(len(recebido), 1)
            self.assertIn(c.email.encode(), recebido[0])
            self.assertNotIn(c.email, r.stdout + r.stderr)
            self.assertEqual(api.sql("SELECT COUNT(*) FROM auth_emails WHERE enviado_em IS NOT NULL AND conteudo IS NULL"), "1")

    def test_logout_apaga_cookie_e_sessao_expira_sem_atividade(self):
        c = api.Cliente(self.base)
        c.cadastrar()
        sessao = Path(os.environ["AUTH_TEST_SESSION_PATH"]) / ("sess_" + c.cookie_sessao())
        original = sessao.read_text(encoding="utf-8")
        sessao.write_text(re.sub(r"ativa_em\|i:\d+;", "ativa_em|i:1;", original), encoding="utf-8")
        self.assertIsNone(c.me()["usuario"])
        self.assertEqual(c.req("GET", "/api/telefones").status, 401)
        self.assertEqual(self.logar(c).status, 200)
        sessao = sessao.parent / ("sess_" + c.cookie_sessao())
        original = sessao.read_text(encoding="utf-8")
        sessao.write_text(re.sub(r"criada_em\|i:\d+;", "criada_em|i:1;", original), encoding="utf-8")
        self.assertIsNone(c.me()["usuario"])
        self.assertEqual(self.logar(c).status, 200)
        cookie = c.cookie_sessao()
        r = c.req("POST", "/api/logout")
        self.assertEqual(r.status, 200)
        self.assertIsNone(c.cookie_sessao())
        self.assertFalse((sessao.parent / ("sess_" + cookie)).exists())

    @unittest.skipUnless(os.environ.get("FORNEX_PLAYWRIGHT_MODULE"), "Playwright opcional: defina FORNEX_PLAYWRIGHT_MODULE")
    def test_interface_no_navegador(self):
        r = subprocess.run(["node", str(api.RAIZ / "site/dev/test_auth_ui.cjs")],
                           env={**os.environ, "FORNEX_UI_BASE": self.base}, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
