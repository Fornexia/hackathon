"""Testes de scripts/backup.py. Não usam Docker de verdade (as chamadas ao Docker são trocadas por dublês) nem tocam o projeto real.

    python -m unittest discover -s scripts/testes -v
"""

import contextlib
import io
import json
import os
import sys
import tarfile
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backup  # noqa: E402

SENHA = "uma-senha-longa-de-teste"


def montar_projeto(raiz: Path, env="NEO4J_SENHA=abc\nOUTRA=1\n") -> None:
    (raiz / "api").mkdir(parents=True, exist_ok=True)
    (raiz / "dados" / "alertas").mkdir(parents=True, exist_ok=True)
    (raiz / "dados" / "externas").mkdir(parents=True, exist_ok=True)
    (raiz / ".env").write_text(env, encoding="utf-8")
    (raiz / "google-sa.json").write_text('{"tipo": "conta"}', encoding="utf-8")
    (raiz / "api" / "chaves.json").write_text('{"hash": {"cliente": "x"}}', encoding="utf-8")
    (raiz / "dados" / "alertas" / "assinaturas.json").write_text('[{"email": "a@b.com"}]', encoding="utf-8")
    (raiz / "dados" / "externas" / "ceis.csv").write_bytes(b"col1;col2\n" * 5000)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.raiz = self.dir / "origem"
        self.wa = self.dir / "wa-origem"
        self.saida = self.dir / "backups"
        (self.wa / "auth").mkdir(parents=True)
        (self.wa / "midia").mkdir()
        (self.wa / "auth" / "creds.json").write_text('{"sessao": 1}', encoding="utf-8")
        (self.wa / "midia" / "foto.jpg").write_bytes(b"x" * 1000)
        montar_projeto(self.raiz)
        patcher = mock.patch.dict(os.environ, {"WHATSAPP_STATE_DIR": str(self.wa)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def criar(self, **kw):
        return backup.criar(self.raiz, self.saida, SENHA, sem_grafo=True, **kw)

    def novo_destino(self):
        d = self.dir / f"destino-{time.monotonic_ns()}"
        d.mkdir()
        return d


class TestCifra(Base):
    def escrever(self, tamanho):
        origem = self.dir / "claro.bin"
        origem.write_bytes(os.urandom(tamanho))
        return origem

    def test_ida_e_volta_com_varios_pedacos(self):
        with mock.patch.object(backup, "PEDACO", 64):
            origem = self.escrever(64 * 5 + 7)
            cifrado, claro = self.dir / "c.fxbak", self.dir / "claro2.bin"
            backup.cifrar(origem, cifrado, SENHA)
            backup.decifrar(cifrado, claro, SENHA)
        self.assertEqual(claro.read_bytes(), origem.read_bytes())

    def test_arquivo_vazio_e_multiplo_exato_do_pedaco(self):
        with mock.patch.object(backup, "PEDACO", 64):
            for tamanho in (0, 64, 128):
                origem = self.escrever(tamanho)
                cifrado, claro = self.dir / "c.fxbak", self.dir / "claro2.bin"
                backup.cifrar(origem, cifrado, SENHA)
                backup.decifrar(cifrado, claro, SENHA)
                self.assertEqual(claro.read_bytes(), origem.read_bytes(), tamanho)

    def test_senha_errada_e_recusada(self):
        origem = self.escrever(500)
        cifrado = self.dir / "c.fxbak"
        backup.cifrar(origem, cifrado, SENHA)
        with self.assertRaisesRegex(backup.ErroDeBackup, "senha incorreta"):
            backup.decifrar(cifrado, self.dir / "x", "outra-senha-qualquer")

    def test_texto_cifrado_nao_contem_o_conteudo(self):
        origem = self.dir / "claro.bin"
        origem.write_bytes(b"SEGREDO-MUITO-RECONHECIVEL" * 100)
        cifrado = self.dir / "c.fxbak"
        backup.cifrar(origem, cifrado, SENHA)
        self.assertNotIn(b"SEGREDO", cifrado.read_bytes())

    def test_duas_cifragens_do_mesmo_arquivo_diferem(self):
        origem = self.escrever(300)
        a, b = self.dir / "a.fxbak", self.dir / "b.fxbak"
        backup.cifrar(origem, a, SENHA)
        backup.cifrar(origem, b, SENHA)
        self.assertNotEqual(a.read_bytes(), b.read_bytes())

    def test_adulteracao_truncamento_e_emenda_sao_detectados(self):
        with mock.patch.object(backup, "PEDACO", 64):
            origem = self.escrever(64 * 4)
            cifrado = self.dir / "c.fxbak"
            backup.cifrar(origem, cifrado, SENHA)
            bruto = cifrado.read_bytes()
            casos = {
                "byte no meio": bruto[:100] + bytes([bruto[100] ^ 1]) + bruto[101:],
                "byte no fim": bruto[:-1] + bytes([bruto[-1] ^ 1]),
                "byte do sal (cabeçalho)": bruto[:10] + bytes([bruto[10] ^ 1]) + bruto[11:],
                "sem o último bloco": bruto[: len(bruto) - (4 + 64 + 16)],
                "cortado ao meio de um bloco": bruto[:-20],
                "lixo no fim": bruto + b"\x00",
                "bloco repetido": bruto + bruto[backup.TAMANHO_CABECALHO:],
            }
            # um bloco do meio removido (os números de ordem deixam de bater)
            tam_bloco = 4 + 64 + 16
            casos["bloco do meio removido"] = bruto[: backup.TAMANHO_CABECALHO + tam_bloco] + bruto[backup.TAMANHO_CABECALHO + 2 * tam_bloco:]
            for nome, conteudo in casos.items():
                alterado = self.dir / "alterado.fxbak"
                alterado.write_bytes(conteudo)
                with self.assertRaises(backup.ErroDeBackup, msg=nome):
                    backup.decifrar(alterado, self.dir / "saida.bin", SENHA)

    def test_arquivo_que_nao_e_backup(self):
        lixo = self.dir / "lixo.bin"
        lixo.write_bytes(b"isto nao e um backup" * 10)
        with self.assertRaisesRegex(backup.ErroDeBackup, "não é um backup"):
            backup.decifrar(lixo, self.dir / "saida.bin", SENHA)
        lixo.write_bytes(b"")
        with self.assertRaises(backup.ErroDeBackup):
            backup.decifrar(lixo, self.dir / "saida.bin", SENHA)


class TestCriarEVerificar(Base):
    def test_cria_um_arquivo_cifrado_e_verifica(self):
        arq = self.criar()
        self.assertTrue(arq.name.startswith("fornexia-") and arq.suffix == ".fxbak")
        self.assertNotIn(b"NEO4J_SENHA", arq.read_bytes())
        manifesto = backup.verificar(arq, SENHA)
        nomes = {a["nome"] for a in manifesto["arquivos"]}
        self.assertEqual(nomes, {"projeto/.env", "projeto/google-sa.json", "projeto/api/chaves.json", "projeto/dados/alertas/assinaturas.json",
                                 "projeto/dados/externas/ceis.csv", "whatsapp/auth/creds.json"})
        self.assertFalse(manifesto["grafo"]["incluido"])

    def test_midia_do_whatsapp_nao_entra_e_as_opcoes_de_omissao_funcionam(self):
        sem = self.criar(sem_dados=True, sem_whatsapp=True)
        nomes = {a["nome"] for a in backup.verificar(sem, SENHA)["arquivos"]}
        self.assertEqual(nomes, {"projeto/.env", "projeto/google-sa.json", "projeto/api/chaves.json"})

    def test_senha_errada_na_verificacao(self):
        arq = self.criar()
        with self.assertRaises(backup.ErroDeBackup):
            backup.verificar(arq, "senha-errada-1234")

    def test_rotacao_guarda_so_os_mais_novos(self):
        base = datetime(2026, 11, 16, 10, 0, 0).astimezone()
        for i in range(4):
            self.criar(manter=2, agora=base + timedelta(seconds=i))
        nomes = sorted(p.name for p in self.saida.glob("fornexia-*.fxbak"))
        self.assertEqual(len(nomes), 2)
        self.assertTrue(nomes[0].endswith("100002.fxbak") and nomes[1].endswith("100003.fxbak"))

    def test_senha_curta_e_recusada_na_criacao(self):
        with mock.patch.dict(os.environ, {"BACKUP_SENHA": "curta"}):
            with self.assertRaisesRegex(backup.ErroDeBackup, "pelo menos"):
                backup._senha(confirmar=True, avisar_tamanho=True)
            self.assertEqual(backup._senha(confirmar=False, avisar_tamanho=False), "curta")   # restaurar aceita qualquer senha

    def test_sem_senha_e_sem_terminal_falha_com_mensagem(self):
        with mock.patch.dict(os.environ, {"BACKUP_SENHA": ""}), mock.patch.object(sys.stdin, "isatty", return_value=False):
            with self.assertRaisesRegex(backup.ErroDeBackup, "BACKUP_SENHA"):
                backup._senha(confirmar=True, avisar_tamanho=True)


class TestSenhaGerada(Base):
    FIXA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

    def criar_gerando(self, digitadas, env=None, tty=True):
        entradas = iter(digitadas)
        saida = io.StringIO()
        with mock.patch.object(backup, "RAIZ", self.raiz), mock.patch.object(sys.stdin, "isatty", return_value=tty), \
                mock.patch.object(backup.getpass, "getpass", side_effect=lambda _p="": next(entradas)), \
                mock.patch.object(backup, "gerar_senha", return_value=self.FIXA), \
                mock.patch.dict(os.environ, {"BACKUP_SENHA": "", **(env or {})}), contextlib.redirect_stdout(saida), contextlib.redirect_stderr(io.StringIO()):
            codigo = backup.main(["criar", "--gerar-senha", "--sem-grafo", "--destino", str(self.saida)])
        return codigo, saida.getvalue()

    def test_formato_e_aleatoriedade(self):
        a, b = backup.gerar_senha(), backup.gerar_senha()
        self.assertRegex(a, r"^[A-Z2-7]{32}$")
        self.assertNotEqual(a, b)
        f = backup.formatar_senha(a)
        self.assertRegex(f, r"^([A-Z2-7]{4}-){7}[A-Z2-7]{4}$")
        self.assertEqual(f.replace("-", ""), a)

    def test_normalizar_aceita_variacoes_e_nao_mexe_em_outras_senhas(self):
        a = backup.gerar_senha()
        f = backup.formatar_senha(a)
        for variante in (f, f.lower(), f.replace("-", " "), "  " + f + "\n", a.lower(), a):
            self.assertEqual(backup.normalizar_senha(variante), a)
        self.assertEqual(backup.normalizar_senha("minha senha longa e boa"), "minha senha longa e boa")
        self.assertEqual(backup.normalizar_senha("ABCD-EFGH"), "ABCD-EFGH")

    def test_fluxo_gera_mostra_uma_vez_confirma_e_cria(self):
        codigo, texto = self.criar_gerando([backup.formatar_senha(self.FIXA).lower()])      # confirma digitando em minúsculas e com hífens
        self.assertEqual(codigo, 0)
        self.assertEqual(texto.count(backup.formatar_senha(self.FIXA)), 1)                  # a senha aparece uma única vez
        self.assertGreater(texto.index("\033[2J"), texto.index(backup.formatar_senha(self.FIXA)))   # e a tela é limpa depois dela
        arq = next(self.saida.glob("fornexia-*.fxbak"))
        backup.verificar(arq, self.FIXA)
        for variante in (backup.formatar_senha(self.FIXA), self.FIXA.lower(), backup.formatar_senha(self.FIXA).replace("-", " ")):
            with mock.patch.dict(os.environ, {"BACKUP_SENHA": variante}), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(backup.main(["verificar", str(arq)]), 0, variante)

    def test_confirmacao_errada_tres_vezes_nao_cria_backup(self):
        codigo, _ = self.criar_gerando(["errada", "errada2", "errada3"])
        self.assertEqual(codigo, 1)
        self.assertEqual(list(self.saida.glob("*.fxbak")) if self.saida.exists() else [], [])

    def test_confirmacao_certa_na_segunda_tentativa(self):
        codigo, _ = self.criar_gerando(["errada", self.FIXA])
        self.assertEqual(codigo, 0)

    def test_sem_terminal_ou_com_senha_no_ambiente_e_recusado(self):
        self.assertEqual(self.criar_gerando([], tty=False)[0], 1)
        self.assertEqual(self.criar_gerando([], env={"BACKUP_SENHA": "alguma-senha-longa-1"})[0], 1)
        self.assertEqual(list(self.saida.glob("*.fxbak")) if self.saida.exists() else [], [])


class TestRestaurar(Base):
    def test_restaura_em_outra_maquina(self):
        arq = self.criar()
        novo = self.novo_destino()
        wa_novo = self.dir / "wa-novo"
        with mock.patch.dict(os.environ, {"WHATSAPP_STATE_DIR": str(wa_novo)}):
            backup.restaurar(arq, SENHA, novo, sem_grafo=True)
        for rel in (".env", "google-sa.json", "api/chaves.json", "dados/alertas/assinaturas.json", "dados/externas/ceis.csv"):
            self.assertEqual((novo / rel).read_bytes(), (self.raiz / rel).read_bytes(), rel)
        self.assertEqual((wa_novo / "auth" / "creds.json").read_text(encoding="utf-8"), '{"sessao": 1}')
        self.assertFalse((wa_novo / "midia").exists())

    def test_conflito_sem_forcar_nao_escreve_nada(self):
        arq = self.criar()
        novo = self.novo_destino()
        (novo / ".env").write_text("OUTRO=1\n", encoding="utf-8")
        wa_novo = self.dir / "wa-novo"
        with mock.patch.dict(os.environ, {"WHATSAPP_STATE_DIR": str(wa_novo)}):
            with self.assertRaisesRegex(backup.ErroDeBackup, "Nada foi escrito"):
                backup.restaurar(arq, SENHA, novo, sem_grafo=True)
        self.assertEqual((novo / ".env").read_text(encoding="utf-8"), "OUTRO=1\n")
        self.assertFalse((novo / "dados").exists())
        self.assertFalse(wa_novo.exists())

    def test_forcar_guarda_o_arquivo_antigo_ao_lado(self):
        arq = self.criar()
        novo = self.novo_destino()
        (novo / ".env").write_text("OUTRO=1\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"WHATSAPP_STATE_DIR": str(self.dir / "wa-novo")}):
            backup.restaurar(arq, SENHA, novo, forcar=True, sem_grafo=True)
        self.assertEqual((novo / ".env").read_text(encoding="utf-8"), "NEO4J_SENHA=abc\nOUTRA=1\n")
        antigos = list(novo.glob(".env.antes-*"))
        self.assertEqual(len(antigos), 1)
        self.assertEqual(antigos[0].read_text(encoding="utf-8"), "OUTRO=1\n")

    def test_restaurar_duas_vezes_e_idempotente(self):
        arq = self.criar()
        novo = self.novo_destino()
        with mock.patch.dict(os.environ, {"WHATSAPP_STATE_DIR": str(self.dir / "wa-novo")}):
            backup.restaurar(arq, SENHA, novo, sem_grafo=True)
            backup.restaurar(arq, SENHA, novo, sem_grafo=True)      # nada difere: sem conflito, sem .antes
        self.assertEqual(list(novo.glob("*.antes-*")), [])

    def test_senha_errada_nao_escreve_nada(self):
        arq = self.criar()
        novo = self.novo_destino()
        with self.assertRaises(backup.ErroDeBackup):
            backup.restaurar(arq, "senha-errada-1234", novo, sem_grafo=True)
        self.assertEqual(list(novo.iterdir()), [])


class TestPacoteMalicioso(Base):
    """Quem tiver a senha poderia forjar um backup: o restaurador não pode escrever fora da pasta do projeto."""

    def forjar(self, membros, manifesto_arquivos=None):
        """membros: lista de (nome, bytes | None para symlink). Devolve o .fxbak cifrado com a senha de teste."""
        pacote = self.dir / "forjado.tar.gz"
        arquivos = manifesto_arquivos if manifesto_arquivos is not None else [
            {"nome": n, "bytes": len(d), "sha256": backup.hashlib.sha256(d).hexdigest()} for n, d in membros if isinstance(d, bytes)]
        with tarfile.open(pacote, "w:gz") as tar:
            dados = json.dumps({"versao": 1, "grafo": {"incluido": False}, "arquivos": arquivos}).encode()
            info = tarfile.TarInfo("manifest.json")
            info.size = len(dados)
            tar.addfile(info, io.BytesIO(dados))
            for nome, conteudo in membros:
                info = tarfile.TarInfo(nome)
                if isinstance(conteudo, tuple):             # ("link", alvo dentro do pacote)
                    info.type, info.linkname = tarfile.SYMTYPE, conteudo[1]
                    tar.addfile(info)
                else:
                    info.size = len(conteudo)
                    tar.addfile(info, io.BytesIO(conteudo))
        saida = self.dir / "forjado.fxbak"
        backup.cifrar(pacote, saida, SENHA)
        return saida

    def test_caminhos_perigosos_sao_recusados(self):
        for nome in ("projeto/../../fora.txt", "projeto/dados/../../fora.txt", "/etc/passwd", "projeto\\..\\fora", "projeto/site/config.php",
                     "projeto/.git/hooks/pre-commit", "outro/x", "projeto/C:/x", "whatsapp/../fora"):
            with self.subTest(nome=nome):
                arq = self.forjar([(nome, b"conteudo")])
                with self.assertRaises(backup.ErroDeBackup):
                    backup.verificar(arq, SENHA)

    def test_link_simbolico_e_recusado(self):
        # o link aponta para um arquivo comum do próprio pacote e o hash do manifesto confere: só a checagem de tipo o barra
        h = backup.hashlib.sha256(b"1").hexdigest()
        arq = self.forjar([("projeto/dados/a.json", b"1"), ("projeto/dados/ln", ("link", "projeto/dados/a.json"))],
                          manifesto_arquivos=[{"nome": "projeto/dados/a.json", "bytes": 1, "sha256": h}, {"nome": "projeto/dados/ln", "bytes": 1, "sha256": h}])
        with self.assertRaisesRegex(backup.ErroDeBackup, "não é arquivo comum"):
            backup.verificar(arq, SENHA)

    def test_arquivo_fora_do_manifesto_e_conteudo_alterado_sao_recusados(self):
        arq = self.forjar([("projeto/dados/a.json", b"1"), ("projeto/dados/b.json", b"2")],
                          manifesto_arquivos=[{"nome": "projeto/dados/a.json", "bytes": 1, "sha256": backup.hashlib.sha256(b"1").hexdigest()}])
        with self.assertRaisesRegex(backup.ErroDeBackup, "não bate"):
            backup.verificar(arq, SENHA)
        arq = self.forjar([("projeto/dados/a.json", b"1")],
                          manifesto_arquivos=[{"nome": "projeto/dados/a.json", "bytes": 1, "sha256": backup.hashlib.sha256(b"outro").hexdigest()}])
        with self.assertRaisesRegex(backup.ErroDeBackup, "alterado"):
            backup.verificar(arq, SENHA)

    def test_nomes_e_destinos(self):
        self.assertEqual(backup.separar_nome("projeto/dados/x/y.json"), ("projeto", "dados/x/y.json"))
        self.assertEqual(backup.separar_nome("whatsapp/auth/creds.json"), ("whatsapp", "auth/creds.json"))
        self.assertEqual(backup.destino_de("projeto/.env", self.raiz), self.raiz / ".env")


class TestGrafoComDockerFalso(Base):
    """A ordem das chamadas ao Docker: parar, copiar, religar (mesmo se a cópia falhar). Docker de verdade: veja docs/backup-e-restauracao.md."""

    def preparar(self, rodando=True, dump_falha=False):
        self.chamadas = []

        def docker(*args, **kw):
            self.chamadas.append(args[0])
            return ""

        def dump(imagem, volume, destino):
            self.chamadas.append("dump")
            if dump_falha:
                raise backup.ErroDeBackup("dump falhou")
            destino.write_bytes(b"DUMP-DO-GRAFO" * 100)

        return [
            mock.patch.object(backup, "docker_disponivel", return_value=True),
            mock.patch.object(backup, "container_existe", return_value=True),
            mock.patch.object(backup, "container_rodando", return_value=rodando),
            mock.patch.object(backup, "volume_de_dados", return_value="vol"),
            mock.patch.object(backup, "imagem_do_container", return_value="neo4j:5.26.0-community"),
            mock.patch.object(backup, "contar_nos", return_value=42),
            mock.patch.object(backup, "_docker", side_effect=docker),
            mock.patch.object(backup, "_dump", side_effect=dump),
        ]

    def com(self, patches):
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_para_copia_e_religa_e_guarda_a_contagem(self):
        self.com(self.preparar())
        arq = backup.criar(self.raiz, self.saida, SENHA)
        self.assertEqual(self.chamadas, ["stop", "dump", "start"])
        g = backup.verificar(arq, SENHA)["grafo"]
        self.assertTrue(g["incluido"] and g["nos"] == 42 and g["imagem"].startswith("neo4j:5.26"))

    def test_religa_mesmo_se_a_copia_falhar(self):
        self.com(self.preparar(dump_falha=True))
        with self.assertRaises(backup.ErroDeBackup):
            backup.criar(self.raiz, self.saida, SENHA)
        self.assertEqual(self.chamadas, ["stop", "dump", "start"])
        self.assertEqual(list(self.saida.glob("*.fxbak")), [])

    def test_container_parado_nao_e_ligado_nem_parado(self):
        self.com(self.preparar(rodando=False))
        backup.criar(self.raiz, self.saida, SENHA)
        self.assertEqual(self.chamadas, ["dump"])

    def test_restaurar_entrega_o_mesmo_dump_ao_restaurador_do_grafo(self):
        self.com(self.preparar())
        arq = backup.criar(self.raiz, self.saida, SENHA)
        recebido = {}

        def grafo(raiz, dump, info, container):
            recebido["bytes"] = dump.read_bytes()
            recebido["nos"] = info["nos"]

        novo = self.novo_destino()
        with mock.patch.object(backup, "_restaurar_grafo", side_effect=grafo), mock.patch.object(backup, "container_existe", return_value=False), \
                mock.patch.dict(os.environ, {"WHATSAPP_STATE_DIR": str(self.dir / "wa-novo")}):
            backup.restaurar(arq, SENHA, novo)
        self.assertEqual(recebido, {"bytes": b"DUMP-DO-GRAFO" * 100, "nos": 42})

    def test_grafo_existente_com_dados_exige_forcar_e_nada_e_escrito(self):
        self.com(self.preparar())
        arq = backup.criar(self.raiz, self.saida, SENHA)
        novo = self.novo_destino()
        with mock.patch.object(backup, "_restaurar_grafo") as restaurar, mock.patch.dict(os.environ, {"WHATSAPP_STATE_DIR": str(self.dir / "wa-novo")}):
            with self.assertRaisesRegex(backup.ErroDeBackup, "grafo do contêiner"):
                backup.restaurar(arq, SENHA, novo)
            restaurar.assert_not_called()
        self.assertEqual(list(novo.iterdir()), [])

    def test_sem_docker_na_criacao_explica_o_que_fazer(self):
        with mock.patch.object(backup, "docker_disponivel", return_value=False):
            with self.assertRaisesRegex(backup.ErroDeBackup, "--sem-grafo"):
                backup.criar(self.raiz, self.saida, SENHA)

    def test_volume_de_dados_le_as_montagens(self):
        montagens = json.dumps([{"Type": "volume", "Name": "logs", "Destination": "/logs"}, {"Type": "volume", "Name": "dados-vol", "Destination": "/data"}])
        with mock.patch.object(backup, "_docker", return_value=montagens):
            self.assertEqual(backup.volume_de_dados("x"), "dados-vol")
        with mock.patch.object(backup, "_docker", return_value="[]"):
            with self.assertRaises(backup.ErroDeBackup):
                backup.volume_de_dados("x")


if __name__ == "__main__":
    unittest.main()
