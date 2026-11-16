"""Testes dos alertas por e-mail (alertas/): assinaturas, comparação, envio e, contra um Neo4j de verdade, o isolamento entre perfis.

    docker run -d --rm --name neo4j-teste-api -p 127.0.0.1:7699:7687 -e NEO4J_AUTH=neo4j/SENHA neo4j:5.26.0-community
    NEO4J_URI=bolt://127.0.0.1:7699 NEO4J_SENHA=SENHA python coleta/carregar_neo4j.py --zerar --exemplo
    NEO4J_URI=bolt://127.0.0.1:7699 NEO4J_SENHA=SENHA python -m unittest discover -s alertas/testes -v

Sem o banco no ar, os testes que precisam dele são pulados e dizem por quê. Os demais não usam banco, modelo nem rede: a fonte é falsa e o
servidor de e-mail é um SMTP de brincadeira numa porta local. Nenhum teste gasta crédito nem manda e-mail de verdade.
"""

import copy
import json
import os
import socketserver
import sys
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
for k in ("TRANSPARENCIA_PERFIL", "TRANSPARENCIA_TENANTS", "TRANSPARENCIA_VER_PESSOAL", "ALERTAS_SMTP_HOST", "ALERTAS_ENVIO"):
    os.environ.pop(k, None)
os.environ["TRANSPARENCIA_LOG"] = str(Path(tempfile.gettempdir()) / "transparencia-testes-alertas.jsonl")
for pasta in ("alertas", "consulta"):
    sys.path.insert(0, str(RAIZ / pasta))

import assinaturas as ass  # noqa: E402
import envio  # noqa: E402
import monitor  # noqa: E402
import simular  # noqa: E402

CNPJ = "33333333000133"
OUTRO = "11111111000111"
AGORA = datetime(2026, 11, 16, 9, 0).astimezone()


def sancao(**m):
    s = {"cadastro": "ceis", "tipo": "Impedimento de licitar", "situacao": "Vigente", "publicada_em": "2026-11-01", "inicio_suspensao": "2026-11-01",
         "orgao": "Órgão X", "ente": "br-uniao", "evidencia": "f1"}
    s.update(m)
    return s


def contrato(**m):
    c = {"numero": "1/2026", "objeto": "Pavimentação", "valor_contratado": 500000.0, "inicio": "2026-04-01", "fim": "2026-12-31",
         "tem_aditivo": False, "ente": "ex-estado", "evidencia": "x2"}
    c.update(m)
    return c


class FonteFalsa:
    """O que a base 'sabe' agora, por CNPJ. `quebrar` simula a base fora do ar."""

    def __init__(self, dados=None):
        self.dados = dados if dados is not None else {}
        self.quebrar = False

    def ler(self, cnpj):
        if self.quebrar:
            raise ConnectionError("neo4j fora do ar")
        d = self.dados.get(cnpj)
        return copy.deepcopy(d) if d is not None else None

    def evidencia(self, id_):
        return {"url": f"https://portal.exemplo/{id_}", "capturado_em": "2026-11-15T10:00:00-03:00"}


def cru(sancoes=(), contratos=(), cadastro=(), nome="Obras Exemplares Ltda (fictícia)"):
    return {"nome": nome, "sancoes": list(sancoes), "contratos": list(contratos), "cadastro": list(cadastro)}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.loja = ass.Assinaturas(Path(self.tmp.name))
        self.enviados = []
        self.falhar_envio = False
        os.environ["ALERTAS_ENVIO"] = "arquivo"
        self.addCleanup(os.environ.pop, "ALERTAS_ENVIO", None)

    def enviar(self, assinatura, eventos, agora):
        if self.falhar_envio:
            raise ConnectionError("smtp fora do ar")
        self.enviados.append((assinatura, eventos))
        return envio.enviar(envio.montar(assinatura, eventos, agora), Path(self.tmp.name))

    def rodar(self, fonte, ensaio=False):
        return monitor.verificar(self.loja, lambda perfil: fonte, self.enviar, ensaio=ensaio, agora=AGORA)

    def assinar(self, cnpjs=(CNPJ,), email="cliente@empresa.com.br", perfil="estado-exemplo", verificado=True, **extra):
        return self.loja.criar(email, perfil, list(cnpjs), verificado=verificado, **extra)


class TestAssinaturas(Base):
    def test_cria_com_codigo_de_cancelamento_aleatorio(self):
        a, b = self.assinar(), self.loja.criar("outra@empresa.com.br", "estado-exemplo", [CNPJ])
        self.assertEqual(a["cnpjs"], [CNPJ])
        self.assertGreaterEqual(len(a["token"]), 24)
        self.assertNotEqual(a["token"], b["token"])

    def test_email_invalido_e_injecao_de_cabecalho_sao_recusados(self):
        for ruim in ("", "sem-arroba", "a@b", "a b@c.com", "a@c.com\r\nBcc: vitima@x.com", "a@c.com\nBcc: x@y.com", "<script>@x.com", "a" * 300 + "@x.com"):
            with self.subTest(ruim=ruim), self.assertRaises(ass.ErroDeAssinatura):
                self.loja.criar(ruim, "estado-exemplo", [CNPJ])

    def test_so_cnpj_cpf_e_lixo_sao_recusados(self):
        for ruim in ("12345678901", "123.456.789-01", "123", "abc", "", "3333333300013"):
            with self.subTest(ruim=ruim), self.assertRaises(ass.ErroDeAssinatura):
                self.loja.criar("a@b.com", "estado-exemplo", [ruim])
        self.assertEqual(self.loja.criar("a@b.com", "estado-exemplo", ["33.333.333/0001-33"])["cnpjs"], [CNPJ])

    def test_perfil_desconhecido_e_perfil_com_dado_pessoal_sao_recusados(self):
        with self.assertRaises(ass.ErroDeAssinatura):
            self.loja.criar("a@b.com", "inexistente", [CNPJ])
        com_pessoal = {"x": {"nome": "X", "tenants": ["ex-estado"], "ver_pessoal": True}}
        with mock.patch.object(ass.perfis, "carregar", return_value=com_pessoal), self.assertRaises(ass.ErroDeAssinatura):
            self.loja.criar("a@b.com", "x", [CNPJ])

    def test_mesmo_email_e_perfil_somam_cnpjs_em_vez_de_duplicar(self):
        a = self.assinar((CNPJ,))
        b = self.assinar((OUTRO, CNPJ))
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(self.loja.listar()[0]["cnpjs"], [CNPJ, OUTRO])
        self.assertEqual(len(self.loja.listar()), 1)

    def test_limite_de_cnpjs_por_assinatura(self):
        muitos = [f"{i:014d}" for i in range(1, ass.MAX_CNPJS + 2)]
        with self.assertRaises(ass.ErroDeAssinatura):
            self.loja.criar("a@b.com", "estado-exemplo", muitos)

    def test_cancelar_por_codigo_por_email_e_codigo_errado(self):
        a = self.assinar()
        self.assertEqual(self.loja.cancelar("codigo-errado"), 0)
        self.assertEqual(self.loja.cancelar("ação-é-não-ascii-ç"), 0)          # não pode estourar com texto fora do ASCII
        self.assertEqual(len(self.loja.listar(so_ativas=True)), 1)
        self.assertEqual(self.loja.cancelar(a["token"]), 1)
        self.assertEqual(self.loja.listar(so_ativas=True), [])
        self.assertEqual(self.loja.cancelar(a["token"]), 0)
        b = self.assinar(email="Maria@Empresa.com.br")
        self.assertEqual(self.loja.cancelar("MARIA@empresa.com.br"), 1)
        self.assertFalse(self.loja.listar()[-1]["ativa"])
        self.assertTrue(b["id"])

    def test_cancelar_apaga_a_foto_de_quem_saiu(self):
        a = self.assinar()
        self.rodar(FonteFalsa({CNPJ: cru()}))
        self.assertIn(a["id"], self.loja.ler_estado())
        self.loja.cancelar(a["token"])
        self.assertNotIn(a["id"], self.loja.ler_estado())

    def test_cancelada_nao_recebe_mais(self):
        a = self.assinar()
        fonte = FonteFalsa({CNPJ: cru()})
        self.rodar(fonte)
        self.loja.cancelar(a["token"])
        fonte.dados[CNPJ]["sancoes"].append(sancao())
        self.assertEqual(self.rodar(fonte), [])
        self.assertEqual(self.enviados, [])


class TestVerificacaoDoEmail(Base):
    def test_sem_verificar_nada_e_lido_nem_enviado(self):
        a = self.assinar(verificado=False, origem="site", usuario_id=7)
        self.assertFalse(a["email_verificado"])
        self.assertIsNone(a["consentimento_em"])
        self.assertEqual((a["origem"], a["usuario_id"]), ("site", 7))
        fonte = FonteFalsa({CNPJ: cru()})
        r = self.rodar(fonte)
        self.assertEqual(r[0]["eventos"], 0)
        self.assertIn("não verificado", r[0]["avisos"][0])
        self.assertEqual(self.loja.ler_estado(), {})             # nem foto: a linha de base nasce quando confirmar
        fonte.dados[CNPJ]["sancoes"].append(sancao())
        self.rodar(fonte)
        self.assertEqual(self.enviados, [])

    def test_ao_confirmar_a_primeira_rodada_e_linha_de_base_e_nao_avisa_o_passado(self):
        a = self.assinar(verificado=False, origem="site")
        fonte = FonteFalsa({CNPJ: cru(sancoes=[sancao()], contratos=[contrato()])})
        self.rodar(fonte)
        self.assertEqual(self.loja.marcar_verificado(a["id"]), 1)
        self.assertTrue(self.loja.listar()[0]["consentimento_em"])
        r = self.rodar(fonte)
        self.assertEqual((r[0]["eventos"], r[0]["linha_de_base"]), (0, [CNPJ]))
        fonte.dados[CNPJ]["sancoes"].append(sancao(tipo="Outra"))
        self.assertEqual(self.rodar(fonte)[0]["eventos"], 1)
        self.assertEqual(len(self.enviados), 1)

    def test_conta_google_ja_nasce_verificada_e_nao_existe_google_sem_verificar(self):
        g = self.assinar(origem="google", usuario_id=3)
        self.assertTrue(g["email_verificado"])
        with self.assertRaises(ass.ErroDeAssinatura):
            self.assinar(email="x@y.com", origem="google", verificado=False)
        with self.assertRaises(ass.ErroDeAssinatura):
            self.assinar(email="x@y.com", origem="inventada")

    def test_confirmar_por_email_e_idempotente_e_nao_confirma_cancelada(self):
        a = self.assinar(verificado=False)
        self.assertEqual(self.loja.marcar_verificado("CLIENTE@empresa.com.br"), 1)
        self.assertEqual(self.loja.marcar_verificado(a["id"]), 0)
        b = self.assinar(email="b@b.com", verificado=False)
        self.loja.cancelar(b["token"])
        self.assertEqual(self.loja.marcar_verificado(b["id"]), 0)

    def test_quem_confirma_o_email_fica_so_com_o_que_ele_pediu(self):
        antigo = self.assinar((OUTRO,), verificado=False)           # pedido de um terceiro, sem prova de posse do e-mail
        dono = self.assinar((CNPJ,), verificado=True)
        self.assertTrue(dono["email_verificado"])
        self.assertEqual(len(self.loja.listar()), 1)
        self.assertEqual(self.loja.listar()[0]["cnpjs"], [CNPJ])    # o CNPJ do terceiro não sobrevive
        self.assertNotEqual(dono["token"], antigo["token"])         # e o código que o terceiro viu deixou de valer
        self.assertEqual(self.loja.cancelar(antigo["token"]), 0)

    def test_pedido_sem_verificar_nao_mexe_na_assinatura_de_quem_verificou(self):
        self.assinar((CNPJ,), verificado=True)
        with self.assertRaises(ass.ErroDeAssinatura):
            self.assinar((OUTRO,), verificado=False)
        self.assertEqual(self.loja.listar()[0]["cnpjs"], [CNPJ])
        self.assertEqual(len(self.loja.listar()), 1)
        self.assinar((OUTRO,), verificado=True)                    # quem prova o e-mail continua podendo acrescentar
        self.assertEqual(self.loja.listar()[0]["cnpjs"], [CNPJ, OUTRO])

    def test_dois_pedidos_sem_verificar_somam_e_continuam_parados(self):
        self.assinar((CNPJ,), verificado=False)
        self.assinar((OUTRO,), verificado=False)
        self.assertEqual(self.loja.listar()[0]["cnpjs"], [CNPJ, OUTRO])
        self.assertFalse(self.loja.listar()[0]["email_verificado"])


class TestMonitor(Base):
    def test_primeira_rodada_so_tira_a_foto_e_nao_avisa(self):
        self.assinar()
        r = self.rodar(FonteFalsa({CNPJ: cru(sancoes=[sancao()], contratos=[contrato()])}))
        self.assertEqual(r[0]["eventos"], 0)
        self.assertEqual(r[0]["linha_de_base"], [CNPJ])
        self.assertEqual(self.enviados, [])

    def test_sem_mudanca_nao_manda_nada(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru(sancoes=[sancao()], contratos=[contrato()])})
        self.rodar(fonte)
        r = self.rodar(fonte)
        self.assertEqual(r[0]["eventos"], 0)
        self.assertEqual(self.enviados, [])

    def test_sancao_nova_gera_aviso_com_fonte_e_prova(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru()})
        self.rodar(fonte)
        fonte.dados[CNPJ]["sancoes"].append(sancao())
        r = self.rodar(fonte)
        self.assertEqual(r[0]["eventos"], 1)
        e = r[0]["lista"][0]
        self.assertEqual((e["tipo"], e["cnpj"], e["evidencia"]), ("sancao_nova", CNPJ, "f1"))
        self.assertIn("CEIS", e["titulo"])
        self.assertEqual(e["fonte_url"], "https://portal.exemplo/f1")
        self.assertTrue(e["capturado_em"])
        self.assertTrue(Path(r[0]["enviado_para"]).is_file())

    def test_o_mesmo_aviso_nao_sai_duas_vezes(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru()})
        self.rodar(fonte)
        fonte.dados[CNPJ]["sancoes"].append(sancao())
        self.rodar(fonte)
        self.rodar(fonte)
        self.assertEqual(len(self.enviados), 1)

    def test_sancao_alterada_e_removida(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru(sancoes=[sancao()])})
        self.rodar(fonte)
        fonte.dados[CNPJ]["sancoes"][0].update(situacao="Encerrada", fim_suspensao="2026-11-20")
        r = self.rodar(fonte)
        self.assertEqual([e["tipo"] for e in r[0]["lista"]], ["sancao_alterada"])
        self.assertIn("Vigente → Encerrada", r[0]["lista"][0]["detalhe"])
        fonte.dados[CNPJ]["sancoes"] = []
        fonte.dados[CNPJ]["contratos"] = [contrato()]       # a base segue com dados: é remoção de verdade, não recarga
        tipos = [e["tipo"] for e in self.rodar(fonte)[0]["lista"]]
        self.assertIn("sancao_removida", tipos)

    def test_contrato_novo_e_alterado(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru(contratos=[contrato()])})
        self.rodar(fonte)
        fonte.dados[CNPJ]["contratos"] = [contrato(valor_final=650000.0, tem_aditivo=True), contrato(numero="2/2026", objeto="Drenagem")]
        r = self.rodar(fonte)
        tipos = sorted(e["tipo"] for e in r[0]["lista"])
        self.assertEqual(tipos, ["contrato_alterado", "contrato_novo"])
        alterado = next(e for e in r[0]["lista"] if e["tipo"] == "contrato_alterado")
        self.assertIn("valor final", alterado["detalhe"])

    def test_mudanca_de_situacao_cadastral(self):
        self.assinar()
        cad = {"razao_social": "X", "situacao": "ATIVA", "situacao_desde": "2020-01-01", "ente": "ex-estado", "evidencia": "r1"}
        fonte = FonteFalsa({CNPJ: cru(cadastro=[cad])})
        self.rodar(fonte)
        fonte.dados[CNPJ]["cadastro"] = [dict(cad, situacao="BAIXADA", situacao_desde="2026-11-10", motivo_situacao="Extinção")]
        r = self.rodar(fonte)
        self.assertEqual(r[0]["lista"][0]["tipo"], "cadastro_alterado")
        self.assertIn("ATIVA → BAIXADA", r[0]["lista"][0]["detalhe"])

    def test_cnpj_acrescentado_depois_vira_linha_de_base_e_nao_aviso(self):
        self.assinar((CNPJ,))
        fonte = FonteFalsa({CNPJ: cru(), OUTRO: cru(sancoes=[sancao()], nome="Outra Ltda")})
        self.rodar(fonte)
        self.assinar((OUTRO,))
        r = self.rodar(fonte)
        self.assertEqual(r[0]["eventos"], 0)
        self.assertEqual(r[0]["linha_de_base"], [OUTRO])

    def test_falha_no_envio_nao_perde_o_aviso(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru()})
        self.rodar(fonte)
        fonte.dados[CNPJ]["sancoes"].append(sancao())
        self.falhar_envio = True
        r = self.rodar(fonte)
        self.assertIn("erro_de_envio", r[0])
        self.assertIsNone(self.loja.listar()[0]["ultimo_envio"])
        self.falhar_envio = False
        r = self.rodar(fonte)                       # a foto antiga foi mantida, então o aviso ainda existe
        self.assertEqual(r[0]["eventos"], 1)
        self.assertTrue(r[0]["enviado_para"])
        self.assertTrue(self.loja.listar()[0]["ultimo_envio"])

    def test_email_ja_saiu_mas_nao_gravou_o_horario_nao_repete_o_aviso(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru()})
        self.rodar(fonte)
        fonte.dados[CNPJ]["sancoes"].append(sancao())
        with mock.patch.object(ass.Assinaturas, "marcar_envio", side_effect=OSError("disco cheio")):
            r = self.rodar(fonte)
        self.assertEqual(len(self.enviados), 1)
        self.assertNotIn("erro_de_envio", r[0])
        self.assertTrue(any("horário" in x for x in r[0]["avisos"]))
        self.assertEqual(self.rodar(fonte)[0]["eventos"], 0)       # a foto avançou: nada de reenviar
        self.assertEqual(len(self.enviados), 1)

    def test_modo_de_envio_com_nome_errado_falha_e_nao_consome_o_aviso(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru()})
        self.rodar(fonte)
        fonte.dados[CNPJ]["sancoes"].append(sancao())
        os.environ["ALERTAS_ENVIO"] = "email"
        r = self.rodar(fonte)
        self.assertIn("ALERTAS_ENVIO inválido", r[0]["erro_de_envio"])
        os.environ["ALERTAS_ENVIO"] = "arquivo"
        self.assertEqual(self.rodar(fonte)[0]["eventos"], 1)       # a foto antiga ficou: o aviso ainda sai

    def test_consulta_cheia_nao_vira_remocao_nem_novidade_falsa(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru(sancoes=[sancao(), sancao(publicada_em="2026-10-01", inicio_suspensao="2026-10-01")])})
        fonte.limite = 2                                            # a consulta devolve no máximo 2: está cheia
        self.rodar(fonte)
        nova = sancao(publicada_em="2026-11-10", inicio_suspensao="2026-11-10")
        fonte.dados[CNPJ]["sancoes"] = [nova, sancao()]             # a nova empurrou a mais antiga para fora da janela
        r = self.rodar(fonte)
        self.assertEqual([e["tipo"] for e in r[0]["lista"]], ["sancao_nova"])
        self.assertTrue(any("comparação parcial" in x for x in r[0]["avisos"]))
        fonte.dados[CNPJ]["sancoes"] = [sancao(), sancao(publicada_em="2026-10-01", inicio_suspensao="2026-10-01")]   # a antiga volta à janela
        self.assertEqual(self.rodar(fonte)[0]["eventos"], 0)       # já era conhecida: não é "nova"

    def test_consulta_que_nao_esta_cheia_continua_vendo_remocao(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru(sancoes=[sancao()])})
        fonte.limite = 50
        self.rodar(fonte)
        fonte.dados[CNPJ]["sancoes"] = []
        fonte.dados[CNPJ]["contratos"] = [contrato()]
        self.assertEqual([e["tipo"] for e in self.rodar(fonte)[0]["lista"]], ["sancao_removida", "contrato_novo"])

    def test_contratos_de_mesmo_numero_nao_se_fundem(self):
        a, b = contrato(unidade="Secretaria A"), contrato(unidade="Secretaria B", objeto="Drenagem", valor_contratado=900000.0)
        sem_numero_1, sem_numero_2 = contrato(numero=None, objeto="Compra X"), contrato(numero=None, objeto="Compra Y")
        gemeos = [contrato(numero="7/2026", unidade="U"), contrato(numero="7/2026", unidade="U")]     # idênticos nos campos da chave
        foto = monitor.fotografar(FonteFalsa({CNPJ: cru(contratos=[a, b, sem_numero_1, sem_numero_2, *gemeos])}), CNPJ)
        self.assertEqual(len(foto["contratos"]), 6)
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru(contratos=[a, b])})
        self.rodar(fonte)
        fonte.dados[CNPJ]["contratos"].reverse()                    # a consulta não garante ordem entre contratos do mesmo dia
        self.assertEqual(self.rodar(fonte)[0]["eventos"], 0)
        fonte.dados[CNPJ]["contratos"].reverse()
        fonte.dados[CNPJ]["contratos"][1]["valor_contratado"] = 1000000.0
        r = self.rodar(fonte)
        self.assertEqual([e["tipo"] for e in r[0]["lista"]], ["contrato_alterado"])
        self.assertIn("Drenagem", r[0]["lista"][0]["detalhe"])     # o contrato B mudou, não o A

    def test_ensaio_nao_envia_nem_grava(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru()})
        self.rodar(fonte)
        fonte.dados[CNPJ]["sancoes"].append(sancao())
        antes = json.dumps(self.loja.ler_estado(), sort_keys=True)
        r = self.rodar(fonte, ensaio=True)
        self.assertEqual(r[0]["eventos"], 1)
        self.assertIsNone(r[0]["enviado_para"])
        self.assertEqual(self.enviados, [])
        self.assertEqual(json.dumps(self.loja.ler_estado(), sort_keys=True), antes)
        self.assertEqual(self.rodar(fonte)[0]["eventos"], 1)       # e o aviso continua valendo para a rodada de verdade

    def test_base_vazia_depois_de_ter_dados_nao_vira_remocao_em_massa(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru(sancoes=[sancao()], contratos=[contrato()])})
        self.rodar(fonte)
        fonte.dados = {}                            # recarga da base: o CNPJ some
        r = self.rodar(fonte)
        self.assertEqual(r[0]["eventos"], 0)
        self.assertTrue(r[0]["avisos"])
        fonte.dados = {CNPJ: cru(sancoes=[sancao()], contratos=[contrato()])}      # a base volta igual: nada a avisar
        self.assertEqual(self.rodar(fonte)[0]["eventos"], 0)
        self.assertEqual(self.enviados, [])

    def test_base_fora_do_ar_mantem_a_foto_e_nao_avisa(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru(sancoes=[sancao()])})
        self.rodar(fonte)
        fonte.quebrar = True
        r = self.rodar(fonte)
        self.assertEqual(r[0]["eventos"], 0)
        self.assertIn("consulta falhou", r[0]["avisos"][0])
        fonte.quebrar = False
        self.assertEqual(self.rodar(fonte)[0]["eventos"], 0)

    def test_um_email_por_assinatura_com_teto_de_avisos(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru()})
        self.rodar(fonte)
        fonte.dados[CNPJ]["contratos"] = [contrato(numero=f"{i}/2026") for i in range(1, 60)]
        r = self.rodar(fonte)
        self.assertEqual(len(self.enviados), 1)
        self.assertEqual(r[0]["eventos"], 59)
        msg = envio.montar(self.loja.listar()[0], r[0]["lista"], AGORA)
        self.assertEqual(msg["Subject"], "FornexIA: 59 novidades nos fornecedores que você acompanha")

    def test_dado_da_fonte_nao_chega_ao_assunto_nem_aos_cabecalhos(self):
        self.assinar()
        fonte = FonteFalsa({CNPJ: cru()})
        self.rodar(fonte)
        malicioso = "Órgão\r\nBcc: vitima@x.com\r\nSubject: PHISHING <script>alert(1)</script>"
        fonte.dados[CNPJ]["sancoes"].append(sancao(orgao=malicioso, tipo="Tipo\nX-Injetado: sim"))
        r = self.rodar(fonte)
        msg = envio.montar(self.loja.listar()[0], r[0]["lista"], AGORA)
        self.assertEqual(msg["Subject"], "FornexIA: 1 novidade nos fornecedores que você acompanha")
        self.assertIsNone(msg["Bcc"])
        self.assertIsNone(msg["X-Injetado"])
        bruto = bytes(msg).decode("utf-8", "replace")
        self.assertNotIn("\nBcc:", bruto)
        corpo_html = msg.get_body(("html",)).get_content()
        self.assertNotIn("<script>", corpo_html)
        self.assertIn("&lt;script&gt;", corpo_html)

    def test_cada_cliente_recebe_so_o_seu(self):
        a = self.assinar(email="um@empresa.com.br")
        b = self.assinar(email="dois@empresa.com.br", cnpjs=(OUTRO,))
        fonte = FonteFalsa({CNPJ: cru(), OUTRO: cru(nome="Outra Ltda")})
        self.rodar(fonte)
        fonte.dados[CNPJ]["sancoes"].append(sancao())
        self.rodar(fonte)
        self.assertEqual([x[0]["id"] for x in self.enviados], [a["id"]])
        self.assertNotEqual(a["id"], b["id"])


class TestEnvio(Base):
    def test_mensagem_traz_codigo_de_cancelamento_aviso_e_prova(self):
        a = self.assinar()
        evento = {"tipo": "sancao_nova", "cnpj": CNPJ, "nome": "Obras Exemplares Ltda (fictícia)", "titulo": "Nova ocorrência no CEIS",
                  "detalhe": "Impedimento de licitar.", "evidencia": "f1", "fonte_url": "https://portal.exemplo/f1", "capturado_em": "2026-11-15"}
        msg = envio.montar(a, [evento], AGORA, de="alertas@fornexia.exemplo")
        texto = msg.get_body(("plain",)).get_content()
        self.assertEqual(msg["To"], "cliente@empresa.com.br")
        self.assertIn(a["token"], texto)
        self.assertIn("33.333.333/0001-33", texto)
        self.assertIn("não prova irregularidade", texto)
        self.assertIn("evidência f1", texto)
        self.assertEqual(msg["Auto-Submitted"], "auto-generated")

    def test_modo_arquivo_grava_eml_legivel(self):
        a = self.assinar()
        caminho = Path(envio.enviar(envio.montar(a, [{"tipo": "x", "cnpj": CNPJ, "nome": "N", "titulo": "T", "detalhe": "D"}], AGORA), Path(self.tmp.name)))
        self.assertEqual(caminho.suffix, ".eml")
        self.assertIn("Subject: FornexIA", caminho.read_text(encoding="utf-8", errors="replace"))

    def test_modo_padrao_sem_servidor_e_arquivo(self):
        os.environ.pop("ALERTAS_ENVIO", None)
        self.assertEqual(envio.modo(), "arquivo")
        with mock.patch.dict(os.environ, {"ALERTAS_SMTP_HOST": "smtp.exemplo"}):
            self.assertEqual(envio.modo(), "smtp")

    def test_smtp_sem_configuracao_falha_e_nao_envia(self):
        with mock.patch.dict(os.environ, {"ALERTAS_ENVIO": "smtp"}, clear=False):
            os.environ.pop("ALERTAS_SMTP_HOST", None)
            with self.assertRaises(RuntimeError):
                envio.enviar(envio.mensagem_de_teste("a@b.com", AGORA))

    def test_smtp_de_verdade_numa_porta_local(self):
        recebidos = []

        class Manipulador(socketserver.StreamRequestHandler):
            def handle(self):
                w = lambda s: self.wfile.write((s + "\r\n").encode())
                w("220 teste")
                dados = False
                corpo = []
                for bruta in self.rfile:
                    linha = bruta.decode("utf-8", "replace").rstrip("\r\n")
                    if dados:
                        if linha == ".":
                            dados = False
                            recebidos.append("\n".join(corpo))
                            w("250 ok")
                        else:
                            corpo.append(linha)
                        continue
                    cmd = linha.upper()
                    if cmd.startswith("EHLO") or cmd.startswith("HELO"):
                        w("250 teste")
                    elif cmd.startswith("DATA"):
                        dados = True
                        w("354 vai")
                    elif cmd.startswith("QUIT"):
                        w("221 tchau")
                        return
                    else:
                        w("250 ok")

        servidor = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Manipulador)
        servidor.daemon_threads = True
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        env = {"ALERTAS_ENVIO": "smtp", "ALERTAS_SMTP_HOST": "127.0.0.1", "ALERTAS_SMTP_PORTA": str(servidor.server_address[1]),
               "ALERTAS_SMTP_SEGURANCA": "nenhuma", "ALERTAS_DE": "alertas@fornexia.exemplo"}
        with mock.patch.dict(os.environ, env):
            destino = envio.enviar(envio.mensagem_de_teste("cliente@empresa.com.br", AGORA))
        self.assertEqual(destino, "smtp:cliente@empresa.com.br")
        self.assertEqual(len(recebidos), 1)
        self.assertIn("Subject: FornexIA: teste do envio de alertas", recebidos[0])

    def test_destino_com_quebra_de_linha_e_recusado_na_montagem(self):
        a = self.assinar()
        a["email"] = "a@b.com\r\nBcc: x@y.com"
        with self.assertRaises(ass.ErroDeAssinatura):
            envio.montar(a, [], AGORA)


class TestEnvDoProjeto(unittest.TestCase):
    def test_carrega_o_env_sem_sobrescrever_e_sem_valor_vazio(self):
        import cli
        with tempfile.TemporaryDirectory() as d:
            arq = Path(d) / ".env"
            arq.write_text('# comentario\nALERTAS_T1=abc\nALERTAS_T2=\nALERTAS_T3="com aspas"\nALERTAS_T4=do-arquivo\nsem_igual\n', encoding="utf-8")
            with mock.patch.dict(os.environ, {"ALERTAS_T4": "do-ambiente"}):
                self.addCleanup(os.environ.pop, "ALERTAS_T1", None)
                self.addCleanup(os.environ.pop, "ALERTAS_T3", None)
                self.assertEqual(cli.carregar_env(arq), 2)
                self.assertEqual(os.environ["ALERTAS_T1"], "abc")
                self.assertNotIn("ALERTAS_T2", os.environ)               # vazio não vira variável
                self.assertEqual(os.environ["ALERTAS_T3"], "com aspas")
                self.assertEqual(os.environ["ALERTAS_T4"], "do-ambiente")  # o ambiente vence o arquivo
            self.assertEqual(cli.carregar_env(Path(d) / "nao-existe"), 0)


class TestSimular(unittest.TestCase):
    def test_recusa_sem_confirmacao_e_o_banco_padrao_do_bot(self):
        with mock.patch.dict(os.environ, {"NEO4J_URI": "bolt://127.0.0.1:7699"}):
            self.assertEqual(simular.main(["sancao-nova"]), 1)
        with mock.patch.dict(os.environ, {"NEO4J_URI": "bolt://127.0.0.1:7689"}):
            self.assertEqual(simular.main(["sancao-nova", "--banco-de-teste"]), 1)
        with mock.patch.dict(os.environ, {"NEO4J_URI": ""}):
            self.assertEqual(simular.main(["sancao-nova", "--banco-de-teste"]), 1)


def _neo4j_de_teste():
    """None se o banco de teste está no ar com os dados de exemplo; senão, o motivo de pular."""
    try:
        import mcp_transparencia as nucleo
        with nucleo.com_perfil("estado-exemplo", ["ex-estado"]):
            achados = nucleo.buscar_fornecedor(CNPJ)
        return None if achados else "sem os dados de exemplo (coleta/carregar_neo4j.py --zerar --exemplo)"
    except Exception as erro:
        return f"Neo4j de teste indisponível: {type(erro).__name__}"


MOTIVO = _neo4j_de_teste() if os.environ.get("NEO4J_URI") else "defina NEO4J_URI e NEO4J_SENHA para rodar contra o Neo4j de teste"


@unittest.skipIf(MOTIVO, MOTIVO or "")
class TestComNeo4j(Base):
    """A mudança nasce no grafo de verdade e o aviso passa pelas mesmas consultas do agente, com o perfil da assinatura."""

    def setUp(self):
        super().setUp()
        simular.main(["restaurar", "--banco-de-teste"])
        self.addCleanup(simular.main, ["restaurar", "--banco-de-teste"])

    def rodar_real(self):
        return monitor.verificar(self.loja, monitor.FonteGrafo, self.enviar, agora=AGORA)

    def test_sancao_nova_no_grafo_avisa_quem_enxerga_e_nao_avisa_quem_nao_enxerga(self):
        dono = self.assinar(email="dono@empresa.com.br", perfil="estado-exemplo")
        fora = self.assinar(email="fora@empresa.com.br", perfil="municipio")         # o plano de Garanhuns não enxerga o ex-estado
        r = self.rodar_real()
        self.assertEqual({x["id"]: x["linha_de_base"] for x in r}, {dono["id"]: [CNPJ], fora["id"]: [CNPJ]})
        self.assertEqual(simular.main(["sancao-nova", "--banco-de-teste"]), 0)
        r = {x["id"]: x for x in self.rodar_real()}
        self.assertEqual(r[dono["id"]]["eventos"], 1)
        e = r[dono["id"]]["lista"][0]
        self.assertEqual(e["tipo"], "sancao_nova")
        self.assertEqual(e["evidencia"], "sim:e1")
        self.assertTrue(e["capturado_em"])
        self.assertEqual(r[fora["id"]]["eventos"], 0)
        self.assertEqual([x[0]["id"] for x in self.enviados], [dono["id"]])

    def test_encerrar_e_contrato_novo_viram_avisos_diferentes(self):
        a = self.assinar()
        self.rodar_real()
        simular.main(["sancao-nova", "--banco-de-teste"])
        self.rodar_real()
        simular.main(["sancao-encerrada", "--banco-de-teste"])
        simular.main(["contrato-novo", "--banco-de-teste"])
        r = self.rodar_real()[0]
        self.assertEqual(sorted(e["tipo"] for e in r["lista"]), ["contrato_novo", "sancao_alterada"])
        self.assertEqual(a["perfil"], "estado-exemplo")

    def test_restaurar_o_banco_volta_ao_normal_sem_aviso_falso(self):
        self.assinar()
        self.rodar_real()
        simular.main(["sancao-nova", "--banco-de-teste"])
        self.rodar_real()
        simular.main(["restaurar", "--banco-de-teste"])
        r = self.rodar_real()[0]
        self.assertEqual([e["tipo"] for e in r["lista"]], ["sancao_removida"])


if __name__ == "__main__":
    unittest.main()
