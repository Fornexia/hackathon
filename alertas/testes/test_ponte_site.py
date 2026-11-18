"""Ponte do site sem enviar e-mail real, modelo ou banco de produção."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[2]
for pasta in ('alertas', 'consulta'):
    sys.path.insert(0, str(RAIZ / pasta))
import ponte_site as ponte
import envio
import monitor
from datetime import datetime

CNPJ = '76535764000143'
TODOS = {'estado': {'tenants': ['pe-estado'], 'ver_pessoal': False},
         'restrito': {'tenants': ['pe-estado', 'pessoal'], 'ver_pessoal': True}}
CONTA = {'usuario_id': 5, 'email': 'cliente@example.invalid', 'tenants': ['pe-estado'],
         'acompanhamentos': [{'id': 1, 'cnpj': CNPJ}]}


class Fonte:
    def __init__(self):
        self.dados = {'nome': 'Fornecedor', 'sancoes': [{'tipo': 'Impedimento', 'situacao': 'Vigente',
                      'cadastro': 'ceis', 'evidencia': 'ev1', 'ente': 'pe-estado'}], 'contratos': [], 'cadastro': []}

    def ler(self, cnpj):
        return copy.deepcopy(self.dados)

    def evidencia(self, id_):
        return {'url': 'https://portal.example.invalid', 'capturado_em': '2026-11-18'}


class TestPonte(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.arquivo = Path(self.tmp.name) / 'estado.json'
        self.contas, self.fonte, self.enviados = [copy.deepcopy(CONTA)], Fonte(), []
        self.p1 = patch.object(ponte, 'buscar', side_effect=lambda *a: self.contas)
        self.p2 = patch.object(ponte.perfis, 'carregar', return_value=TODOS)
        self.p1.start(); self.p2.start()
        self.addCleanup(self.p1.stop); self.addCleanup(self.p2.stop)

    def rodada(self, **kw):
        return ponte.rodada(self.arquivo, 'https://site.invalid/api', 'teste',
                            fabricar_fonte=lambda p: self.fonte,
                            enviar=kw.pop('enviar', lambda a, e, d: self.enviados.append((a, e)) or 'capturado'), **kw)

    def test_inicial_com_prova_uma_vez_depois_so_mudancas(self):
        self.rodada()
        self.assertEqual(len(self.enviados), 1)
        a, eventos = self.enviados[0]
        self.assertTrue(all(e['tipo'] == 'retrato_inicial' for e in eventos))
        self.assertTrue(any(e.get('evidencia') == 'ev1' and e.get('fonte_url') == 'https://portal.example.invalid' for e in eventos))
        self.rodada()
        self.assertEqual(len(self.enviados), 1)
        self.fonte.dados['sancoes'][0]['situacao'] = 'Encerrada'
        self.rodada()
        self.assertEqual(len(self.enviados), 2)
        self.assertEqual(self.enviados[-1][1][0]['tipo'], 'sancao_alterada')

    def test_falha_smtp_nao_perde_inicial(self):
        def falhar(*args): raise OSError('SMTP indisponível')
        self.assertIn('erro_de_envio', self.rodada(enviar=falhar)[0])
        self.rodada()
        self.assertEqual(len(self.enviados), 1)
        self.rodada()
        self.assertEqual(len(self.enviados), 1)

    def test_sem_resultado_tambem_confirma_com_limite_da_amostra(self):
        self.fonte.dados = None
        self.rodada()
        self.assertIn('ausência', self.enviados[0][1][0]['detalhe'])
        self.rodada()
        self.assertEqual(len(self.enviados), 1)

    def test_cancelar_apaga_foto_e_reincluir_reenvia_inicial(self):
        self.rodada()
        self.contas = []
        self.rodada()
        self.assertEqual(json.loads(self.arquivo.read_text()), {})
        self.contas = [copy.deepcopy(CONTA)]
        self.contas[0]['acompanhamentos'][0]['id'] = 2
        self.rodada()
        self.assertEqual(len(self.enviados), 2)

    def test_reincluir_entre_rodadas_tem_nova_linha_de_base(self):
        self.rodada()
        self.contas[0]['acompanhamentos'][0]['id'] = 2
        self.rodada()
        self.assertEqual(len(self.enviados), 2)

    def test_site_indisponivel_nao_envia_nem_altera_estado(self):
        self.rodada()
        antes = self.arquivo.read_bytes()
        with patch.object(ponte, 'buscar', side_effect=OSError('sem conexão')):
            with self.assertRaises(OSError): self.rodada()
        self.assertEqual(self.arquivo.read_bytes(), antes)
        self.assertEqual(len(self.enviados), 1)

    def test_perfil_nunca_amplia_plano_nem_le_dado_pessoal(self):
        self.contas[0]['tenants'] = ['pe-estado', 'pessoal']
        self.rodada()
        self.assertEqual(self.enviados, [])
        self.contas[0]['tenants'] = ['desconhecido']
        self.rodada()
        self.assertEqual(self.enviados, [])

    def test_trocar_email_ou_plano_nao_reutiliza_foto(self):
        self.rodada()
        self.contas[0]['email'] = 'outro@example.invalid'
        self.rodada()
        self.assertEqual(len(self.enviados), 2)
        self.assertEqual(len(json.loads(self.arquivo.read_text())), 1)

    def test_resposta_invalida_aborta_antes_do_envio(self):
        self.contas += [{'usuario_id': 6}]
        with self.assertRaises(KeyError): self.rodada()
        self.assertEqual(self.enviados, [])
        self.assertFalse(self.arquivo.exists())

    def test_ensaio_nao_envia_nem_grava(self):
        self.assertTrue(self.rodada(ensaio=True)[0]['eventos'])
        self.assertEqual(self.enviados, [])
        self.assertFalse(self.arquivo.exists())

    def test_email_site_traz_link_e_nao_comando_ou_token(self):
        self.rodada()
        a, eventos = self.enviados[0]
        msg = envio.montar(a, eventos, datetime.now().astimezone())
        self.assertIn('retrato', str(msg['Subject']))
        for parte in (msg.get_body(('plain',)), msg.get_body(('html',))):
            texto = parte.get_content()
            self.assertIn('/conta.html', texto)
            self.assertNotIn('cli.py', texto)
            self.assertNotIn('Nova ocorrência', texto)

    def test_seguranca_smtp_desconhecida_falha_antes_de_conectar(self):
        with patch.dict(os.environ, {'ALERTAS_ENVIO': 'smtp', 'ALERTAS_SMTP_HOST': 'smtp.invalid',
                        'ALERTAS_DE': 'a@example.invalid', 'ALERTAS_SMTP_SEGURANCA': 'tls-digitado-errado'}):
            with patch.object(envio.smtplib, 'SMTP') as smtp:
                with self.assertRaisesRegex(RuntimeError, 'SEGURANCA'):
                    envio.enviar(envio.mensagem_de_teste('b@example.invalid', datetime.now().astimezone()))
                smtp.assert_not_called()

    def test_reutiliza_smtp_login_sem_sobrescrever_alertas(self):
        with patch.dict(os.environ, {'SMTP_HOST': 'smtp.example.invalid', 'SMTP_SECURITY': 'ssl',
                        'SMTP_PORT': '465', 'ALERTAS_SMTP_HOST': 'outro.example.invalid'}, clear=True):
            ponte.configurar_email()
            self.assertEqual(os.environ['ALERTAS_SMTP_HOST'], 'outro.example.invalid')
            self.assertEqual(os.environ['ALERTAS_SMTP_SEGURANCA'], 'ssl')
            self.assertEqual(os.environ['ALERTAS_SMTP_PORTA'], '465')


if __name__ == '__main__': unittest.main()
