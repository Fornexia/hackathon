"""Monta e envia o e-mail de aviso.

Dois jeitos de entregar, escolhidos por variável de ambiente (nunca no código):
- `arquivo` (padrão quando não há servidor configurado): grava o .eml em `<pasta de alertas>/saida/`. Serve para ensaio e demonstração.
- `smtp`: usa `ALERTAS_SMTP_HOST` (e `ALERTAS_SMTP_PORTA`, `ALERTAS_SMTP_USUARIO`, `ALERTAS_SMTP_SENHA`, `ALERTAS_SMTP_SEGURANCA` = starttls|ssl|nenhuma)
  com remetente em `ALERTAS_DE`. A senha só vive no ambiente (ou no .env, que o git ignora).

O texto vindo dos portais entra no e-mail só depois de limpo (sem quebra de linha, sem caractere de controle, com tamanho máximo) e, no HTML, escapado.
Nada vindo de fora vai para o assunto nem para os cabeçalhos.
"""

import html
import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

import assinaturas

AVISO = ("Isto é o que a fonte registra, na data indicada. Uma ocorrência num cadastro não prova irregularidade, e a ausência dela não prova "
         "que não existe: a base cobre só as fontes listadas no sistema.")


def modo() -> str:
    escolhido = (os.environ.get("ALERTAS_ENVIO") or "").strip().lower()
    if escolhido in ("arquivo", "smtp"):
        return escolhido
    if escolhido:        # erro de digitação não pode virar "arquivo" em silêncio: o aviso seria dado como enviado e ninguém receberia
        raise RuntimeError(f"ALERTAS_ENVIO inválido: '{escolhido[:20]}' (use arquivo ou smtp)")
    return "smtp" if os.environ.get("ALERTAS_SMTP_HOST") else "arquivo"


def _cnpj_formatado(c: str) -> str:
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else c


def _agrupar(eventos: list[dict]) -> dict[str, list[dict]]:
    grupos: dict[str, list[dict]] = {}
    for e in eventos:
        grupos.setdefault(e["cnpj"], []).append(e)
    return grupos


def assunto(n: int) -> str:
    return "FornexIA: 1 novidade nos fornecedores que você acompanha" if n == 1 else f"FornexIA: {n} novidades nos fornecedores que você acompanha"


def montar(assinatura: dict, eventos: list[dict], agora: datetime, de: str | None = None) -> EmailMessage:
    remetente = de or os.environ.get("ALERTAS_DE") or "alertas@fornexia.invalid"
    msg = EmailMessage()
    msg["From"] = remetente
    msg["To"] = assinaturas.validar_email(assinatura["email"])     # nunca um endereço com quebra de linha (injeção de cabeçalho)
    msg["Subject"] = assunto(len(eventos))
    msg["Date"] = formatdate(agora.timestamp(), localtime=True)
    msg["Message-ID"] = make_msgid(domain="fornexia.local")
    msg["Auto-Submitted"] = "auto-generated"
    inicial = any(e.get("tipo") == "retrato_inicial" for e in eventos)
    if inicial:
        msg.replace_header("Subject", "FornexIA: acompanhamento iniciado e retrato da base")

    linhas = [f"Houve {len(eventos)} mudança(s) nos fornecedores que você acompanha (verificado em {agora:%d/%m/%Y %H:%M}).", ""]
    partes = ["<p>Houve <strong>%d</strong> mudança(s) nos fornecedores que você acompanha (verificado em %s).</p>" % (len(eventos), agora.strftime("%d/%m/%Y %H:%M"))]
    if inicial:
        intro = ("O acompanhamento começou. Abaixo está o retrato do que a base registra hoje, dentro do seu plano. "
                 "Os itens marcados como retrato inicial já existiam na base; não são novidades. Os demais itens indicam mudanças desde a última verificação. Depois, avisaremos quando a base mudar.")
        linhas = [intro, ""]
        partes = [f"<p>{intro}</p>"]
    for cnpj, lista in _agrupar(eventos).items():
        nome = lista[0].get("nome") or "fornecedor"
        cab = f"{nome}, CNPJ {_cnpj_formatado(cnpj)}"
        linhas += [cab, "-" * min(len(cab), 70)]
        partes.append(f"<h3>{html.escape(cab)}</h3><ul>")
        for e in lista:
            prova = []
            if e.get("fonte_url"):
                prova.append(f"Fonte: {e['fonte_url']}")
            if e.get("capturado_em"):
                prova.append(f"capturada em {e['capturado_em']}")
            if e.get("evidencia"):
                prova.append(f"prova: evidência {e['evidencia']}")
            titulo = ("Retrato inicial: " if e.get("tipo") == "retrato_inicial" else "") + e["titulo"]
            linhas += [f"* {titulo}", f"  {e['detalhe']}"] + ([f"  {'; '.join(prova)}"] if prova else []) + [""]
            partes.append(f"<li><strong>{html.escape(titulo)}</strong><br>{html.escape(e['detalhe'])}"
                          + (f"<br><small>{html.escape('; '.join(prova))}</small>" if prova else "") + "</li>")
        partes.append("</ul>")
    if assinatura.get("origem") == "site":
        conta = (os.environ.get("APP_URL") or "https://fornexia.figueiredo.dev").rstrip("/") + "/conta.html"
        rodape = "Você recebe este e-mail porque pediu para acompanhar estes CNPJs. Para parar de receber, abra Minha conta e use Parar de acompanhar."
        linhas += [AVISO, "", rodape, conta]
        partes.append(f'<p><small>{html.escape(AVISO)}</small></p><p><small>{rodape} '
                      f'<a href="{html.escape(conta, quote=True)}">Minha conta</a>.</small></p>')
    else:
        cancelar = f"python alertas/cli.py cancelar {assinatura['token']}"
        linhas += [AVISO, "", "Você recebe este e-mail porque pediu para acompanhar estes CNPJs. Para parar de receber, peça o cancelamento",
                   f"com o código: {assinatura['token']}  (ou rode: {cancelar})."]
        partes.append(f"<p><small>{html.escape(AVISO)}</small></p><p><small>Você recebe este e-mail porque pediu para acompanhar estes CNPJs. "
                      f"Para parar de receber, peça o cancelamento com o código <code>{html.escape(assinatura['token'])}</code>.</small></p>")
    msg.set_content("\n".join(linhas))
    msg.add_alternative("<html><body style=\"font-family:Arial,sans-serif\">" + "".join(partes) + "</body></html>", subtype="html")
    return msg


def enviar(msg: EmailMessage, pasta: Path | None = None) -> str:
    """Entrega a mensagem. Devolve onde ela foi parar (caminho do .eml ou 'smtp:destino'). Falha vira exceção: quem chama não grava a foto."""
    if modo() == "arquivo":
        saida = (pasta or assinaturas.pasta()) / "saida"
        saida.mkdir(parents=True, exist_ok=True)
        id_ = make_msgid(domain="x").strip("<>").split("@")[0].replace(".", "-")
        caminho = saida / f"{datetime.now():%Y%m%d-%H%M%S}-{id_[-8:]}.eml"
        caminho.write_bytes(bytes(msg))
        return str(caminho)
    host = os.environ.get("ALERTAS_SMTP_HOST", "")
    if not host or not os.environ.get("ALERTAS_DE"):
        raise RuntimeError("SMTP sem ALERTAS_SMTP_HOST e ALERTAS_DE")
    porta = int(os.environ.get("ALERTAS_SMTP_PORTA") or 587)
    seguranca = (os.environ.get("ALERTAS_SMTP_SEGURANCA") or "starttls").lower()
    if seguranca not in ("starttls", "ssl", "nenhuma"):
        raise RuntimeError("ALERTAS_SMTP_SEGURANCA inválida")
    contexto = ssl.create_default_context()
    if seguranca == "ssl":
        servidor = smtplib.SMTP_SSL(host, porta, timeout=30, context=contexto)
    else:
        servidor = smtplib.SMTP(host, porta, timeout=30)
    with servidor:
        servidor.ehlo()
        if seguranca == "starttls":
            servidor.starttls(context=contexto)      # sem TLS a senha e o aviso iriam em texto aberto
            servidor.ehlo()
        usuario = os.environ.get("ALERTAS_SMTP_USUARIO")
        if usuario:
            servidor.login(usuario, os.environ.get("ALERTAS_SMTP_SENHA", ""))
        servidor.send_message(msg)
    return f"smtp:{msg['To']}"


def enviar_aviso(assinatura: dict, eventos: list[dict], agora: datetime) -> str:
    return enviar(montar(assinatura, eventos, agora))


def mensagem_de_teste(destino: str, agora: datetime) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = os.environ.get("ALERTAS_DE") or "alertas@fornexia.invalid"
    msg["To"] = assinaturas.validar_email(destino)
    msg["Subject"] = "FornexIA: teste do envio de alertas"
    msg["Date"] = formatdate(agora.timestamp(), localtime=True)
    msg.set_content(f"Este é um e-mail de teste do envio de alertas do FornexIA ({agora:%d/%m/%Y %H:%M}). Nenhuma ação é necessária.")
    return msg
