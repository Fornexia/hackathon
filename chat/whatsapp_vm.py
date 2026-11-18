"""Executa uma pergunta do WhatsApp na VM via SSH, sem enviar mensagens."""

import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys

import agente

COMANDO_REMOTO = "$HOME/.local/bin/fornexia-whatsapp-claude"
LIMITE_VM_S = 40


class FalhaVM(ValueError):
    pass


def perguntar_vm(destino, texto, tenants, contexto, request_id):
    chave = os.environ.get("AGENTE_WHATSAPP_VM_CHAVE")
    comando = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4",
               "-o", "StrictHostKeyChecking=yes", "-o", "ClearAllForwardings=yes"]
    if chave:
        comando += ["-o", "IdentitiesOnly=yes", "-i", str(Path(chave).expanduser())]
    comando += ["--", destino, COMANDO_REMOTO]
    pedido = dict(texto=texto, tenants=tenants, historico=contexto, request_id=request_id)
    try:
        processo = subprocess.run(comando, input=json.dumps(pedido), text=True, encoding="utf-8",
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   timeout=LIMITE_VM_S)
    except subprocess.TimeoutExpired as erro:
        raise FalhaVM("Claude da VM excedeu o prazo") from erro
    except OSError as erro:
        raise FalhaVM("Conexão com a VM indisponível") from erro
    except UnicodeError as erro:
        raise FalhaVM("Resposta inválida do agente da VM") from erro
    if processo.returncode:
        raise FalhaVM("Conexão com a VM ou agente remoto indisponível")
    try:
        dados = json.loads(processo.stdout)
        if not isinstance(dados, dict):
            raise ValueError
        if dados.get("ok") is False:
            raise FalhaVM("Claude da VM não concluiu a resposta")
        campos_validos = (dados.get("ok") is True
                          and isinstance(dados.get("resposta"), str) and dados["resposta"].strip()
                          and isinstance(dados.get("modelo"), str) and dados["modelo"]
                          and isinstance(dados.get("uso"), dict)
                          and all(isinstance(dados.get(k), list) for k in ("fontes", "consultas", "evidencias"))
                          and all(isinstance(f, dict) for f in dados["fontes"])
                          and all(isinstance(v, str) for k in ("consultas", "evidencias") for v in dados[k]))
        if not campos_validos:
            raise ValueError
    except FalhaVM:
        raise
    except ValueError as erro:
        raise FalhaVM("Resposta inválida do agente da VM") from erro
    return dados


def atender(pedido):
    leitor = agente.Leitor()
    fontes = []
    for tipo, dados in agente.perguntar(
        pedido["texto"], pedido["tenants"], pedido["historico"], leitor,
        permitir_fallback=False, request_id=pedido.get("request_id"), provedor="claude",
    ):
        if tipo == "fonte":
            fontes.append(dados)
        elif tipo == "fim" and leitor.resposta.strip():
            return dict(ok=True, resposta=leitor.resposta, modelo=leitor.modelo, fontes=fontes,
                        consultas=leitor.consultas, evidencias=leitor.evidencias, uso=leitor.uso)
    return {"ok": False}


def main():
    try:
        with contextlib.redirect_stdout(sys.stderr):
            pedido = json.loads(sys.stdin.buffer.read(64_001))
            resposta = atender(pedido)
    except (KeyError, TypeError, ValueError, OSError):
        resposta = {"ok": False}
    print(json.dumps(resposta, ensure_ascii=True))


if __name__ == "__main__":
    main()
