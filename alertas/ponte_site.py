"""Consulta os acompanhamentos do site e executa o monitor. Só conexões de saída.

python alertas/ponte_site.py [--uma-vez] [--ensaio]
Estado separado do CLI; uma falha no site impede todos os envios daquela rodada.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

RAIZ = Path(__file__).resolve().parents[1]
for pasta in ('alertas', 'consulta', 'chat'):
    sys.path.insert(0, str(RAIZ / pasta))
import assinaturas
import envio
import monitor
import perfis
from cli import carregar_env
from http_api import criar_cliente


def configurar_email():
    """Reutiliza a caixa do login, sem sobrescrever opções explícitas dos alertas."""
    for destino, origem in (("ALERTAS_SMTP_HOST", "SMTP_HOST"), ("ALERTAS_SMTP_PORTA", "SMTP_PORT"),
                            ("ALERTAS_SMTP_USUARIO", "SMTP_USER"), ("ALERTAS_SMTP_SENHA", "SMTP_PASS"), ("ALERTAS_DE", "MAIL_FROM")):
        if os.environ.get(origem) and not os.environ.get(destino):
            os.environ[destino] = os.environ[origem]
    if not os.environ.get('ALERTAS_SMTP_SEGURANCA'):
        os.environ['ALERTAS_SMTP_SEGURANCA'] = {'tls': 'starttls', 'ssl': 'ssl'}.get(os.environ.get('SMTP_SECURITY', 'tls'), 'starttls')


def buscar(api, chave):
    req = urllib.request.Request(api.rstrip('/') + '/worker/acompanhamentos',
                                 headers={'X-Worker-Key': chave, 'User-Agent': 'fornexia-alertas/1.0'})
    with criar_cliente().open(req, timeout=20) as resposta:
        dados = json.loads(resposta.read(2_000_001).decode('utf-8'))
    if not isinstance(dados, list):
        raise ValueError('resposta inesperada do site')
    return dados


def montar(contas, todos):
    """Valida a resposta inteira antes de enviar; perfil exige os entes exatos e sem dado pessoal."""
    itens = []
    vistos = set()
    for c in contas:
        uid = c['usuario_id']
        if type(uid) is not int or uid <= 0 or uid in vistos:
            raise ValueError('conta inválida ou duplicada')
        vistos.add(uid)
        email = assinaturas.validar_email(c['email'])
        tenants = c['tenants']
        if not isinstance(tenants, list) or not tenants or not all(isinstance(t, str) and t for t in tenants):
            raise ValueError('entes inválidos')
        perfil = next((n for n, p in todos.items() if not p['ver_pessoal'] and set(p['tenants']) == set(tenants)), None)
        if perfil is None:
            continue  # Nunca amplia o plano para um perfil mais abrangente.
        acompanhamentos = c['acompanhamentos']
        if not isinstance(acompanhamentos, list) or len(acompanhamentos) > 10:
            raise ValueError('acompanhamentos inválidos')
        mapa = {}
        for a in acompanhamentos:
            cnpj = assinaturas.validar_cnpj(a['cnpj'])
            if type(a['id']) is not int or a['id'] <= 0 or cnpj in mapa:
                raise ValueError('acompanhamento inválido ou duplicado')
            mapa[cnpj] = a['id']
        if not mapa:
            continue
        # Trocar plano ou destinatário começa outra linha de base, sem reaproveitar dados de outro acesso.
        identidade = hashlib.sha256(json.dumps([uid, email, sorted(set(tenants))]).encode()).hexdigest()
        itens.append({'id': identidade, 'usuario_id': uid, 'email': email, 'perfil': perfil, 'cnpjs': list(mapa),
                      'acompanhamentos': mapa, 'origem': 'site', 'email_verificado': True, 'ativa': True, 'avisar_inicial': True})
    return itens


class LojaSite:
    """Só o estado do monitor é local. A lista e o consentimento sempre vêm do site nesta rodada."""
    def __init__(self, arquivo, itens):
        self.arquivo, self.itens = Path(arquivo), itens
        salvo = json.loads(self.arquivo.read_text(encoding='utf-8')) if self.arquivo.exists() else {}
        self.estado = {}
        for a in itens:
            anterior = salvo.get(a['id'], {})
            self.estado[a['id']] = {cnpj: foto for cnpj, foto in anterior.get('fotos', {}).items()
                                   if cnpj in a['acompanhamentos'] and anterior.get('acompanhamentos', {}).get(cnpj) == a['acompanhamentos'][cnpj]}

    def listar(self, so_ativas=False):
        return self.itens

    def ler_estado(self):
        return self.estado

    def gravar_estado(self, estado):
        novo = {a['id']: {'acompanhamentos': a['acompanhamentos'], 'fotos': estado.get(a['id'], {})} for a in self.itens}
        tmp = self.arquivo.with_suffix('.tmp')
        tmp.write_text(json.dumps(novo, ensure_ascii=False), encoding='utf-8')
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.arquivo)
        self.estado = estado

    def marcar_envio(self, id_):
        pass  # O estado só avança no monitor depois da entrega; não há lista local para atualizar.


def rodada(arquivo, api, chave, *, ensaio=False, fabricar_fonte=monitor.FonteGrafo, enviar=envio.enviar_aviso):
    contas = buscar(api, chave)  # Sem resposta atual, não usa uma lista antiga para enviar.
    loja = LojaSite(arquivo, montar(contas, perfis.carregar()))
    relatorio = monitor.verificar(loja, fabricar_fonte, enviar, ensaio=ensaio)
    if not ensaio:
        loja.gravar_estado(loja.ler_estado())  # Remove fotos de acompanhamentos cancelados, inclusive lista vazia.
    return relatorio


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--uma-vez', action='store_true')
    ap.add_argument('--ensaio', action='store_true')
    args = ap.parse_args()
    carregar_env()
    configurar_email()
    chave = os.environ.get('WORKER_KEY', '')
    if len(chave) < 24:
        ap.error('defina WORKER_KEY (a mesma do site) no .env')
    if not args.ensaio and envio.modo() != 'smtp':
        ap.error('a ponte exige SMTP; use --ensaio para testar sem enviar')
    api = os.environ.get('API_BASE', f"https://{os.environ.get('SITE', 'fornexia.figueiredo.dev')}").rstrip('/') + '/api'
    pasta = Path(os.environ.get('ALERTAS_SITE_PASTA') or RAIZ / 'dados/alertas-site')
    pasta.mkdir(parents=True, exist_ok=True, mode=0o700)
    # flock é liberado até numa queda do processo; dois serviços não enviam a mesma rodada.
    import fcntl
    with (pasta / 'monitor.lock').open('a') as trava:
        try:
            fcntl.flock(trava, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('monitor do site já está em execução', file=sys.stderr)
            return 1
        while True:
            falha = False
            try:
                resultado = rodada(pasta / 'estado.json', api, chave, ensaio=args.ensaio)
                falha = any(r.get('erro') or r.get('erro_de_envio') or r.get('avisos') for r in resultado)
                print(time.strftime('%H:%M:%S'), f"alertas: {len(resultado)} conta(s), "
                      f"{sum(bool(r.get('enviado_para')) for r in resultado)} envio(s), falhas: {falha}", flush=True)
            except Exception as erro:
                # Não expõe destinatários, URLs de requisição nem credenciais nos logs.
                print(time.strftime('%H:%M:%S'), 'alertas: rodada falhou:', type(erro).__name__, flush=True)
                falha = True
            if args.uma_vez or args.ensaio:
                return int(falha)
            time.sleep(60)


if __name__ == '__main__':
    sys.exit(main())
