"""Chaves da API: cada chave pertence a um cliente e a UM perfil de acesso.

O perfil (quais entes e que tipo de dado) vem desta tabela, guardada no servidor. Nunca vem de um campo da requisição,
nem de uma tool, nem do texto de uma pergunta: o que o chamador não pode informar, um ataque de prompt não muda.
É a mesma regra do resto do projeto (consulta/perfis.py).

A tabela guarda só o SHA-256 de cada chave. A chave de verdade aparece uma única vez, quando é gerada:

    python api/gerar_chave.py demo-cliente estado          # perfis: python consulta/perfis.py

Formato de api/chaves.json (fora do git):
    { "<sha256 da chave>": { "cliente": "demo-cliente", "perfil": "estado", "limite_por_minuto": 60,
                              "perguntas_por_dia": 30, "ativo": true } }

Perfil com dado pessoal (`ver_pessoal: true`) é RECUSADO aqui: a API é para terceiros, e dado pessoal não sai dela.
Chave de perfil desconhecido ou entrada malformada também é recusada, com erro claro; nada cai num perfil padrão.
"""

import hashlib
import json
import os
import secrets
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "consulta"))
import perfis  # noqa: E402

ARQUIVO_PADRAO = RAIZ / "api" / "chaves.json"
PREFIXO = "fx_"
LIMITE_MINUTO_PADRAO = 60
PERGUNTAS_DIA_PADRAO = 30


@dataclass(frozen=True)
class Cliente:
    id: str
    perfil: str
    nome_do_perfil: str
    tenants: tuple[str, ...]
    limite_por_minuto: int
    perguntas_por_dia: int


def hash_da_chave(chave: str) -> str:
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()


def _cliente(entrada: dict, todos: dict) -> Cliente:
    perfil = entrada.get("perfil")
    if perfil not in todos:
        raise ValueError(f"perfil desconhecido: {perfil!r}. Disponíveis: {', '.join(todos)}")
    if todos[perfil]["ver_pessoal"]:
        raise ValueError(f"perfil '{perfil}' vê dado pessoal: a API não entrega dado pessoal a terceiros")
    nome = entrada.get("cliente")
    if not isinstance(nome, str) or not nome.strip() or len(nome) > 60:
        raise ValueError("'cliente' precisa ser um texto de 1 a 60 caracteres")
    limite = entrada.get("limite_por_minuto", LIMITE_MINUTO_PADRAO)
    dia = entrada.get("perguntas_por_dia", PERGUNTAS_DIA_PADRAO)
    if not (isinstance(limite, int) and 1 <= limite <= 1000) or not (isinstance(dia, int) and 0 <= dia <= 10000):
        raise ValueError("limites fora da faixa (por minuto: 1 a 1000; perguntas por dia: 0 a 10000)")
    return Cliente(nome.strip(), perfil, todos[perfil]["nome"], tuple(todos[perfil]["tenants"]), limite, dia)


class Chaves:
    """Lê o arquivo de chaves e o relê quando ele muda: chave nova ou revogada vale sem reiniciar a API."""

    def __init__(self, arquivo: Path | str | None = None):
        self.arquivo = Path(arquivo or os.environ.get("API_CHAVES") or ARQUIVO_PADRAO)
        self._trava = threading.Lock()
        self._marca: tuple | None = None
        self._tabela: dict[str, Cliente] = {}

    def _recarregar(self) -> None:
        try:
            st = self.arquivo.stat()
        except OSError:
            self._marca, self._tabela = None, {}        # sem arquivo, sem chaves: tudo é 401 (falha fechada)
            return
        marca = (st.st_mtime_ns, st.st_size)
        if marca == self._marca:
            return
        bruto = json.loads(self.arquivo.read_text(encoding="utf-8") or "{}")
        todos = perfis.carregar()
        tabela = {}
        for h, entrada in bruto.items():
            if not entrada.get("ativo", True):
                continue
            try:
                tabela[h] = _cliente(entrada, todos)
            except ValueError as erro:
                raise ValueError(f"{self.arquivo.name}: chave de '{entrada.get('cliente')}': {erro}") from None
        self._marca, self._tabela = marca, tabela

    def autenticar(self, chave: str) -> Cliente | None:
        if not chave or len(chave) > 200:
            return None
        with self._trava:
            self._recarregar()
            return self._tabela.get(hash_da_chave(chave))

    def gerar(self, cliente: str, perfil: str, limite_por_minuto: int = LIMITE_MINUTO_PADRAO,
              perguntas_por_dia: int = PERGUNTAS_DIA_PADRAO) -> str:
        """Cria uma chave nova e grava só o hash. Devolve a chave em texto, que não será mostrada de novo."""
        entrada = {"cliente": cliente, "perfil": perfil, "limite_por_minuto": limite_por_minuto,
                   "perguntas_por_dia": perguntas_por_dia, "ativo": True}
        _cliente(entrada, perfis.carregar())                 # valida antes de gravar
        chave = PREFIXO + secrets.token_urlsafe(24)
        with self._trava:
            atual = json.loads(self.arquivo.read_text(encoding="utf-8") or "{}") if self.arquivo.exists() else {}
            atual[hash_da_chave(chave)] = entrada
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.arquivo.with_suffix(".tmp")
            tmp.write_text(json.dumps(atual, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.arquivo)
            self._marca = None
        return chave
