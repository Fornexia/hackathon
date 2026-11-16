"""Assinaturas de alerta: quem quer ser avisado, com qual perfil e sobre quais CNPJs.

Fica em arquivos JSON na pasta de alertas (`ALERTAS_PASTA`, padrão `dados/alertas/`, que o git ignora): é demonstração, para o site
trocar por uma tabela depois. Tem e-mail de cliente, então é dado pessoal (LGPD): sem consentimento e sem descadastro não se manda nada.

- O perfil é o do plano do cliente e define o que o aviso pode conter; perfil que enxerga dado pessoal é recusado.
- Só CNPJ (14 dígitos). CPF não é aceito.
- Cada assinatura tem um código de cancelamento aleatório, que vai em todo e-mail.
- **E-mail verificado:** só recebe aviso quem confirmou que o e-mail é dele (entrou com o Google, que garante `email_verified`, ou confirmou um código
  enviado ao endereço). Assinatura sem verificação fica guardada, mas o monitor não lê nem envia nada para ela. `origem` diz de onde veio
  (`cli`, `site` ou `google`) e `usuario_id` liga ao usuário do site, quando houver.
"""

import json
import os
import re
import secrets
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "consulta"))
import perfis  # noqa: E402

MAX_CNPJS = 20
ORIGENS = ("cli", "site", "google")
MAX_ASSINATURAS = 500
EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9\-]{1,63}(\.[A-Za-z0-9\-]{1,63})*\.[A-Za-z]{2,}$")


class ErroDeAssinatura(ValueError):
    pass


def pasta() -> Path:
    p = Path(os.environ.get("ALERTAS_PASTA") or RAIZ / "dados" / "alertas")
    p.mkdir(parents=True, exist_ok=True)
    return p


def so_digitos(cnpj: str) -> str:
    return re.sub(r"\D", "", str(cnpj or ""))


def validar_cnpj(cnpj: str) -> str:
    """14 dígitos. Não confere o dígito verificador: os CNPJs fictícios da base de exemplo não o têm. CPF (11) é recusado."""
    d = so_digitos(cnpj)
    if len(d) == 11:
        raise ErroDeAssinatura("CPF não é aceito: só CNPJ")
    if len(d) != 14:
        raise ErroDeAssinatura(f"CNPJ inválido: '{cnpj}' (precisa de 14 dígitos)")
    return d


def validar_email(email: str) -> str:
    e = str(email or "").strip().lower()
    if len(e) > 254 or not EMAIL.match(e):
        raise ErroDeAssinatura("e-mail inválido")
    return e


def _agora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _gravar(arquivo: Path, dados) -> None:
    """Grava inteiro ou não grava: escreve num arquivo ao lado e troca. Uma falha no meio nunca deixa o arquivo pela metade."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=arquivo.parent, suffix=".tmp", delete=False) as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
        temporario = f.name
    os.replace(temporario, arquivo)


class Assinaturas:
    def __init__(self, pasta_: Path | None = None):
        self.pasta = Path(pasta_) if pasta_ else pasta()
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.arquivo = self.pasta / "assinaturas.json"
        self.arquivo_estado = self.pasta / "estado.json"

    # ---------- assinaturas ----------
    def listar(self, so_ativas: bool = False) -> list[dict]:
        if not self.arquivo.exists():
            return []
        itens = json.loads(self.arquivo.read_text(encoding="utf-8"))
        return [a for a in itens if a.get("ativa")] if so_ativas else itens

    def criar(self, email: str, perfil: str, cnpjs: list[str], verificado: bool = False, origem: str = "cli", usuario_id: int | None = None) -> dict:
        email = validar_email(email)
        if origem not in ORIGENS:
            raise ErroDeAssinatura(f"origem desconhecida: '{origem}'")
        if origem == "google" and not verificado:
            raise ErroDeAssinatura("origem google exige e-mail verificado (o Google só entrega e-mail verificado)")
        todos = perfis.carregar()
        if perfil not in todos:
            raise ErroDeAssinatura(f"perfil desconhecido: '{perfil}'. Disponíveis: {', '.join(todos)}")
        if todos[perfil]["ver_pessoal"]:
            raise ErroDeAssinatura("perfil com dado pessoal não recebe alertas")
        novos = list(dict.fromkeys(validar_cnpj(c) for c in cnpjs))
        if not novos:
            raise ErroDeAssinatura("informe ao menos um CNPJ")
        itens = self.listar()
        # a mesma pessoa e o mesmo perfil não geram duas assinaturas (dois e-mails iguais por dia): os CNPJs somam
        for a in itens:
            if a["ativa"] and a["email"] == email and a["perfil"] == perfil:
                juntos = list(dict.fromkeys(a["cnpjs"] + novos))
                if len(juntos) > MAX_CNPJS:
                    raise ErroDeAssinatura(f"no máximo {MAX_CNPJS} CNPJs por assinatura")
                a["cnpjs"] = juntos
                if verificado and not a.get("email_verificado"):
                    a["email_verificado"], a["consentimento_em"] = True, _agora()
                _gravar(self.arquivo, itens)
                return a
        if len(novos) > MAX_CNPJS:
            raise ErroDeAssinatura(f"no máximo {MAX_CNPJS} CNPJs por assinatura")
        if len([a for a in itens if a["ativa"]]) >= MAX_ASSINATURAS:
            raise ErroDeAssinatura("limite de assinaturas atingido")
        nova = {"id": secrets.token_hex(4), "email": email, "perfil": perfil, "cnpjs": novos, "token": secrets.token_hex(16),
                "ativa": True, "criada_em": _agora(), "ultimo_envio": None,
                "origem": origem, "usuario_id": usuario_id, "email_verificado": bool(verificado), "consentimento_em": _agora() if verificado else None}
        itens.append(nova)
        _gravar(self.arquivo, itens)
        return nova

    def cancelar(self, codigo_ou_email: str) -> int:
        """Cancela pelo código do e-mail (ou por todos os avisos do endereço). Devolve quantas assinaturas foram canceladas."""
        chave = str(codigo_ou_email or "").strip()
        if not chave:
            return 0
        itens, feitos = self.listar(), 0
        for a in itens:
            if a["ativa"] and (secrets.compare_digest(a["token"].encode(), chave.encode()) or a["email"] == chave.lower()):
                a["ativa"] = False
                a["cancelada_em"] = _agora()
                feitos += 1
        if feitos:
            _gravar(self.arquivo, itens)
            estado = self.ler_estado()
            for a in itens:
                if not a["ativa"]:
                    estado.pop(a["id"], None)       # não guarda a foto de quem saiu
            self.gravar_estado(estado)
        return feitos

    def marcar_verificado(self, id_ou_email: str) -> int:
        """Marca o e-mail como confirmado (chamado depois que o código foi conferido, ou na conta Google). Devolve quantas assinaturas mudaram."""
        chave = str(id_ou_email or "").strip().lower()
        itens, feitos = self.listar(), 0
        for a in itens:
            if a["ativa"] and not a.get("email_verificado") and chave in (a["id"], a["email"]):
                a["email_verificado"], a["consentimento_em"] = True, _agora()
                feitos += 1
        if feitos:
            _gravar(self.arquivo, itens)
        return feitos

    def marcar_envio(self, id_: str) -> None:
        itens = self.listar()
        for a in itens:
            if a["id"] == id_:
                a["ultimo_envio"] = _agora()
        _gravar(self.arquivo, itens)

    # ---------- estado (a foto de cada CNPJ na última verificação) ----------
    def ler_estado(self) -> dict:
        return json.loads(self.arquivo_estado.read_text(encoding="utf-8")) if self.arquivo_estado.exists() else {}

    def gravar_estado(self, estado: dict) -> None:
        _gravar(self.arquivo_estado, estado)
