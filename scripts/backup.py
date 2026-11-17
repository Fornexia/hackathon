#!/usr/bin/env python3
"""Backup e restauração do FornexIA: tudo o que o git NÃO guarda, num único arquivo cifrado, para subir o servidor em outra máquina.

    python scripts/backup.py criar [--gerar-senha] [--destino PASTA] [--sem-grafo] [--sem-dados] [--sem-whatsapp] [--manter N]
    python scripts/backup.py verificar ARQUIVO                  confere senha e integridade sem escrever nada no projeto
    python scripts/backup.py restaurar ARQUIVO [--forcar] [--sem-grafo]

O que entra (e por quê): `.env`, `google-sa.json` e `api/chaves.json` (segredos), `dados/` (captura dos portais, caro de refazer, e
`dados/alertas/` com e-mails de clientes), o estado do WhatsApp (sessão e lista de acesso, sem a pasta de mídia) e o grafo do Neo4j
(`neo4j-admin database dump`, com o contêiner parado por alguns segundos). O código vem do git, não daqui. O banco do site (MariaDB) fica
na hospedagem: o `site/deploy.sh` já guarda o backup dele no servidor.

Cifra: AES-256-GCM em pedaços de 1 MiB, chave derivada da senha com scrypt (N=2^15). A senha vem de BACKUP_SENHA ou é pedida; nunca vai para
disco, log ou arquivo; `criar --gerar-senha` cria uma senha aleatória de 160 bits, mostra uma vez e só segue depois que você a digita de volta. Senha errada, arquivo adulterado ou truncado: a restauração recusa e não escreve nada. Só biblioteca padrão e `cryptography`.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import io
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

RAIZ = Path(__file__).resolve().parents[1]
VERSAO_DO_FORMATO = 1
MAGIC = b"FXBAK1\n"
PEDACO = 1024 * 1024
SCRYPT_N_LOG2, SCRYPT_R, SCRYPT_P = 15, 8, 1
SENHA_MINIMA = 12
CONTAINER_PADRAO = "hackathon-neo4j"
COMPOSE = "infra/docker-compose.yml"
PROJETO_FIXOS = (".env", "google-sa.json", "api/chaves.json")
SENSIVEIS = (".env", "google-sa.json", "api/chaves.json")
TAMANHO_CABECALHO = len(MAGIC) + 16 + 8 + 3


class ErroDeBackup(Exception):
    pass


# ---------- cifra ----------

def _chave(senha: str, sal: bytes) -> bytes:
    return hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=1 << SCRYPT_N_LOG2, r=SCRYPT_R, p=SCRYPT_P, dklen=32, maxmem=96 * 1024 * 1024)


def cifrar(origem: Path, destino: Path, senha: str) -> None:
    """Cifra `origem` em `destino`. Cada pedaço leva o cabeçalho e a marca de 'último' como dado autenticado: truncar ou emendar é detectado."""
    sal, prefixo = os.urandom(16), os.urandom(8)
    cab = MAGIC + sal + prefixo + bytes([SCRYPT_N_LOG2, SCRYPT_R, SCRYPT_P])
    aes = AESGCM(_chave(senha, sal))
    with open(origem, "rb") as f, open(destino, "wb") as g:
        g.write(cab)
        atual, i = f.read(PEDACO), 0
        while True:
            proximo = f.read(PEDACO)
            final = not proximo
            texto = aes.encrypt(prefixo + i.to_bytes(4, "big"), atual, cab + (b"\x01" if final else b"\x00"))
            g.write(len(texto).to_bytes(4, "big"))
            g.write(texto)
            if final:
                break
            atual, i = proximo, i + 1


def decifrar(origem: Path, destino: Path, senha: str) -> None:
    with open(origem, "rb") as f:
        cab = f.read(TAMANHO_CABECALHO)
        if len(cab) != TAMANHO_CABECALHO or cab[: len(MAGIC)] != MAGIC:
            raise ErroDeBackup("não é um backup do FornexIA (cabeçalho desconhecido)")
        sal, prefixo, params = cab[7:23], cab[23:31], tuple(cab[31:34])
        if params != (SCRYPT_N_LOG2, SCRYPT_R, SCRYPT_P):
            raise ErroDeBackup("formato de criptografia desconhecido: use o mesmo scripts/backup.py (versão) que criou o arquivo")
        aes = AESGCM(_chave(senha, sal))
        with open(destino, "wb") as g:
            i = 0
            while True:
                tam = f.read(4)
                if len(tam) != 4:
                    raise ErroDeBackup("arquivo truncado (falta o fim): a cópia foi interrompida ou o arquivo está incompleto")
                n = int.from_bytes(tam, "big")
                if not 16 <= n <= PEDACO + 16:
                    raise ErroDeBackup("arquivo corrompido (tamanho de bloco inválido)")
                texto = f.read(n)
                if len(texto) != n:
                    raise ErroDeBackup("arquivo truncado (falta o fim): a cópia foi interrompida ou o arquivo está incompleto")
                resto = f.read(1)
                final = resto == b""
                if not final:
                    f.seek(-1, os.SEEK_CUR)
                try:
                    g.write(aes.decrypt(prefixo + i.to_bytes(4, "big"), texto, cab + (b"\x01" if final else b"\x00")))
                except InvalidTag:
                    if i == 0:
                        raise ErroDeBackup("senha incorreta, ou o arquivo foi alterado") from None
                    raise ErroDeBackup("arquivo corrompido, alterado ou truncado") from None
                if final:
                    return
                i += 1


# ---------- utilidades ----------

def _saida_utf8() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _tamanho(n: int) -> str:
    for unidade in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidade == "GB":
            return f"{n:.0f} {unidade}" if unidade == "B" else f"{n:.1f} {unidade}"
        n /= 1024
    return f"{n} B"


def _ler_env(arquivo: Path) -> dict[str, str]:
    saida: dict[str, str] = {}
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8-sig").splitlines():
            if "=" in linha and not linha.lstrip().startswith("#"):
                k, v = linha.split("=", 1)
                if k.strip() and v.strip():
                    saida[k.strip()] = v.strip()
    return saida


def _whatsapp_dir() -> Path:
    return Path(os.environ.get("WHATSAPP_STATE_DIR") or Path.home() / ".claude" / "channels" / "whatsapp-hackathon")


def gerar_senha() -> str:
    """Senha aleatória de 160 bits: 32 letras e números sem os que se confundem (alfabeto base32: A-Z e 2-7), sem separadores."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def formatar_senha(compacta: str) -> str:
    """Em grupos de 4 separados por hífen, para copiar no papel sem errar: ABCD-EFGH-..."""
    return "-".join(compacta[i:i + 4] for i in range(0, len(compacta), 4))


def normalizar_senha(texto: str) -> str:
    """A senha gerada vale digitada com ou sem hífens e espaços, em maiúsculas ou minúsculas. Qualquer outra senha vale exatamente como foi digitada."""
    compacta = re.sub(r"[\s-]", "", texto).upper()
    return compacta if re.fullmatch(r"[A-Z2-7]{32}", compacta) else texto


def _senha(confirmar: bool, avisar_tamanho: bool) -> str:
    senha = os.environ.get("BACKUP_SENHA", "")
    if not senha:
        if not sys.stdin.isatty():
            raise ErroDeBackup("defina BACKUP_SENHA (não há terminal para pedir a senha)")
        senha = getpass.getpass("Senha do backup: ")
        if confirmar and getpass.getpass("Repita a senha: ") != senha:
            raise ErroDeBackup("as senhas não são iguais")
    senha = normalizar_senha(senha)
    if avisar_tamanho and len(senha) < SENHA_MINIMA:
        raise ErroDeBackup(f"a senha do backup precisa ter pelo menos {SENHA_MINIMA} caracteres")
    if not senha:
        raise ErroDeBackup("senha vazia")
    return senha


def _senha_gerada() -> str:
    """`criar --gerar-senha`: gera a senha, mostra UMA vez, só segue depois que a pessoa a digita de volta (prova de que a guardou) e limpa a tela."""
    if os.environ.get("BACKUP_SENHA"):
        raise ErroDeBackup("--gerar-senha não combina com BACKUP_SENHA: escolha uma das duas formas")
    if not sys.stdin.isatty():
        raise ErroDeBackup("--gerar-senha precisa de um terminal para mostrar a senha e confirmar que você a guardou (tarefa agendada: use BACKUP_SENHA)")
    senha = gerar_senha()
    print("\nSENHA DO BACKUP (aparece só esta vez; quem a perde, perde o backup):\n")
    print(f"    {formatar_senha(senha)}\n")
    print("Guarde AGORA: no Gerenciador de Senhas da conta da empresa e numa cópia no papel, em lugar seguro. Não vai para o .env, o git nem o chat.")
    for _ in range(3):
        if normalizar_senha(getpass.getpass("Digite a senha de novo para confirmar que você a guardou: ")) == senha:
            print("\033[2J\033[H", end="")          # limpa a tela: a senha não fica no histórico do terminal
            print("Senha confirmada e apagada da tela. Criando o backup...")
            return senha
        print("Não bateu. Confira a cópia que você fez.")
    raise ErroDeBackup("a confirmação não bateu em 3 tentativas: nenhum backup foi criado")


def _git(raiz: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


# ---------- docker / Neo4j ----------

def _docker(*args: str, env: dict | None = None, ok: tuple = (0,), cwd: Path | None = None) -> str:
    try:
        r = subprocess.run(["docker", *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, **(env or {})}, cwd=cwd)
    except FileNotFoundError:
        raise ErroDeBackup("o comando `docker` não foi encontrado: instale e ligue o Docker, ou use --sem-grafo") from None
    if r.returncode not in ok:
        raise ErroDeBackup(f"`docker {args[0]}` falhou: {(r.stderr or r.stdout).strip()[-400:]}")
    return r.stdout.strip()


def docker_disponivel() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def container_existe(nome: str) -> bool:
    try:
        return subprocess.run(["docker", "inspect", nome], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def container_rodando(nome: str) -> bool:
    return _docker("inspect", "-f", "{{.State.Running}}", nome) == "true"


def volume_de_dados(nome: str) -> str:
    montagens = json.loads(_docker("inspect", "-f", "{{json .Mounts}}", nome))
    for m in montagens:
        if m.get("Destination") == "/data" and m.get("Type") == "volume":
            return m["Name"]
    raise ErroDeBackup(f"o contêiner {nome} não tem um volume em /data")


def imagem_do_container(nome: str) -> str:
    return _docker("inspect", "-f", "{{.Config.Image}}", nome)


def contar_nos(nome: str, senha_neo4j: str | None) -> int | None:
    """Quantos nós o grafo tem (para conferir depois da restauração). None se não deu para consultar."""
    if not senha_neo4j:
        return None
    try:
        saida = _docker("exec", "-e", "NEO4J_PASSWORD", nome, "cypher-shell", "-u", "neo4j", "--format", "plain",
                        "MATCH (n) RETURN count(n) AS n", env={"NEO4J_PASSWORD": senha_neo4j})
        return int(saida.strip().splitlines()[-1])
    except (ErroDeBackup, ValueError, IndexError):
        return None


def _dump(imagem: str, volume: str, destino: Path) -> None:
    tmp = f"fx-backup-dump-{os.getpid()}"
    try:
        _docker("run", "--name", tmp, "-v", f"{volume}:/data", imagem, "neo4j-admin", "database", "dump", "neo4j", "--to-path=/tmp")
        _docker("cp", f"{tmp}:/tmp/neo4j.dump", str(destino))
    finally:
        _docker("rm", "-f", tmp, ok=(0, 1))


def _carregar(imagem: str, volume: str, dump: Path) -> None:
    tmp = f"fx-backup-load-{os.getpid()}"
    try:
        _docker("create", "--name", tmp, "-v", f"{volume}:/data", imagem, "neo4j-admin", "database", "load", "neo4j",
                "--from-path=/tmp", "--overwrite-destination=true")
        _docker("cp", str(dump), f"{tmp}:/tmp/neo4j.dump")
        _docker("start", "-a", tmp)
    finally:
        _docker("rm", "-f", tmp, ok=(0, 1))


def _esperar_saudavel(nome: str, limite_s: int = 180) -> bool:
    fim = time.time() + limite_s
    while time.time() < fim:
        estado = _docker("inspect", "-f", "{{if .State.Health}}{{.State.Health.Status}}{{else}}sem-healthcheck{{end}}", nome, ok=(0, 1))
        if estado == "healthy":
            return True
        time.sleep(3)
    return False


# ---------- inventário ----------

def inventario(raiz: Path, sem_dados: bool, sem_whatsapp: bool) -> list[tuple[str, Path]]:
    """(nome dentro do pacote, caminho no disco). Só arquivos comuns: links simbólicos não entram."""
    itens: list[tuple[str, Path]] = []
    for rel in PROJETO_FIXOS:
        p = raiz / rel
        if p.is_file() and not p.is_symlink():
            itens.append((f"projeto/{rel}", p))
    if not sem_dados and (raiz / "dados").is_dir():
        for p in sorted((raiz / "dados").rglob("*")):
            if p.is_file() and not p.is_symlink():
                itens.append((f"projeto/{p.relative_to(raiz).as_posix()}", p))
    wa = _whatsapp_dir()
    if not sem_whatsapp and wa.is_dir():
        for p in sorted(wa.rglob("*")):
            rel = p.relative_to(wa)
            if p.is_file() and not p.is_symlink() and rel.parts[0] != "midia":
                itens.append((f"whatsapp/{rel.as_posix()}", p))
    return itens


def separar_nome(nome: str) -> tuple[str, str]:
    """Valida um nome de dentro do pacote e o separa em (origem, caminho relativo). Recusa tudo que possa sair da pasta de destino."""
    partes = nome.split("/")
    if "\\" in nome or nome.startswith("/") or len(partes) < 2 or any(p in ("", ".", "..") for p in partes) or ":" in partes[0]:
        raise ErroDeBackup(f"nome inválido dentro do backup: {nome[:80]!r}")
    origem, rel = partes[0], "/".join(partes[1:])
    if origem == "projeto":
        if not (rel in PROJETO_FIXOS or rel.startswith("dados/")):
            raise ErroDeBackup(f"o backup traz um caminho que esta versão não restaura: {rel[:80]!r}")
    elif origem != "whatsapp":
        raise ErroDeBackup(f"origem desconhecida no backup: {origem[:40]!r}")
    return origem, rel


def destino_de(nome: str, raiz: Path) -> Path:
    origem, rel = separar_nome(nome)
    base = raiz if origem == "projeto" else _whatsapp_dir()
    destino = (base / rel)
    if not destino.resolve().is_relative_to(base.resolve()):
        raise ErroDeBackup(f"caminho fora da pasta de destino: {nome[:80]!r}")
    return destino


# ---------- criar ----------

def criar(raiz: Path, destino: Path, senha: str, sem_grafo: bool = False, sem_dados: bool = False, sem_whatsapp: bool = False,
          manter: int = 10, container: str | None = None, agora: datetime | None = None) -> Path:
    agora = agora or datetime.now().astimezone()
    container = container or os.environ.get("NEO4J_CONTAINER") or CONTAINER_PADRAO
    destino.mkdir(parents=True, exist_ok=True)
    avisos: list[str] = []
    with tempfile.TemporaryDirectory(prefix="fx-backup-") as tmp_:
        tmp = Path(tmp_)
        grafo = {"incluido": False}
        dump = tmp / "neo4j.dump"
        if not sem_grafo:
            if not docker_disponivel():
                raise ErroDeBackup("o Docker não está ligado: ligue-o, ou rode com --sem-grafo (o grafo pode ser refeito com coleta/carregar_neo4j.py a partir de dados/)")
            if not container_existe(container):
                avisos.append(f"contêiner {container} não existe: o grafo ficou fora do backup")
            else:
                senha_neo = os.environ.get("NEO4J_SENHA") or _ler_env(raiz / ".env").get("NEO4J_SENHA")
                rodando = container_rodando(container)
                nos = contar_nos(container, senha_neo) if rodando else None
                volume, imagem = volume_de_dados(container), imagem_do_container(container)
                if rodando:
                    print(f"Parando {container} por alguns segundos para copiar o grafo...")
                    _docker("stop", "-t", "90", container)
                try:
                    _dump(imagem, volume, dump)
                finally:
                    if rodando:
                        _docker("start", container)
                        print(f"{container} religado.")
                grafo = {"incluido": True, "container": container, "imagem": imagem, "nos": nos, "bytes": dump.stat().st_size, "sha256": _sha256(dump)}
                if nos is None:
                    avisos.append("não deu para contar os nós antes da cópia (Neo4j parado ou NEO4J_SENHA ausente): a conferência da restauração será só pelo hash")
        arquivos = []
        for nome, caminho in inventario(raiz, sem_dados, sem_whatsapp):
            arquivos.append({"nome": nome, "bytes": caminho.stat().st_size, "sha256": _sha256(caminho)})
        manifesto = {
            "versao": VERSAO_DO_FORMATO, "criado_em": agora.isoformat(timespec="seconds"), "sistema": platform.system(),
            "python": platform.python_version(), "git": {"commit": _git(raiz, "rev-parse", "--short", "HEAD"), "branch": _git(raiz, "rev-parse", "--abbrev-ref", "HEAD")},
            "grafo": grafo, "arquivos": arquivos,
        }
        pacote = tmp / "pacote.tar.gz"

        def sem_dono(info: tarfile.TarInfo) -> tarfile.TarInfo:
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            return info

        with tarfile.open(pacote, "w:gz") as tar:
            dados = json.dumps(manifesto, ensure_ascii=False, indent=1).encode("utf-8")
            info = tarfile.TarInfo("manifest.json")
            info.size, info.mtime = len(dados), int(agora.timestamp())
            tar.addfile(info, io.BytesIO(dados))
            for nome, caminho in inventario(raiz, sem_dados, sem_whatsapp):
                tar.add(caminho, arcname=nome, recursive=False, filter=sem_dono)
            if grafo["incluido"]:
                tar.add(dump, arcname="grafo/neo4j.dump", recursive=False, filter=sem_dono)
        saida = destino / f"fornexia-{agora:%Y%m%d-%H%M%S}.fxbak"
        cifrar(pacote, saida, senha)
    try:
        os.chmod(saida, 0o600)
    except OSError:
        pass
    antigos = sorted(destino.glob("fornexia-*.fxbak"))
    for velho in antigos[: max(0, len(antigos) - manter)] if manter > 0 else []:
        velho.unlink()
    print(f"Backup criado: {saida}")
    print(f"  tamanho: {_tamanho(saida.stat().st_size)} | arquivos: {len(arquivos)} | grafo: " + (f"sim ({grafo.get('nos', '?')} nós)" if grafo["incluido"] else "não"))
    print(f"  sha256 do arquivo (compare depois de copiar): {_sha256(saida)}")
    for a in avisos:
        print(f"  aviso: {a}")
    print("  Copie para FORA deste computador (outro PC, nuvem, pendrive). A senha do backup guarde à parte, num gerenciador de senhas.")
    return saida


# ---------- ler, verificar, restaurar ----------

def _abrir(arquivo: Path, senha: str, tmp: Path) -> tuple[dict, Path]:
    """Decifra para `tmp` e confere o pacote inteiro (nomes, tipos e sha256 de cada arquivo). Devolve (manifesto, caminho do .tar.gz)."""
    pacote = tmp / "pacote.tar.gz"
    decifrar(arquivo, pacote, senha)
    try:
        with tarfile.open(pacote, "r:gz") as tar:
            membros = {m.name: m for m in tar.getmembers()}
            if "manifest.json" not in membros or not membros["manifest.json"].isreg():
                raise ErroDeBackup("o backup não tem manifesto")
            manifesto = json.loads(tar.extractfile(membros["manifest.json"]).read().decode("utf-8"))
            esperados = {a["nome"]: a for a in manifesto.get("arquivos", [])}
            if manifesto.get("grafo", {}).get("incluido"):
                esperados["grafo/neo4j.dump"] = {"nome": "grafo/neo4j.dump", "sha256": manifesto["grafo"]["sha256"]}
            extras = set(membros) - set(esperados) - {"manifest.json"}
            faltam = set(esperados) - set(membros)
            if extras or faltam:
                raise ErroDeBackup("o conteúdo do backup não bate com o manifesto")
            for nome, m in membros.items():
                if nome == "manifest.json":
                    continue
                if not m.isreg():
                    raise ErroDeBackup(f"o backup traz um item que não é arquivo comum: {nome[:80]!r}")
                if nome != "grafo/neo4j.dump":
                    separar_nome(nome)
                h = hashlib.sha256()
                f = tar.extractfile(m)
                for bloco in iter(lambda: f.read(1 << 20), b""):
                    h.update(bloco)
                if h.hexdigest() != esperados[nome]["sha256"]:
                    raise ErroDeBackup(f"conteúdo alterado: {nome[:80]!r}")
    except (tarfile.TarError, json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
        raise ErroDeBackup(f"pacote ilegível ({type(e).__name__})") from None
    return manifesto, pacote


def resumo(manifesto: dict) -> str:
    g = manifesto.get("grafo", {})
    return (f"criado em {manifesto.get('criado_em')} | git {manifesto.get('git', {}).get('branch')}@{manifesto.get('git', {}).get('commit')} | "
            f"{len(manifesto.get('arquivos', []))} arquivos | grafo: " + (f"sim, {g.get('nos', '?')} nós, imagem {g.get('imagem')}" if g.get("incluido") else "não"))


def verificar(arquivo: Path, senha: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="fx-verificar-") as tmp:
        manifesto, _ = _abrir(arquivo, senha, Path(tmp))
    print(f"Backup íntegro e senha correta: {resumo(manifesto)}")
    return manifesto


def restaurar(arquivo: Path, senha: str, raiz: Path, forcar: bool = False, sem_grafo: bool = False, container: str | None = None) -> None:
    container = container or os.environ.get("NEO4J_CONTAINER") or CONTAINER_PADRAO
    with tempfile.TemporaryDirectory(prefix="fx-restaurar-") as tmp_:
        tmp = Path(tmp_)
        manifesto, pacote = _abrir(arquivo, senha, tmp)
        print(f"Backup íntegro: {resumo(manifesto)}")
        com_grafo = bool(manifesto.get("grafo", {}).get("incluido")) and not sem_grafo

        # 1) Tudo o que pode atrapalhar é conferido ANTES de escrever qualquer coisa.
        plano = []
        conflitos = []
        for a in manifesto["arquivos"]:
            dest = destino_de(a["nome"], raiz)
            if dest.exists() and _sha256(dest) != a["sha256"]:
                conflitos.append(str(dest))
            plano.append((a, dest))
        if com_grafo:
            if not docker_disponivel():
                raise ErroDeBackup("o Docker não está ligado: ligue-o, ou use --sem-grafo e refaça o grafo com coleta/carregar_neo4j.py")
            if container_existe(container) and not forcar:
                nos = contar_nos(container, os.environ.get("NEO4J_SENHA") or _ler_env(raiz / ".env").get("NEO4J_SENHA")) if container_rodando(container) else None
                if nos is None or nos > 0:
                    conflitos.append(f"grafo do contêiner {container} (já existe e a restauração o apagaria)")
        if conflitos and not forcar:
            lista = "\n  ".join(conflitos[:10]) + (f"\n  ... e mais {len(conflitos) - 10}" if len(conflitos) > 10 else "")
            raise ErroDeBackup(f"{len(conflitos)} item(ns) já existem e são diferentes do backup. Nada foi escrito. Confira e, se for isso mesmo, rode com --forcar "
                               f"(os arquivos atuais ficam ao lado, com a marca .antes-AAAAMMDD-HHMMSS):\n  {lista}")

        # 2) Arquivos.
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        escritos = 0
        with tarfile.open(pacote, "r:gz") as tar:
            for a, dest in plano:
                if dest.exists() and _sha256(dest) == a["sha256"]:
                    continue
                if dest.exists():
                    dest.rename(dest.with_name(dest.name + f".antes-{marca}"))
                dest.parent.mkdir(parents=True, exist_ok=True)
                parcial = dest.with_name(dest.name + ".fxtmp")
                with open(parcial, "wb") as g:
                    shutil.copyfileobj(tar.extractfile(a["nome"]), g)
                os.replace(parcial, dest)
                if a["nome"].startswith("whatsapp/") or a["nome"].removeprefix("projeto/") in SENSIVEIS:
                    try:
                        os.chmod(dest, 0o600)
                    except OSError:
                        pass
                escritos += 1
            print(f"Arquivos restaurados: {escritos} (os {len(plano) - escritos} restantes já eram idênticos).")

            # 3) Grafo.
            if com_grafo:
                dump = tmp / "neo4j.dump"
                with open(dump, "wb") as g:
                    shutil.copyfileobj(tar.extractfile("grafo/neo4j.dump"), g)
                _restaurar_grafo(raiz, dump, manifesto["grafo"], container)
    print("Restauração concluída.")


def _restaurar_grafo(raiz: Path, dump: Path, grafo: dict, container: str) -> None:
    if not (raiz / ".env").exists():
        raise ErroDeBackup("sem .env no projeto: o compose precisa de NEO4J_SENHA (o .env está no backup; restaure os arquivos antes)")
    env_proj = _ler_env(raiz / ".env")
    senha_neo = env_proj.get("NEO4J_SENHA")
    print("Criando o contêiner do Neo4j (docker compose)...")
    _docker("compose", "--env-file", ".env", "-f", COMPOSE, "up", "--no-start", "neo4j", cwd=raiz)
    if container_rodando(container):
        print("Parando o Neo4j para carregar o grafo...")
        _docker("stop", "-t", "90", container)
    volume, imagem = volume_de_dados(container), imagem_do_container(container)
    print("Carregando o grafo (neo4j-admin database load)...")
    _carregar(imagem, volume, dump)
    print("Ligando o Neo4j...")
    _docker("start", container)
    if not _esperar_saudavel(container):
        raise ErroDeBackup(f"o Neo4j não ficou saudável em 3 minutos: veja `docker logs {container}`")
    esperado, atual = grafo.get("nos"), None
    for _ in range(10):
        atual = contar_nos(container, senha_neo)
        if atual is not None:
            break
        time.sleep(3)
    if esperado is not None and atual is not None:
        print(f"Grafo: {atual} nós (no backup: {esperado}) " + ("OK" if atual == esperado else "ATENÇÃO: números diferentes"))
        if atual != esperado:
            raise ErroDeBackup("o número de nós restaurado difere do backup")
    else:
        print(f"Grafo carregado e saudável (nós agora: {atual if atual is not None else 'não consultado'}).")


# ---------- linha de comando ----------

def main(argv: list[str]) -> int:
    _saida_utf8()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="comando", required=True)
    c = sub.add_parser("criar")
    c.add_argument("--destino", type=Path, default=Path(os.environ.get("BACKUP_DESTINO") or Path.home() / "backups-fornexia"))
    c.add_argument("--sem-grafo", action="store_true")
    c.add_argument("--sem-dados", action="store_true")
    c.add_argument("--sem-whatsapp", action="store_true")
    c.add_argument("--gerar-senha", action="store_true", help="gera uma senha forte aleatória, mostra uma vez e pede para você digitá-la de volta")
    c.add_argument("--manter", type=int, default=10, help="quantos backups guardar na pasta (padrão 10; 0 = não apagar nenhum)")
    v = sub.add_parser("verificar")
    v.add_argument("arquivo", type=Path)
    r = sub.add_parser("restaurar")
    r.add_argument("arquivo", type=Path)
    r.add_argument("--forcar", action="store_true", help="sobrescreve o que já existe (o antigo fica ao lado com .antes-...)")
    r.add_argument("--sem-grafo", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.comando == "criar":
            senha = _senha_gerada() if a.gerar_senha else _senha(confirmar=True, avisar_tamanho=True)
            criar(RAIZ, a.destino, senha, a.sem_grafo, a.sem_dados, a.sem_whatsapp, a.manter)
        elif a.comando == "verificar":
            verificar(a.arquivo, _senha(confirmar=False, avisar_tamanho=False))
        else:
            restaurar(a.arquivo, _senha(confirmar=False, avisar_tamanho=False), RAIZ, a.forcar, a.sem_grafo)
    except ErroDeBackup as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    except OSError as erro:
        print(f"erro de arquivo: {erro.strerror or erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
