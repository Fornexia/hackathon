"""Monitor: compara o que a base sabe HOJE de cada CNPJ acompanhado com a foto da última verificação e gera os avisos.

Roda depois da coleta (cron diário: recaptura, extrai, carrega no Neo4j, `python alertas/cli.py verificar`). Não consulta o portal:
lê o grafo, pelas mesmas consultas do agente e COM O PERFIL DA ASSINATURA. Um cliente nunca é avisado de algo que o plano dele não enxerga.

Regras que importam:
- A primeira verificação de um CNPJ só tira a foto ("linha de base"): não avisa nada, senão tudo o que já existia viraria novidade.
- A foto só é gravada depois que o e-mail saiu. Se o envio falha, a próxima rodada tenta de novo, sem perder aviso.
- CNPJ que tinha dados e agora não tem nenhum (recarga ou queda da base) não vira "tudo foi removido": fica sem aviso e sem trocar a foto.
- O aviso diz o que a fonte registra, nunca que há irregularidade.
- **Só recebe quem verificou o e-mail.** Assinatura sem `email_verificado` é pulada por inteiro (sem consulta, sem foto, sem envio): quando o cliente
  confirmar o e-mail, a primeira rodada vira linha de base, e ele não recebe de uma vez tudo o que já existia.
"""

import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "consulta"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import assinaturas  # noqa: E402

LIMITE_EVENTOS_POR_EMAIL = 30
CAMPOS_SANCAO = ("cadastro", "tipo", "situacao", "publicada_em", "inicio_suspensao", "fim_suspensao", "orgao", "abrangencia", "valor_multa", "ente", "evidencia")
CAMPOS_CONTRATO = ("numero", "objeto", "valor_contratado", "valor_final", "inicio", "fim", "tem_aditivo", "situacao", "fonte", "ente", "evidencia")
CAMPOS_CADASTRO = ("razao_social", "situacao", "situacao_desde", "motivo_situacao", "ente", "evidencia")


def _limpo(valor, tamanho: int = 160) -> str:
    """Texto vindo do portal é dado: sem quebra de linha nem caractere de controle, e com tamanho máximo."""
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(valor if valor is not None else "")).strip()[:tamanho]


def _linha(origem: dict, campos: tuple[str, ...]) -> dict:
    return {c: origem[c] for c in campos if origem.get(c) is not None}


def _chave_sancao(s: dict) -> str:
    base = "|".join(str(s.get(c, "")) for c in ("cadastro", "tipo", "publicada_em", "inicio_suspensao", "orgao", "ente"))
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def _chave_contrato(c: dict) -> str:
    """Identifica o contrato sem depender da ordem da consulta. O número sozinho não basta: unidades diferentes repetem número, e há contrato sem número."""
    partes = [c.get("ente"), c.get("numero"), c.get("unidade"), c.get("inicio")]
    if not c.get("numero"):
        partes.append(c.get("objeto"))
    return "|".join("" if p is None else str(p) for p in partes)


def _indexar(itens: list[dict], chave, campos: tuple[str, ...]) -> dict:
    """Um dicionário por chave. Itens de chave igual não se sobrescrevem: o segundo vira `chave#2`, e assim por diante."""
    saida, vistos = {}, {}
    for item in itens:
        k = chave(item)
        vistos[k] = vistos.get(k, 0) + 1
        saida[k if vistos[k] == 1 else f"{k}#{vistos[k]}"] = _linha(item, campos)
    return saida


class FonteGrafo:
    """Lê o grafo pelas consultas do agente, com o perfil da assinatura. É o único lugar que toca o Neo4j."""

    def __init__(self, perfil: str):
        import perfis
        import mcp_transparencia as nucleo
        self.nucleo = nucleo
        p = perfis.carregar()[perfil]
        self.perfil, self.tenants = perfil, list(p["tenants"])
        self.limite = nucleo.LIMITE_LINHAS      # as consultas devolvem no máximo isto: com tantos itens a foto pode ser um recorte

    def _no_perfil(self, funcao, *args):
        with self.nucleo.com_perfil(self.perfil, self.tenants, False, "alertas"):
            return funcao(*args)

    def ler(self, cnpj: str) -> dict | None:
        achados = self._no_perfil(self.nucleo.buscar_fornecedor, cnpj)
        fornecedor = next((f for f in achados if f.get("cnpj") == cnpj), None)
        if fornecedor is None:
            return None
        id_ = fornecedor["id"]
        return {"nome": fornecedor.get("nome"),
                "sancoes": self._no_perfil(self.nucleo.sancoes_do_fornecedor, id_),
                "contratos": self._no_perfil(self.nucleo.contratos_do_fornecedor, id_),
                "cadastro": self._no_perfil(self.nucleo.cadastro_do_fornecedor, id_)}

    def evidencia(self, id_: str) -> dict:
        return self._no_perfil(self.nucleo.conferir_evidencia, id_)


def fotografar(fonte, cnpj: str) -> dict | None:
    """A foto de um CNPJ: só o que muda o aviso. None = o CNPJ não aparece na base deste perfil."""
    cru = fonte.ler(cnpj)
    if cru is None:
        return None
    sancoes, contratos = cru.get("sancoes", []), cru.get("contratos", [])
    foto = {
        "nome": cru.get("nome"),
        "sancoes": _indexar(sancoes, _chave_sancao, CAMPOS_SANCAO),
        "contratos": _indexar(contratos, _chave_contrato, CAMPOS_CONTRATO),
        "cadastro": _linha(cru["cadastro"][0], CAMPOS_CADASTRO) if cru.get("cadastro") else None,
    }
    limite = getattr(fonte, "limite", None)
    cheias = [nome for nome, lista in (("sancoes", sancoes), ("contratos", contratos)) if limite and len(lista) >= limite]
    if cheias:
        foto["truncado"] = cheias
    return foto


def _fundir_truncado(antes: dict, foto: dict) -> None:
    """Quando a consulta veio cheia, a foto é só uma janela: o que saiu dela não foi removido na fonte e o que voltou não é novo.
    Então o que já se conhecia fica na foto. O custo: remoção e mudança de itens fora da janela deixam de ser vistas."""
    for nome in foto.get("truncado", []):
        for chave, item in antes.get(nome, {}).items():
            foto[nome].setdefault(chave, item)


def _vazia(foto: dict | None) -> bool:
    return foto is None or not (foto["sancoes"] or foto["contratos"] or foto["cadastro"])


def _evento(tipo: str, cnpj: str, nome, titulo: str, detalhe: str, item: dict) -> dict:
    return {"tipo": tipo, "cnpj": cnpj, "nome": _limpo(nome, 120) or None, "titulo": titulo, "detalhe": _limpo(detalhe, 300),
            "ente": _limpo(item.get("ente"), 40), "evidencia": _limpo(item.get("evidencia"), 80) or None}


def _dinheiro(v) -> str:
    try:
        return "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return _limpo(v, 30)


def comparar(cnpj: str, antes: dict, agora: dict) -> list[dict]:
    """Os avisos de um CNPJ. `antes` e `agora` são fotos (de `fotografar`)."""
    nome = agora.get("nome") or antes.get("nome")
    eventos = []
    for k, s in agora["sancoes"].items():
        cad = _limpo(s.get("cadastro", "cadastro de sanções"), 20).upper()
        base = f"{_limpo(s.get('tipo'), 80) or 'sanção'}, órgão {_limpo(s.get('orgao'), 80) or 'não informado'}"
        if k not in antes["sancoes"]:
            eventos.append(_evento("sancao_nova", cnpj, nome, f"Nova ocorrência no {cad}", f"{base}. Situação na fonte: {_limpo(s.get('situacao'), 40) or 'não informada'}.", s))
        else:
            antiga = antes["sancoes"][k]
            if any(antiga.get(c) != s.get(c) for c in ("situacao", "fim_suspensao", "valor_multa")):
                eventos.append(_evento("sancao_alterada", cnpj, nome, f"Ocorrência do {cad} foi atualizada",
                                       f"{base}. Situação: {_limpo(antiga.get('situacao'), 40) or '-'} → {_limpo(s.get('situacao'), 40) or '-'}; "
                                       f"fim: {_limpo(antiga.get('fim_suspensao'), 12) or '-'} → {_limpo(s.get('fim_suspensao'), 12) or '-'}.", s))
    for k, s in antes["sancoes"].items():
        if k not in agora["sancoes"]:
            cad = _limpo(s.get("cadastro", "cadastro de sanções"), 20).upper()
            eventos.append(_evento("sancao_removida", cnpj, nome, f"Ocorrência deixou de constar no {cad}",
                                   f"{_limpo(s.get('tipo'), 80) or 'sanção'}, órgão {_limpo(s.get('orgao'), 80) or 'não informado'}. A fonte não a lista mais.", s))
    for k, c in agora["contratos"].items():
        obj = _limpo(c.get("objeto"), 90) or "sem objeto informado"
        if k not in antes["contratos"]:
            eventos.append(_evento("contrato_novo", cnpj, nome, f"Novo contrato {_limpo(c.get('numero'), 30)}",
                                   f"{obj}. Valor contratado: {_dinheiro(c.get('valor_contratado'))}. Fonte: {_limpo(c.get('fonte'), 40) or 'portal do ente'}.", c))
        else:
            antigo = antes["contratos"][k]
            mudou = [f"{rotulo}: {_limpo(antigo.get(campo), 30) or '-'} → {_limpo(c.get(campo), 30) or '-'}"
                     for campo, rotulo in (("valor_final", "valor final"), ("fim", "fim"), ("situacao", "situação"), ("tem_aditivo", "aditivo"))
                     if antigo.get(campo) != c.get(campo)]
            if antigo.get("valor_contratado") != c.get("valor_contratado"):
                mudou.insert(0, f"valor contratado: {_dinheiro(antigo.get('valor_contratado'))} → {_dinheiro(c.get('valor_contratado'))}")
            if mudou:
                eventos.append(_evento("contrato_alterado", cnpj, nome, f"Contrato {_limpo(c.get('numero'), 30)} foi atualizado", f"{obj}. " + "; ".join(mudou) + ".", c))
    a, b = antes.get("cadastro"), agora.get("cadastro")
    if a and b and any(a.get(c) != b.get(c) for c in ("situacao", "situacao_desde", "motivo_situacao")):
        eventos.append(_evento("cadastro_alterado", cnpj, nome, "Situação cadastral na Receita mudou",
                               f"{_limpo(a.get('situacao'), 40) or '-'} → {_limpo(b.get('situacao'), 40) or '-'}"
                               + (f" (motivo: {_limpo(b.get('motivo_situacao'), 80)})" if b.get("motivo_situacao") else "") + ".", b))
    return eventos


def _com_prova(fonte, evento: dict) -> dict:
    """Junta ao aviso o endereço da fonte e a data da captura (a prova é aberta pelo mesmo caminho do chat). Sem prova, o aviso sai assim mesmo."""
    if evento.get("evidencia"):
        try:
            e = fonte.evidencia(evento["evidencia"])
            if e and not e.get("erro"):
                evento["fonte_url"] = _limpo(e.get("url"), 300) or None
                evento["capturado_em"] = _limpo(e.get("capturado_em"), 40) or None
        except Exception:      # a prova é um acréscimo: não derruba o aviso
            pass
    return evento


def verificar(loja, fabricar_fonte, enviar, ensaio: bool = False, agora: datetime | None = None) -> list[dict]:
    """Uma rodada. `fabricar_fonte(perfil)` dá a fonte do perfil; `enviar(assinatura, eventos, agora)` devolve onde o aviso foi parar.
    Em ensaio não envia nem grava nada: só mostra o que seria enviado."""
    agora = agora or datetime.now().astimezone()
    estado = loja.ler_estado()
    relatorio = []
    for a in loja.listar(so_ativas=True):
        if not a.get("email_verificado"):
            relatorio.append({"id": a["id"], "eventos": 0, "linha_de_base": [], "avisos": ["e-mail ainda não verificado: nada é lido nem enviado"],
                              "enviado_para": None, "lista": []})
            continue
        antes_tudo = estado.get(a["id"], {})
        depois_tudo = dict(antes_tudo)
        eventos, base, avisos = [], [], []
        try:
            fonte = fabricar_fonte(a["perfil"])
        except Exception as erro:
            relatorio.append({"id": a["id"], "erro": f"perfil indisponível: {_limpo(erro)}"})
            continue
        for cnpj in a["cnpjs"]:
            try:
                foto = fotografar(fonte, cnpj)
            except Exception as erro:       # base fora do ar: não troca a foto e tenta de novo na próxima rodada
                avisos.append(f"{cnpj}: consulta falhou ({_limpo(erro, 80)})")
                continue
            if foto and foto.get("truncado"):
                avisos.append(f"{cnpj}: a consulta veio cheia ({', '.join(foto['truncado'])}): comparação parcial, o que sair da janela não gera aviso")
            antes = antes_tudo.get(cnpj)
            if antes is None:
                base.append(cnpj)
                depois_tudo[cnpj] = foto if foto is not None else {"nome": None, "sancoes": {}, "contratos": {}, "cadastro": None}
                continue
            if _vazia(foto) and not _vazia(antes):
                avisos.append(f"{cnpj}: tinha dados e agora não tem nenhum (recarga ou queda da base?). Sem aviso; a foto anterior foi mantida")
                continue
            if foto:
                _fundir_truncado(antes, foto)
            eventos += comparar(cnpj, antes, foto or {"nome": antes.get("nome"), "sancoes": {}, "contratos": {}, "cadastro": None})
            depois_tudo[cnpj] = foto if foto is not None else antes
        eventos = [_com_prova(fonte, e) for e in eventos[:LIMITE_EVENTOS_POR_EMAIL]] + eventos[LIMITE_EVENTOS_POR_EMAIL:]
        item = {"id": a["id"], "eventos": len(eventos), "linha_de_base": base, "avisos": avisos, "enviado_para": None, "lista": eventos}
        if eventos and not ensaio:
            try:
                item["enviado_para"] = enviar(a, eventos, agora)
            except Exception as erro:
                item["erro_de_envio"] = _limpo(erro, 200)
                relatorio.append(item)
                continue          # a foto não muda: o aviso sai na próxima rodada
            try:
                loja.marcar_envio(a["id"])
            except Exception as erro:      # o e-mail JÁ saiu: a foto avança mesmo assim, senão o mesmo aviso se repetiria a cada rodada
                avisos.append(f"aviso enviado, mas o horário do envio não foi gravado ({_limpo(erro, 80)})")
        if not ensaio:
            estado[a["id"]] = depois_tudo
            loja.gravar_estado(estado)
        relatorio.append(item)
    return relatorio
