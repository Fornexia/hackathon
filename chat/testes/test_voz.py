"""Nota de voz: conferência do CNPJ falado e o transcritor (sem Whisper e sem rede).

    python -m unittest discover -s chat/testes -v
"""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "chat"))
import voz  # noqa: E402

BERNHOEFT = "26852688000202"          # CNPJ válido
FERREIRA = "10230480000130"           # CNPJ válido


class TestCnpjValido(unittest.TestCase):
    def test_digito_verificador(self):
        self.assertTrue(voz.cnpj_valido(BERNHOEFT) and voz.cnpj_valido(FERREIRA))
        for ruim in ("26852688000203", "00000000000000", "123", "", "2685268800020a", "２６８５２６８８０００２０２"):
            self.assertFalse(voz.cnpj_valido(ruim), ruim)


class TestConferirCnpjFalado(unittest.TestCase):
    def test_cnpj_valido_em_qualquer_forma_de_escrever_passa(self):
        for texto in ("Quais contratos federais tem a Bernhoeft, CNPJ 26.852.688/0002-02?", "CNPJ 26852688000202", "o cnpj é 26 852 688 0002 02",
                      "Me fale sobre o CNPJ número 10.230.480/0001-30.", "CNPJ de 26.852.688/0002-02 tem contrato?"):
            self.assertIsNone(voz.conferir_cnpj_falado(texto), texto)

    def test_as_frases_reais_que_o_whisper_devolveu_com_voz_sintetica_sao_barradas(self):
        """Medido em 14/11/2026 com o modelo small: truncado, dígito a menos e sem forma de CNPJ."""
        for texto, n in (("Quais contratos e denais tem a melhor efe? CNPJ 26.852.688.00.", 10),
                         ("Me fale sobre o CNPJ 26 852-688-0002-3.", 13),
                         ("Me fale sobre o CNPJ 1.0, 2.3.0, 4.8.0, 1.0, 1.0, 1.0, 1.0.0", 14)):
            problema = voz.conferir_cnpj_falado(texto)
            self.assertIsNotNone(problema, texto)
            if n != 14:
                self.assertIn(f"tem {n} números", problema)

    def test_quatorze_numeros_com_o_digito_final_errado_nao_fecha(self):
        self.assertIn("não fecha", voz.conferir_cnpj_falado("CNPJ 26.852.688/0002-03"))
        self.assertIn("não fecha", voz.conferir_cnpj_falado("CNPJ 11111111111111"))

    def test_sequencia_longa_sem_a_palavra_cnpj_tambem_e_conferida(self):
        self.assertIsNone(voz.conferir_cnpj_falado("a empresa 26.852.688/0002-02 tem sanção?"))
        self.assertIn("tem 13 números", voz.conferir_cnpj_falado("a empresa 2685268800020 tem sanção?"))

    def test_o_que_nao_e_cnpj_nao_atrapalha(self):
        for texto in ("Existe sanção para algum fornecedor?", "Qual o CNPJ da Ferreira Costa?", "CNPJ", "o contrato 3342014 vale quanto?", "contrato 45/2026",
                      "valor de R$ 276.061,44", "o CPF 52998224725", "em 2024 foram 12 contratos", "", "CNPJ da empresa, de 2024"):
            self.assertIsNone(voz.conferir_cnpj_falado(texto), texto)

    def test_o_marcador_do_transcritor_pede_para_digitar(self):
        self.assertIsNotNone(voz.conferir_cnpj_falado("Me fale do CNPJ [CNPJ não entendido]"))

    def test_dois_cnpjs_um_bom_e_um_ruim_barra(self):
        self.assertIsNotNone(voz.conferir_cnpj_falado("compare o CNPJ 26.852.688/0002-02 com 10.230.480/0001-3"))

    def test_candidatos_nao_repete_o_mesmo_numero(self):
        self.assertEqual(voz.candidatos("CNPJ 26.852.688/0002-02, repito 26.852.688/0002-02"), [BERNHOEFT])


class TestLeituraDaSaidaDoTranscritor(unittest.TestCase):
    """Um processo filho de verdade, sem PYTHONIOENCODING no ambiente: o acento tem de chegar inteiro (o Windows lia em cp1252)."""

    def test_acento_chega_inteiro_do_processo_filho(self):
        import os
        import tempfile
        import worker
        script = "import sys\nsys.stdout.buffer.write('existe sanção para o fornecedor, ação e coração\\n'.encode('utf-8'))\n"
        with tempfile.TemporaryDirectory() as pasta:
            falso = Path(pasta) / "transcrever_falso.py"
            falso.write_text(script, encoding="utf-8")
            sem_variavel = {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}
            with mock.patch.dict(os.environ, sem_variavel, clear=True), mock.patch.object(worker, "PYTHON_AUDIO", Path(sys.executable)), \
                    mock.patch.object(worker, "TRANSCRITOR", falso):
                self.assertEqual(worker.transcrever("a.ogg"), "existe sanção para o fornecedor, ação e coração")

    def test_falha_do_processo_filho_devolve_none(self):
        import worker
        with mock.patch.object(worker.subprocess, "run", side_effect=OSError("sem python")):
            self.assertIsNone(worker.transcrever("a.ogg"))


class TestMensagens(unittest.TestCase):
    def test_pedido_para_digitar_mostra_o_que_foi_ouvido_e_diz_por_que_nao_consulta(self):
        m = voz.pedir_para_digitar("CNPJ 26 852-688-0002-3", "o CNPJ que ouvi tem 13 números, e ele precisa ter 14")
        self.assertIn("Ouvi: “CNPJ 26 852-688-0002-3”", m)
        self.assertIn("Não vou consultar", m)
        self.assertIn("digitar o CNPJ", m)

    def test_eco_e_texto_longo_e_cortado(self):
        self.assertEqual(voz.eco("existe sanção"), "🎙️ Entendi: “existe sanção”\n\n")
        longo = voz.eco("palavra " * 200)
        self.assertLess(len(longo), 340)
        self.assertIn("…", longo)


def carregar_transcritor():
    """O transcrever.py importa numpy e faster_whisper (só existem em inferencia/.venv): troco os dois por falsos para testar a lógica de texto."""
    with mock.patch.dict(sys.modules, {"numpy": mock.MagicMock(), "faster_whisper": mock.MagicMock()}):
        spec = importlib.util.spec_from_file_location("transcrever_teste", RAIZ / "inferencia" / "transcrever.py")
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    return modulo


class TestTranscritor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = carregar_transcritor()

    def transcrever_dizendo(self, texto):
        segmento = mock.Mock(text=texto)
        modelo = mock.Mock()
        modelo.transcribe.return_value = ([segmento], None)
        with mock.patch.object(self.t, "WhisperModel", return_value=modelo), mock.patch.object(self.t, "decodificar", return_value=b""):
            return self.t.transcrever("a.ogg"), modelo

    def test_o_contexto_e_do_nosso_assunto_e_nao_de_precos_de_compra(self):
        self.assertIn("fornecedores", self.t.CONTEXTO)
        self.assertNotIn("pacotes", self.t.CONTEXTO)
        _, modelo = self.transcrever_dizendo("existe sanção")
        self.assertEqual(modelo.transcribe.call_args.kwargs["initial_prompt"], self.t.CONTEXTO)
        self.assertEqual(modelo.transcribe.call_args.kwargs["language"], "pt")
        self.assertIn("sanções", modelo.transcribe.call_args.kwargs["hotwords"])        # "sanções" saiu "sensações" numa nota real
        self.assertGreater(modelo.transcribe.call_args.kwargs["beam_size"], 1)

    def test_cnpj_copiado_do_exemplo_do_contexto_vira_marcador(self):
        for dito in ("o CNPJ 12.345.678/0001-95 tem contrato", "CNPJ 12345678000195", "CNPJ 12 345 678 0001 95"):
            texto, _ = self.transcrever_dizendo(dito)
            self.assertIn("[CNPJ não entendido]", texto, dito)
            self.assertNotIn("12.345", texto)
            self.assertIsNotNone(voz.conferir_cnpj_falado(texto))          # e o worker não consulta

    def test_valor_copiado_do_exemplo_vira_marcador_e_outro_valor_passa(self):
        self.assertIn("[valor não entendido]", self.transcrever_dizendo("contrato de R$ 7,77")[0])
        self.assertEqual(self.transcrever_dizendo("contrato de R$ 276.061,44")[0], "contrato de R$ 276.061,44")

    def test_cnpj_diferente_do_exemplo_passa_inteiro(self):
        self.assertEqual(self.transcrever_dizendo("CNPJ 26.852.688/0002-02")[0], "CNPJ 26.852.688/0002-02")

    def test_junta_os_segmentos(self):
        s1, s2 = mock.Mock(text=" existe sanção "), mock.Mock(text="para algum fornecedor")
        modelo = mock.Mock()
        modelo.transcribe.return_value = ([s1, s2], None)
        with mock.patch.object(self.t, "WhisperModel", return_value=modelo), mock.patch.object(self.t, "decodificar", return_value=b""):
            self.assertEqual(self.t.transcrever("a.ogg"), "existe sanção para algum fornecedor")

    def test_ffmpeg_do_sistema_vence_e_sem_ele_usa_o_do_pacote(self):
        with mock.patch.object(self.t.shutil, "which", return_value="C:/ff/ffmpeg.exe"):
            self.assertEqual(self.t.achar_ffmpeg(), "C:/ff/ffmpeg.exe")
        falso = mock.Mock(get_ffmpeg_exe=lambda: "C:/venv/imageio/ffmpeg.exe")
        with mock.patch.object(self.t.shutil, "which", return_value=None), mock.patch.dict(sys.modules, {"imageio_ffmpeg": falso}), \
                mock.patch.dict(self.t.os.environ, {"FFMPEG_BIN": ""}):
            self.assertEqual(self.t.achar_ffmpeg(), "C:/venv/imageio/ffmpeg.exe")

    def test_sem_nenhum_ffmpeg_o_erro_diz_o_que_fazer(self):
        with mock.patch.object(self.t.shutil, "which", return_value=None), mock.patch.dict(sys.modules, {"imageio_ffmpeg": None}), \
                mock.patch.dict(self.t.os.environ, {"FFMPEG_BIN": ""}):
            with self.assertRaisesRegex(RuntimeError, "imageio-ffmpeg"):
                self.t.achar_ffmpeg()


if __name__ == "__main__":
    unittest.main()
