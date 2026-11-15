"""Adaptador Codex/ChatGPT para os mesmos eventos do agente do FornexIA.

Uma sessão/processo por pergunta, somente com o MCP de transparência. Não há
fallback para Claude, acesso a outros conectores nem ferramentas de shell/escrita.
"""
import collections
import json
import os
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import tomllib

import agente


class ErroCodex(RuntimeError):
    pass


def binario():
    explicito = os.environ.get('CODEX_BIN')
    if explicito:
        if not Path(explicito).is_file():
            raise ErroCodex('CODEX_BIN não foi encontrado.')
        return explicito
    # O CLI antigo no PATH não entende o catálogo/modelos atuais. O binário da
    # extensão é o mesmo cliente validado no benchmark e acompanha suas atualizações.
    candidatos = list((Path.home()/'.vscode/extensions').glob('openai.chatgpt-*/bin/linux-x86_64/codex'))
    if candidatos:
        return str(max(candidatos, key=lambda p: p.stat().st_mtime))
    encontrado = shutil.which('codex')
    if not encontrado:
        raise ErroCodex('Codex não está instalado para o worker.')
    return encontrado


def modelo_configurado():
    if os.environ.get('CODEX_MODELO'):
        return os.environ['CODEX_MODELO']
    cfg = Path.home()/'.codex/config.toml'
    dados = tomllib.loads(cfg.read_text()) if cfg.exists() else {}
    if not dados.get('model'):
        raise ErroCodex('Configure o modelo do Codex antes de iniciar o worker.')
    return dados['model']


class Sessao:
    def __init__(self, home, cwd, stderr, limite_s):
        self.prazo = time.monotonic()+limite_s
        self.fila = queue.Queue()
        self.notificacoes = collections.deque()
        self.contador = 0
        self.proc = subprocess.Popen([binario(), 'app-server'], cwd=cwd,
            env={**os.environ, 'CODEX_HOME': str(home)}, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=stderr, text=True, encoding='utf-8',
            start_new_session=True)
        threading.Thread(target=self.ler, daemon=True).start()

    def ler(self):
        try:
            for linha in self.proc.stdout:
                try: self.fila.put(json.loads(linha))
                except ValueError: pass
        finally:
            self.fila.put(None)

    def enviar(self, d):
        self.proc.stdin.write(json.dumps(d)+'\n')
        self.proc.stdin.flush()

    def receber(self):
        espera = self.prazo-time.monotonic()
        if espera <= 0:
            raise TimeoutError('A consulta demorou mais que o esperado.')
        try: m = self.fila.get(timeout=espera)
        except queue.Empty: raise TimeoutError('A consulta demorou mais que o esperado.') from None
        if m is None:
            raise ErroCodex('O processo Codex encerrou sem terminar a resposta.')
        if 'method' in m and 'id' in m:
            # As consultas de leitura do MCP já foram explicitamente autorizadas
            # na configuração. Nenhuma aprovação interativa adicional é concedida.
            self.enviar({'id': m['id'], 'error': {'code': -32601,
                'message': 'Operação interativa não disponível neste assistente.'}})
            return self.receber()
        return m

    def rpc(self, metodo, params=None):
        self.contador += 1
        ident = self.contador
        self.enviar({'id': ident, 'method': metodo, **({'params': params} if params is not None else {})})
        while True:
            m = self.receber()
            if m.get('id') == ident:
                if 'error' in m:
                    raise ErroCodex(str(m['error'].get('message', 'Erro na sessão Codex.')))
                return m['result']
            if 'method' in m:
                self.notificacoes.append(m)

    def proxima(self):
        return self.notificacoes.popleft() if self.notificacoes else self.receber()

    def fechar(self):
        try: os.killpg(self.proc.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try: os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            self.proc.wait(timeout=3)


def eventos_do_item(item, leitor):
    """Traduz o resultado concluído sem interpretar HTML nem expor texto de erro interno."""
    if item.get('type') == 'mcpToolCall':
        if item.get('server') != 'transparencia' or item.get('tool') not in agente.PRIMITIVAS:
            raise ErroCodex('O agente tentou uma ferramenta fora do perfil permitido.')
        if item.get('status') != 'completed' or item.get('error'):
            return []
        if item['tool'] != 'conferir_evidencia':
            return []
        ident = str((item.get('arguments') or {}).get('evidencia_id', ''))
        fontes = []
        for dado in agente._itens((item.get('result') or {}).get('content') or []):
            if dado.get('trecho') and ident not in leitor.evidencias:
                leitor.evidencias.append(ident)
                fontes.append(('fonte', {'evidencia': ident,
                    'trecho': agente.CPF.sub('[CPF]', str(dado['trecho']))[:1500],
                    'url': dado.get('url'), 'capturado_em': dado.get('capturado_em'),
                    'hash_confere': bool(dado.get('hash_confere'))}))
        return fontes
    if item.get('type') == 'agentMessage' and item.get('phase') in (None, 'final_answer'):
        texto = str(item.get('text') or '')
        if texto:
            leitor.resposta += texto
            return [('texto', {'delta': texto})]
    if item.get('type') in ('commandExecution', 'fileChange', 'collabAgentToolCall'):
        raise ErroCodex('O agente tentou uma operação indisponível neste assistente.')
    return []


def perguntar(texto, tenants, historico, leitor):
    inicio = time.monotonic()
    perfil = agente.perfil_dos_entes(tenants)  # Correspondência exata; nunca amplia acesso.
    modelo = modelo_configurado()
    auth_home = Path(os.environ.get('CODEX_AUTH_HOME', Path.home()/'.codex'))
    sessao = None
    with tempfile.TemporaryDirectory(prefix='fornexia-codex-') as temporario:
        home = Path(temporario)
        (home/'neutro').mkdir()
        origem = auth_home/'auth.json'
        if not origem.exists():
            yield ('erro', {'motivo': 'Codex não está autenticado para o assistente.'})
            return
        shutil.copyfile(origem, home/'auth.json')
        (home/'auth.json').chmod(0o600)
        env = agente.perfis.ambiente(perfil)
        env['TRANSPARENCIA_SESSAO'] = 'site-codex-'+str(time.time_ns())
        linhas = [f'model = {json.dumps(modelo)}', 'model_reasoning_effort = "medium"',
            'approval_policy = "never"', 'sandbox_mode = "read-only"', 'web_search = "disabled"',
            'mcp_optional_startup_grace_ms = 0', '[features]', 'shell_tool = false',
            'apps = false', 'plugins = false', 'memories = false', '[agents]', 'enabled = false',
            '[mcp_servers.transparencia]', 'required = true',
            'default_tools_approval_mode = "approve"', f'command = {json.dumps(agente.PYTHON)}',
            f'args = [{json.dumps(str(agente.perfis.SERVIDOR))}]',
            f'enabled_tools = {json.dumps(list(agente.PRIMITIVAS))}',
            '[mcp_servers.transparencia.env]', *[f'{k} = {json.dumps(v)}' for k,v in env.items()]]
        (home/'config.toml').write_text('\n'.join(linhas)+'\n')
        with (home/'stderr.log').open('w') as log:
            try:
                sessao = Sessao(home, home/'neutro', log, agente.LIMITE_S)
                sessao.rpc('initialize', {'clientInfo': {'name':'fornexia-worker','version':'1.0'},
                    'capabilities': {'experimentalApi':True}})
                sessao.enviar({'method':'initialized'})
                th = sessao.rpc('thread/start', {'cwd':str(home/'neutro'), 'model':modelo,
                    'approvalPolicy':'never','sandbox':'read-only','ephemeral':True,
                    'baseInstructions':agente.REGRAS,
                    'developerInstructions':'Use somente o MCP transparencia. Nunca execute comandos, escreva arquivos ou delegue a agentes.'})
                tid = th['thread']['id']
                catalogo = sessao.rpc('mcpServerStatus/list', {'threadId':tid,'serverName':'transparencia','detail':'toolsAndAuthOnly'})
                if not any(x.get('tools') for x in catalogo['data']):
                    raise ErroCodex('As consultas da base não estão disponíveis.')
                sessao.rpc('turn/start', {'threadId':tid,'effort':'medium',
                    'input':[{'type':'text','text':agente.montar_prompt(texto,historico)}]})
                calls = set()
                while True:
                    m = sessao.proxima()
                    p = m.get('params') or {}
                    metodo = m.get('method')
                    if p.get('threadId') not in (None, tid): continue
                    if metodo == 'item/started' and p.get('item',{}).get('type') == 'mcpToolCall':
                        item = p['item']
                        if item.get('server') != 'transparencia' or item.get('tool') not in agente.PRIMITIVAS:
                            raise ErroCodex('Ferramenta fora do perfil permitido.')
                        if item['id'] not in calls:
                            calls.add(item['id'])
                            if len(calls) > 12: raise ErroCodex('A pergunta exigiu consultas demais. Pergunte por um fornecedor ou recorte específico.')
                            leitor.consultas.append(item['tool'])
                            yield ('consulta', {'nome':item['tool']})
                    elif metodo == 'item/completed':
                        yield from eventos_do_item(p['item'],leitor)
                    elif metodo == 'turn/completed':
                        turno = p['turn']
                        if turno['status'] != 'completed' or not leitor.resposta:
                            erro = turno.get('error') or {}
                            raise ErroCodex(str(erro.get('message') or 'Codex encerrou sem resposta.'))
                        yield ('fim', {'duracao_ms':round((time.monotonic()-inicio)*1000)})
                        return
            except TimeoutError:
                yield ('erro', {'motivo':'A consulta demorou mais que o esperado. Tente uma pergunta mais específica.'})
            except Exception as erro:
                # Diagnóstico operacional no journal; o worker envia uma mensagem neutra ao navegador.
                print('Codex:',type(erro).__name__,str(erro)[:300],flush=True)
                yield ('erro', {'motivo':str(erro) if isinstance(erro,ErroCodex) and 'consultas demais' in str(erro) else 'O assistente está temporariamente indisponível. Tente novamente.'})
            finally:
                if sessao: sessao.fechar()
