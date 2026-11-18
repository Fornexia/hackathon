"""Regressões da auditoria; executadas somente pelo ambiente descartável de test_auth.py."""
import concurrent.futures
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import unittest.mock
import uuid

import test_api as api
import test_prova

setUpModule = api.setUpModule
tearDownModule = api.tearDownModule
spec = importlib.util.spec_from_file_location("carga", api.RAIZ / "bench/carga.py")
carga = importlib.util.module_from_spec(spec)
spec.loader.exec_module(carga)


class TestAuditoria(api.Base):
    def docker_bash(self, script, *args):
        resultado = subprocess.run(
            ["docker", "exec", "-i", "-e", "MYSQL_PWD", api.CONTAINER, "bash", "-s", "--", *args],
            input=script.encode("utf-8"), capture_output=True,
            env={**os.environ, "MYSQL_PWD": os.environ["DB_TEST_ROOT_PASSWORD"]}, timeout=60)
        resultado.stdout = resultado.stdout.decode("utf-8", errors="replace")
        resultado.stderr = resultado.stderr.decode("utf-8", errors="replace")
        return resultado

    def test_login_concorrente_nao_ultrapassa_cinco_falhas(self):
        for _ in range(2):
            api.sql("DELETE FROM tentativas_login")
            clientes = [api.Cliente(api.SERVIDORES[i % 3][1]) for i in range(6)]
            for c in clientes:
                c.me()
            barreira = threading.Barrier(6)
            email = "fornextest." + uuid.uuid4().hex[:12] + "@gmail.com"
            def falhar(c):
                barreira.wait(timeout=15)
                return c.req("POST", "/api/login", {"email": email, "senha": "errada"}).status
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                resultados = list(executor.map(falhar, clientes))
            self.assertEqual(sorted(resultados), [401] * 5 + [429])
            self.assertEqual(api.sql(f"SELECT COUNT(*) FROM tentativas_login WHERE email='{email}'"), "5")

    def test_limites_globais_de_ip_e_email_e_liberacao_das_travas(self):
        c = api.Cliente(self.base)
        c.cadastrar()
        for i in range(20):
            api.sql(f"INSERT INTO tentativas_login (email,ip) VALUES ('outra{i}@example.invalid','127.0.0.1')")
        self.assertEqual(c.req("POST", "/api/login", {"email": c.email, "senha": c.senha}).status, 429)
        api.sql("DELETE FROM tentativas_login")
        for i in range(30):
            api.sql(f"INSERT INTO tentativas_login (email,ip) VALUES ('{c.email}','192.0.2.{i + 1}')")
        self.assertEqual(c.req("POST", "/api/login", {"email": c.email, "senha": c.senha}).status, 429)
        api.sql("DELETE FROM tentativas_login")
        self.assertEqual(c.req("POST", "/api/login", {"email": c.email, "senha": c.senha}).status, 200)

    def test_coletor_php_preserva_25_minutos_e_aplicacao_expira_31(self):
        porta = api.porta_livre()
        base = f"http://127.0.0.1:{porta}"
        p = subprocess.Popen([api.PHP, "-d", "session.gc_probability=1", "-d", "session.gc_divisor=1",
                              "-d", "session.gc_maxlifetime=1440", "-S", f"127.0.0.1:{porta}",
                              "-t", str(api.RAIZ / "site/public_html"), str(api.RAIZ / "site/dev/router.php")],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(60):
                try:
                    api.chamar(base, "GET", "/api/saude")
                    break
                except OSError:
                    time.sleep(0.1)
            c = api.Cliente(base)
            c.cadastrar()
            arquivo = Path(os.environ["AUTH_SESSION_PATH"]) / ("sess_" + c.cookie_sessao())
            original = arquivo.read_text(encoding="utf-8")
            agora = int(time.time())
            arquivo.write_text(re.sub(r"ativa_em\|i:\d+;", f"ativa_em|i:{agora - 1500};", original), encoding="utf-8")
            os.utime(arquivo, (agora - 1500, agora - 1500))
            api.Cliente(base).me()  # Outra sessão provoca GC, sem tocar no arquivo autenticado.
            self.assertTrue(arquivo.exists(), "GC apagou uma sessão ainda válida")
            self.assertIsNotNone(c.me()["usuario"])
            arquivo.write_text(re.sub(r"ativa_em\|i:\d+;", f"ativa_em|i:{agora - 1860};", original), encoding="utf-8")
            self.assertIsNone(c.me()["usuario"])
        finally:
            p.terminate()
            p.wait(timeout=10)

    def test_prova_nao_le_configuracao_privada_mesmo_se_existir(self):
        proibido = api.RAIZ / "site/hackathon-config.php"
        ler = Path.read_text
        def seguro(caminho, *args, **kwargs):
            if caminho.resolve() == proibido.resolve():
                raise AssertionError("Teste tentou ler configuração privada")
            return ler(caminho, *args, **kwargs)
        caso = test_prova.TestSemSegredo("test_arquivo_exportado_nao_tem_segredo_chave_nem_caminho_interno")
        caso.base = self.base
        with unittest.mock.patch.object(Path, "read_text", seguro):
            caso.test_arquivo_exportado_nao_tem_segredo_chave_nem_caminho_interno()

    def test_benchmark_login_legado_e_verificado_sem_cadastro_automatico(self):
        def sessao():
            return carga.Sessao(self.base, {"requisicoes": 0, "tempos": [], "erros_500": 0}, threading.Lock())
        s = sessao()
        self.assertTrue(s.entrar("cliente@example.invalid", "Cliente", "legado-seguro-123"))
        c = api.Cliente(self.base)
        c.cadastrar()
        self.assertTrue(sessao().entrar(c.email, "Cliente", c.senha))
        api.sql(f"UPDATE usuarios SET email_verificado_em=NULL WHERE email='{c.email}'")
        self.assertFalse(sessao().entrar(c.email, "Pendente", c.senha))
        email = "fornextest." + uuid.uuid4().hex[:12] + "@gmail.com"
        self.assertFalse(sessao().entrar(email, "Ausente", "uma senha segura de teste"))
        self.assertEqual(api.sql(f"SELECT COUNT(*) FROM usuarios WHERE email='{email}'"), "0")

    def test_backup_real_restaura_dados_e_migracao_e_reexecutavel(self):
        c = self.cliente_com_plano()
        c.perguntar()
        tabelas = api.sql("SHOW TABLES").splitlines()
        nomes = ','.join('`' + t + '`' for t in tabelas)
        antes = api.sql("CHECKSUM TABLE " + nomes)
        for _ in range(2):
            subprocess.run([api.PHP, str(api.RAIZ / "site/migrar-autenticacao.php")], check=True, capture_output=True)
        self.assertEqual(api.sql("CHECKSUM TABLE " + nomes), antes)
        helper = (api.RAIZ / "site/backup-banco.sh").read_text(encoding="utf-8")
        # Cria só um segundo banco de prefixo reservado dentro do contêiner descartável.
        clone = api.BANCO + "_restore"
        script = 'set -euo pipefail\ntrabalho=$(mktemp -d)\ntrap \'rm -rf -- "$trabalho"\' EXIT\n'
        script += 'cat > "$trabalho/backup.sh" <<\'FORNEX_HELPER\'\n' + helper + '\nFORNEX_HELPER\n'
        script += 'bash "$trabalho/backup.sh" 127.0.0.1 3306 root "$1" "$trabalho/banco.gz" atualizar\n'
        script += 'test "$(stat -c %a "$trabalho/banco.gz")" = 600\n'
        script += 'mariadb -uroot -e "CREATE DATABASE \\`$2\\`"\ngzip -cd "$trabalho/banco.gz" | mariadb -uroot "$2"\n'
        r = self.docker_bash(script, api.BANCO, clone)
        self.assertEqual(r.returncode, 0, r.stderr)
        try:
            depois = api.sql("CHECKSUM TABLE " + ','.join(f'`{clone}`.`{t}`' for t in tabelas))
            self.assertEqual([l.split('\t')[-1] for l in antes.splitlines()], [l.split('\t')[-1] for l in depois.splitlines()])
        finally:
            api.sql(f"DROP DATABASE `{clone}`")

    def test_backup_recusa_dump_parcial_preserva_destino_e_respeita_porta(self):
        self.verificar_backup_falso("parcial")

    def test_backup_vazio_so_permitido_na_instalacao(self):
        self.verificar_backup_falso("vazio")

    def verificar_backup_falso(self, caso):
        helper = (api.RAIZ / "site/backup-banco.sh").read_text(encoding="utf-8")
        script = '''set -euo pipefail
trabalho=$(mktemp -d)
trap 'rm -rf -- "$trabalho"' EXIT
cat > "$trabalho/backup.sh" <<'FORNEX_HELPER'
''' + helper + '''
FORNEX_HELPER
export MYSQL_CLIENT_BIN="$trabalho/client" MYSQL_DUMP_BIN="$trabalho/dump"
cat > "$MYSQL_CLIENT_BIN" <<'CLIENT'
#!/bin/bash
[[ " $* " == *" --port=3317 "* ]] || exit 81
if [[ "$CASO" == vazio ]]; then echo 0; else echo 1; fi
CLIENT
cat > "$MYSQL_DUMP_BIN" <<'DUMP'
#!/bin/bash
[[ " $* " == *" --port=3317 "* ]] || exit 82
if [[ "$CASO" == parcial ]]; then echo 'CREATE TABLE parcial (id INT);'; exit 42; fi
echo '-- Empty database dump completed'
DUMP
chmod +x "$MYSQL_CLIENT_BIN" "$MYSQL_DUMP_BIN"
export CASO="$1"
echo 'backup anterior' > "$trabalho/final.gz"
if bash "$trabalho/backup.sh" localhost 3317 teste teste "$trabalho/final.gz" atualizar; then exit 90; fi
test "$(cat "$trabalho/final.gz")" = 'backup anterior'
test -z "$(find "$trabalho" -name '*.parcial.*' -print)"
if [[ "$CASO" == vazio ]]; then
  bash "$trabalho/backup.sh" localhost 3317 teste teste "$trabalho/novo.gz" instalar
  gzip -t "$trabalho/novo.gz"
else
  if bash "$trabalho/backup.sh" localhost 3317 teste teste "$trabalho/novo.gz" instalar; then exit 91; fi
  test ! -e "$trabalho/novo.gz"
fi
'''
        r = self.docker_bash(script, caso)
        self.assertEqual(r.returncode, 0, r.stderr)
