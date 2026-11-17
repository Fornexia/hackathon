"""Regressões da entrega 1; apenas dentro do executor de autenticação descartável."""
import base64
import json
import os
import subprocess
import uuid

import test_api as api
import test_auth as auth

setUpModule = api.setUpModule
tearDownModule = api.tearDownModule


class TestAjustes(api.Base):
    entregar = auth.TestAuthPublica.entregar

    def setUp(self):
        super().setUp()
        api.sql("DELETE FROM auth_emails; DELETE FROM auth_tokens")

    def test_dominio_corporativo_aceito_e_formato_invalido_recusado(self):
        c = api.Cliente(self.base)
        senha = "uma frase exclusiva FORNEX!"
        email = "fornextest." + uuid.uuid4().hex[:12] + "@empresa.example"
        dados = {"nome": "Cliente", "email": email, "senha": senha, "confirmacao": senha}
        self.assertEqual(c.req("POST", "/api/cadastro", dados).status, 202)
        self.assertIsNone(c.me()["usuario"])
        for invalido in ["sem-arroba", "x@@empresa.example", "x@", "a" * 191 + "@example.com"]:
            self.assertEqual(c.req("POST", "/api/cadastro", {**dados, "email": invalido}).status, 400)
        token = self.entregar(email, "verificar")
        self.assertEqual(c.req("POST", "/api/email/verificar", {"token": token}).status, 200)
        login = c.req("POST", "/api/login", {"email": email, "senha": senha})
        self.assertEqual(login.status, 200)
        self.assertTrue(login["usuario"]["email_verificado"])
        self.assertTrue(c.me()["usuario"]["email_verificado"])

    def test_conta_antiga_verifica_proprio_email_sem_mudar_regra_ou_papel(self):
        email = "cliente@example.invalid"
        api.sql(f"UPDATE usuarios SET email_verificado_em=NULL WHERE email='{email}'")
        c = api.Cliente(self.base)
        login = c.req("POST", "/api/login", {"email": email, "senha": "legado-seguro-123"})
        self.assertEqual(login.status, 200)
        self.assertFalse(login["usuario"]["email_verificado"])
        self.assertFalse(c.me()["usuario"]["email_verificado"])
        antes = api.sql(f"SELECT senha_hash,papel,email_verificacao_exigida FROM usuarios WHERE email='{email}'")
        self.assertEqual(c.req("POST", "/api/email/verificar-conta", {"email": "admin@example.invalid"}).status, 202)
        self.assertEqual(api.sql("SELECT COUNT(*) FROM auth_tokens t JOIN usuarios u ON u.id=t.usuario_id WHERE u.papel='admin'"), "0")
        token = self.entregar(email, "verificar")
        self.assertEqual(c.req("POST", "/api/email/verificar", {"token": token}).status, 200)
        self.assertTrue(c.me()["usuario"]["email_verificado"])
        self.assertEqual(api.sql(f"SELECT senha_hash,papel,email_verificacao_exigida FROM usuarios WHERE email='{email}'"), antes)
        quantidade = api.sql("SELECT COUNT(*) FROM auth_tokens")
        self.assertEqual(c.req("POST", "/api/email/verificar-conta", {}).status, 202)
        self.assertEqual(api.sql("SELECT COUNT(*) FROM auth_tokens"), quantidade)
        api.sql(f"UPDATE usuarios SET email_verificado_em=NULL WHERE email='{email}'")

    def test_verificar_conta_exige_login_e_csrf(self):
        c = api.Cliente(self.base)
        self.assertEqual(c.req("POST", "/api/email/verificar-conta", {}).status, 401)
        self.assertEqual(c.req("POST", "/api/login", {"email": "cliente@example.invalid", "senha": "legado-seguro-123"}).status, 200)
        self.assertEqual(c.req("POST", "/api/email/verificar-conta", {}, csrf=False).status, 403)
        self.assertEqual(api.sql("SELECT COUNT(*) FROM auth_tokens"), "0")

    def test_proxy_exige_remetente_confiavel_e_usa_ultimo_ip_valido(self):
        casos = [
            ("", "192.0.2.10", "198.51.100.20", "192.0.2.10"),
            ("192.0.2.10", "192.0.2.10", "203.0.113.1, 198.51.100.20", "198.51.100.20"),
            ("192.0.2.11", "192.0.2.10", "198.51.100.20", "192.0.2.10"),
            ("192.0.2.10", "192.0.2.10", "forjado, 2001:db8::1, invalido", "2001:db8::1"),
            ("192.0.2.10", "192.0.2.10", "invalido", "192.0.2.10"),
        ]
        for proxies, remoto, header, esperado in casos:
            with self.subTest(proxies=proxies, remoto=remoto, header=header):
                payload = base64.b64encode(json.dumps({"REMOTE_ADDR": remoto, "HTTP_X_FORWARDED_FOR": header}).encode()).decode()
                pasta = (api.RAIZ / "site/public_html/api").as_posix()
                codigo = f"<?php define('API', true); require '{pasta}/lib_base.php'; require '{pasta}/lib_auth.php'; $_SERVER=json_decode(base64_decode('{payload}'),true); echo ip_do_cliente();"
                r = subprocess.run([api.PHP], input=codigo.encode(), capture_output=True, env={**os.environ, "TRUSTED_PROXIES": proxies})
                self.assertEqual(r.returncode, 0, r.stderr.decode())
                self.assertEqual(r.stdout.decode(), esperado)
