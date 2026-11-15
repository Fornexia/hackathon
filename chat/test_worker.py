"""Regressões do chat: não consome modelos nem usa o banco de produção.

    .venv/bin/python -m unittest discover -s chat -p 'test_*.py' -v
"""
import json
import socket
import ssl
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agente
import agente_codex
import http_api
import worker


class TestRoteamento(unittest.TestCase):
    def test_codex_nao_inicia_claude_nem_faz_fallback(self):
        with patch.object(agente_codex, 'perguntar', return_value=iter([('erro', {'motivo':'limite Codex'})])) as codex, \
             patch.object(agente.subprocess, 'Popen') as popen:
            eventos = list(agente.perguntar('pergunta', ['pe-garanhuns'], provedor='codex'))
        self.assertEqual(eventos, [('erro', {'motivo':'limite Codex'})])
        codex.assert_called_once()
        popen.assert_not_called()

    def test_worker_do_site_seleciona_codex_e_entrega_fonte_texto_e_fim(self):
        sequencia = [('consulta',{'nome':'cobertura'}),('fonte',{'trecho':'Prova','url':'https://exemplo.test'}),
                     ('texto',{'delta':'Resposta'}),('fim',{'duracao_ms':10})]
        with patch.object(worker, 'PROVEDOR_SITE', 'codex'), \
             patch.object(worker.agente, 'perguntar', return_value=iter(sequencia)) as perguntar, \
             patch.object(worker, 'api', return_value=(200,{})) as api, \
             patch.object(worker, 'gravar_log') as log:
            worker.atender_site({'id':1,'usuario_id':991,'tenants':['pe-garanhuns'],'texto':'pergunta'})
        self.assertEqual(perguntar.call_args.kwargs['provedor'],'codex')
        eventos = [e for c in api.call_args_list for e in c.args[2]['eventos']]
        self.assertEqual([e['tipo'] for e in eventos],['consulta','fonte','texto','fim'])
        self.assertEqual(log.call_args.kwargs['desfecho'],'concluida')
        self.assertEqual(log.call_args.kwargs['provedor'],'codex')

    def test_historico_municipal_nao_reutiliza_estado(self):
        self.assertNotEqual(worker.chave_entes(['pe-garanhuns']),worker.chave_entes(['pe-garanhuns','pe-estado']))
        self.assertEqual(worker.chave_entes(['pe-garanhuns','pe-estado']),worker.chave_entes(['pe-estado','pe-garanhuns']))


class TestEventosCodex(unittest.TestCase):
    def test_fonte_preserva_prova_mascara_cpf_e_nao_duplica(self):
        leitor=agente.Leitor()
        item={'type':'mcpToolCall','server':'transparencia','tool':'conferir_evidencia','status':'completed',
              'arguments':{'evidencia_id':'e1'},'result':{'content':[{'type':'text','text':json.dumps({
                  'trecho':'Trecho 123.456.789-00','url':'https://portal.test/fonte','hash_confere':True,'capturado_em':'2026-11-06'})}]}}
        eventos=agente_codex.eventos_do_item(item,leitor)
        self.assertEqual(eventos[0][0],'fonte')
        self.assertEqual(eventos[0][1]['trecho'],'Trecho [CPF]')
        self.assertTrue(eventos[0][1]['hash_confere'])
        self.assertEqual(agente_codex.eventos_do_item(item,leitor),[])

    def test_tool_falha_nao_vira_fonte(self):
        item={'type':'mcpToolCall','server':'transparencia','tool':'conferir_evidencia','status':'failed','error':{'message':'erro'}}
        self.assertEqual(agente_codex.eventos_do_item(item,agente.Leitor()),[])

    def test_operacoes_fora_da_lista_sao_recusadas(self):
        for item in [{'type':'mcpToolCall','server':'outro','tool':'ler_segredo'},
                     {'type':'mcpToolCall','server':'transparencia','tool':'executar_cypher'},
                     {'type':'commandExecution'}, {'type':'fileChange'}]:
            with self.assertRaises(agente_codex.ErroCodex):
                agente_codex.eventos_do_item(item,agente.Leitor())

    def test_so_a_resposta_final_vira_texto(self):
        leitor=agente.Leitor()
        self.assertEqual(agente_codex.eventos_do_item({'type':'agentMessage','phase':'commentary','text':'Vou consultar'},leitor),[])
        self.assertEqual(agente_codex.eventos_do_item({'type':'agentMessage','phase':'final_answer','text':'Resposta'},leitor),[('texto',{'delta':'Resposta'})])
        self.assertEqual(leitor.resposta,'Resposta')

    def test_sem_autenticacao_falha_sem_iniciar_modelo(self):
        with tempfile.TemporaryDirectory() as d, patch.dict('os.environ',{'CODEX_AUTH_HOME':d,'CODEX_MODELO':'modelo-teste'}), \
             patch.object(agente_codex, 'Sessao') as sessao:
            eventos=list(agente_codex.perguntar('pergunta',['pe-garanhuns'],[],agente.Leitor()))
        self.assertEqual(eventos[0][0],'erro')
        self.assertIn('autenticado',eventos[0][1]['motivo'])
        sessao.assert_not_called()


class TestConexaoIPv4(unittest.TestCase):
    def test_seleciona_ipv4_tenta_outro_endereco_e_fecha_socket_com_falha(self):
        primeiro,segundo=Mock(),Mock()
        primeiro.connect.side_effect=OSError('indisponível')
        enderecos=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('192.0.2.1',443)),
                   (socket.AF_INET,socket.SOCK_STREAM,6,'',('192.0.2.2',443))]
        with patch.object(http_api.socket,'getaddrinfo',return_value=enderecos) as resolver, \
             patch.object(http_api.socket,'socket',side_effect=[primeiro,segundo]):
            self.assertIs(http_api.conectar_ipv4(('api.test',443),20),segundo)
        self.assertEqual(resolver.call_args.args[2],socket.AF_INET)
        primeiro.close.assert_called_once()
        segundo.settimeout.assert_called_once_with(20)

    def test_handler_funciona_com_python_312(self):
        handler=http_api.HTTPSIPv4()
        with patch.object(handler,'do_open',return_value='ok') as abrir:
            self.assertEqual(handler.https_open(Mock()),'ok')
        self.assertIs(abrir.call_args.args[0],http_api.ConexaoHTTPSIPv4)
        self.assertIn('context',abrir.call_args.kwargs)

    def test_preserva_verificacao_tls_e_hostname(self):
        conexao=http_api.ConexaoHTTPSIPv4('api.test',timeout=20)
        self.assertTrue(conexao._context.check_hostname)
        self.assertEqual(conexao._context.verify_mode,ssl.CERT_REQUIRED)
        self.assertIs(conexao._create_connection,http_api.conectar_ipv4)


if __name__=='__main__': unittest.main()
