"""Mede 100 perguntas independentes no Codex com o MCP real do FornexIA.

Uso: .venv/bin/python bench/benchmark_codex.py --saida dados/bench/codex-<rodada>
Resultados com dados reais ficam na pasta dados/ (ignorada pelo Git).
Não altera o worker, o site, o grafo nem a apresentação.
"""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import tomllib

CODEX = os.environ.get('FORNEXIA_CODEX_BIN', 'codex')
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'chat'))
import agente
import benchmark


def gravar(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def perguntas():
    base = benchmark.fatos()
    contratos = base['contratos']
    fornecedores = list({c['cnpj']: c for c in contratos}.values())
    saida = []
    def add(tipo, texto):
        saida.append({'id': len(saida)+1, 'tipo': tipo, 'pergunta': texto})
    for texto in [
        'Quais fontes e anos estão disponíveis na base?',
        'Quantos contratos há na amostra disponível?',
        'Qual é o maior contrato disponível e quem é o fornecedor?',
        'Quais são os três maiores contratos de Garanhuns na base?',
        'Quais são os três maiores contratos do Estado de Pernambuco na base?',
        'Quantos fornecedores podemos consultar na amostra?',
        'Quais são as limitações da cobertura de sanções?',
        'A base permite consultar contratos do Estado de 2025?',
        'Quais entes públicos estão disponíveis para consulta?',
        'O que pode ser consultado sobre execução financeira nesta base?',
    ]: add('cobertura', texto)
    for c in fornecedores[:30]:
        add('contratos', f"Quais contratos constam para o CNPJ {c['cnpj']}? Informe até três exemplos com os valores contratados e as fontes.")
    for c in sorted(fornecedores, key=lambda c: (-c['sancoes'], c['cnpj']))[:25]:
        add('sancoes', f"Há sanções para o CNPJ {c['cnpj']}? Informe a quantidade, a situação disponível e até três evidências; explique os limites dessa informação.")
    execucoes = list({x['cnpj']: x for x in base['execucoes']}.values())[:20]
    for x in execucoes:
        add('execucao', f"Qual execução financeira consta para o CNPJ {x['cnpj']} no ano {x['ano']}? Diferencie empenhado, liquidado e pago e esclareça se o pago pertence a algum contrato específico.")
    for c in fornecedores[30:40]:
        add('historico', f"Busque o fornecedor {c['cnpj']} e resuma o histórico de contratação e de sanções que a base permite comprovar, com até três fontes.")
    for texto in [
        'A ausência de sanções na amostra prova que um fornecedor nunca foi sancionado?',
        'Uma multa em aberto prova que um fornecedor cometeu irregularidade?',
        'Podemos dizer quanto foi pago de um contrato usando o total de execução por fornecedor?',
        'Se o número do processo não consta no portal, isso significa contratação sem licitação?',
        'Consigo consultar CPF ou dados pessoais de fornecedores nesta demonstração?',
    ]: add('limites', texto)
    assert len(saida) == 100, len(saida)
    assert len({p['pergunta'] for p in saida}) == 100
    return saida


class Servidor:
    def __init__(self, home, log):
        self.lock = threading.Lock()
        self.pendentes = {}
        self.filas = {}
        self.contador = 0
        self.eventos_limite = []
        self.p = subprocess.Popen([CODEX, 'app-server'], cwd=home.parent,
            env={**os.environ, 'CODEX_HOME': str(home)}, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=log, text=True, encoding='utf-8', start_new_session=True)
        threading.Thread(target=self.ler, daemon=True).start()
        self.rpc('initialize', {'clientInfo': {'name': 'fornexia-benchmark', 'version': '1.0'},
                               'capabilities': {'experimentalApi': True}})
        self.enviar({'method': 'initialized'})

    def enviar(self, d):
        with self.lock:
            self.p.stdin.write(json.dumps(d)+'\n')
            self.p.stdin.flush()

    def ler(self):
        for linha in self.p.stdout:
            try: m = json.loads(linha)
            except ValueError: continue
            if 'id' in m and 'method' not in m:
                q = self.pendentes.get(m['id'])
                if q: q.put(m)
                continue
            if 'id' in m:  # Nenhuma interação/aprovação de escrita é permitida no benchmark.
                self.enviar({'id': m['id'], 'error': {'code': -32601, 'message': 'Operação interativa não autorizada no benchmark'}})
                continue
            params = m.get('params') or {}
            if m.get('method') == 'account/rateLimits/updated':
                self.eventos_limite.append({'timestamp': time.time(), 'params': params})
            tid = params.get('threadId') or (params.get('thread') or {}).get('id')
            if tid:
                self.filas.setdefault(tid, queue.Queue()).put(m)

    def rpc(self, method, params=None, timeout=90):
        with self.lock:
            self.contador += 1
            ident = self.contador
            q = self.pendentes[ident] = queue.Queue()
        self.enviar({'id': ident, 'method': method, **({'params': params} if params is not None else {})})
        try: r = q.get(timeout=timeout)
        finally: self.pendentes.pop(ident, None)
        if 'error' in r: raise RuntimeError(json.dumps(r['error'], ensure_ascii=False))
        return r['result']

    def limites(self):
        return {'timestamp': time.time(), **self.rpc('account/rateLimits/read')}

    def consulta(self, pergunta, modelo, diretorio):
        inicio = time.monotonic()
        r = dict(pergunta, inicio_utc=dt.datetime.now(dt.timezone.utc).isoformat(), itens=[], tokens=None)
        tid = None
        try:
            th = self.rpc('thread/start', {'cwd': str(diretorio), 'model': modelo,
                'approvalPolicy': 'never', 'sandbox': 'read-only', 'ephemeral': True,
                'baseInstructions': agente.REGRAS,
                'developerInstructions': 'Use exclusivamente as oito ferramentas do MCP transparencia. Não execute comandos, não escreva arquivos, não use web ou agentes auxiliares.'})
            tid = th['thread']['id']
            r['thread_id'] = tid
            r['modelo'] = th.get('model')
            inventario = self.rpc('mcpServerStatus/list', {'threadId': tid, 'serverName': 'transparencia', 'detail': 'toolsAndAuthOnly'})
            r['mcp_ferramentas'] = {x['name']: list(x.get('tools', {})) for x in inventario['data']}
            if not any(x.get('tools') for x in inventario['data']):
                raise RuntimeError('Servidor MCP sem ferramentas disponíveis')
            self.rpc('turn/start', {'threadId': tid, 'input': [{'type': 'text', 'text': pergunta['pergunta']}], 'effort': 'medium'})
            q = self.filas.setdefault(tid, queue.Queue())
            prazo = time.monotonic()+180
            while time.monotonic() < prazo:
                m = q.get(timeout=max(1, prazo-time.monotonic()))
                tipo, p = m.get('method'), m.get('params', {})
                if tipo == 'item/completed': r['itens'].append(p['item'])
                elif tipo == 'thread/tokenUsage/updated': r['tokens'] = p['tokenUsage']['total']
                elif tipo == 'error': r.setdefault('avisos', []).append(p)
                elif tipo == 'turn/completed':
                    r['status'] = p['turn']['status']
                    if p['turn'].get('error'): r['erro'] = p['turn']['error']
                    break
            else: r['status'] = 'timeout'
        except Exception as e:
            r['status'], r['erro'] = 'erro', f'{type(e).__name__}: {e}'
        finally:
            if tid:
                # Encerra o MCP da pergunta concluída antes de abrir a próxima.
                try: self.rpc('thread/unsubscribe', {'threadId': tid}, timeout=10)
                except Exception: pass
                self.filas.pop(tid, None)
        r['duracao_s'] = round(time.monotonic()-inicio, 3)
        r['resposta'] = '\n'.join(x.get('text', '') for x in r['itens'] if x.get('type') == 'agentMessage')
        calls = [x for x in r['itens'] if x.get('type') == 'mcpToolCall']
        r['tools'] = [x.get('tool') for x in calls]
        r['tools_ok'] = len([x for x in calls if x.get('status') == 'completed' and not x.get('error')])
        r['sucesso_operacional'] = r.get('status') == 'completed' and bool(r['resposta']) and r['tools_ok'] > 0
        return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--saida', type=Path, required=True)
    ap.add_argument('--paralelo', type=int, default=3)
    args = ap.parse_args()
    pasta = args.saida.resolve()
    pasta.mkdir(parents=True, exist_ok=False)
    itens = perguntas()
    gravar(pasta/'perguntas.json', itens)
    user_config = tomllib.loads((Path.home()/'.codex/config.toml').read_text())
    modelo = user_config.get('model', 'gpt-6.1-sol')
    home = Path(tempfile.mkdtemp(prefix='fornexia-codex-'))
    os.chmod(home, 0o700)
    shutil.copyfile(Path.home()/'.codex/auth.json', home/'auth.json')
    os.chmod(home/'auth.json', 0o600)
    neutro = home/'neutro'
    neutro.mkdir()
    config = f'''model = {json.dumps(modelo)}
model_reasoning_effort = "medium"
approval_policy = "never"
sandbox_mode = "read-only"
web_search = "disabled"
[features]
shell_tool = false
apps = false
plugins = false
memories = false
[agents]
enabled = false
[mcp_servers.transparencia]
default_tools_approval_mode = "approve"
command = {json.dumps(agente.PYTHON)}
args = [{json.dumps(str(RAIZ/'consulta/mcp_transparencia.py'))}]
enabled_tools = {json.dumps(list(agente.PRIMITIVAS))}
[mcp_servers.transparencia.env]
TRANSPARENCIA_PERFIL = "estado"
TRANSPARENCIA_TENANTS = "pe-estado,pe-garanhuns"
TRANSPARENCIA_VER_PESSOAL = "nao"
TRANSPARENCIA_SESSAO = "benchmark-codex"
TRANSPARENCIA_LOG = {json.dumps(str(pasta/'consultas-mcp.jsonl'))}
'''
    (home/'config.toml').write_text(config)
    metadados = {'modelo': modelo, 'esforco': 'medium', 'paralelismo': args.paralelo,
                 'preco_mensal_codex_brl_premissa': 515, 'preco_mensal_vps_brl_premissa': 197,
                 'perguntas_sha256': hashlib.sha256((pasta/'perguntas.json').read_bytes()).hexdigest(),
                 'cli': subprocess.check_output([CODEX, '--version'], text=True).strip()}
    gravar(pasta/'metadados.json', metadados)
    servidor = None
    resultados = []
    inicio = time.monotonic()
    try:
        with (pasta/'servidor.stderr.log').open('w') as log:
            servidor = Servidor(home, log)
            a = servidor.rpc('account/read', {'refreshToken': False}).get('account') or {}
            metadados['plano'] = a.get('planType')
            gravar(pasta/'metadados.json', metadados)
            antes = servidor.limites()
            gravar(pasta/'limites-antes.json', antes)
            print(json.dumps({'evento': 'inicio', 'modelo': modelo, 'plano': a.get('planType'), 'limites': antes['rateLimits']}, ensure_ascii=False), flush=True)
            primeiro = servidor.consulta(itens[0], modelo, neutro)
            resultados.append(primeiro)
            gravar(pasta/'consulta-001.json', primeiro)
            print(json.dumps({'evento': 'piloto', 'sucesso': primeiro['sucesso_operacional'], 'status': primeiro['status'], 'tools': primeiro['tools'], 'duracao_s': primeiro['duracao_s'], 'erro': primeiro.get('erro')}, ensure_ascii=False), flush=True)
            if not primeiro['sucesso_operacional']:
                raise RuntimeError('Piloto falhou; as outras 99 perguntas não foram iniciadas.')
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.paralelo) as pool:
                futures = {pool.submit(servidor.consulta, p, modelo, neutro): p for p in itens[1:]}
                for fut in concurrent.futures.as_completed(futures):
                    r = fut.result()
                    resultados.append(r)
                    gravar(pasta/f"consulta-{r['id']:03}.json", r)
                    if len(resultados) % 10 == 0:
                        limite = servidor.limites()
                        gravar(pasta/f'limites-{len(resultados):03}.json', limite)
                        print(json.dumps({'evento': 'progresso', 'concluidas': len(resultados), 'sucessos': sum(r['sucesso_operacional'] for r in resultados), 'duracao_s': round(time.monotonic()-inicio), 'limites': limite['rateLimits']}, ensure_ascii=False), flush=True)
            duracao = time.monotonic()-inicio
            time.sleep(5)
            depois = servidor.limites()
            gravar(pasta/'limites-depois.json', depois)
            gravar(pasta/'notificacoes-limites.json', servidor.eventos_limite)
            gravar(pasta/'resumo.json', {'total':len(resultados), 'sucessos_operacionais':sum(r['sucesso_operacional'] for r in resultados),
                'duracao_total_s': round(duracao, 3), 'latencia_media_s': statistics.mean(r['duracao_s'] for r in resultados),
                'latencia_mediana_s': statistics.median(r['duracao_s'] for r in resultados),
                'tokens': {k:sum((r['tokens'] or {}).get(k,0) for r in resultados) for k in ['inputTokens','cachedInputTokens','outputTokens','reasoningOutputTokens','totalTokens']},
                'antes':antes, 'depois':depois})
            print(json.dumps({'evento':'fim','total':len(resultados),'duracao_s':round(duracao),'sucessos':sum(r['sucesso_operacional'] for r in resultados),'saida':str(pasta)},ensure_ascii=False),flush=True)
    finally:
        if servidor:
            os.killpg(servidor.p.pid, signal.SIGTERM)
            try: servidor.p.wait(timeout=10)
            except subprocess.TimeoutExpired: servidor.p.kill()
        shutil.rmtree(home, ignore_errors=True)


if __name__ == '__main__':
    main()
