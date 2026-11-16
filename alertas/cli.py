"""Alertas por e-mail quando algo muda nos fornecedores acompanhados. Veja alertas/README.md.

    python alertas/cli.py assinar EMAIL PERFIL CNPJ [CNPJ ...] [--verificado]   cria a assinatura (mostra o código de cancelamento);
                                                                  sem --verificado ela fica parada até `confirmar`
    python alertas/cli.py confirmar ID_OU_EMAIL                   marca o e-mail como verificado
    python alertas/cli.py listar                                  assinaturas ativas (sem mostrar o código)
    python alertas/cli.py cancelar CODIGO_OU_EMAIL                cancela
    python alertas/cli.py verificar [--ensaio]                    compara com a última foto e envia os avisos; --ensaio só mostra
    python alertas/cli.py enviar-teste EMAIL                      manda um e-mail de teste pelo canal configurado
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assinaturas  # noqa: E402
import envio  # noqa: E402
import monitor  # noqa: E402


def _saida_utf8() -> None:
    for fluxo in (sys.stdout, sys.stderr):          # o console do Windows usa cp1252 e quebra a acentuação
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str]) -> int:
    _saida_utf8()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("assinar")
    s.add_argument("email"), s.add_argument("perfil"), s.add_argument("cnpjs", nargs="+")
    s.add_argument("--verificado", action="store_true", help="o e-mail já foi confirmado (use só em demonstração ou depois de conferir o código)")
    s.add_argument("--origem", choices=assinaturas.ORIGENS, default="cli")
    k = sub.add_parser("confirmar")
    k.add_argument("alvo")
    sub.add_parser("listar")
    c = sub.add_parser("cancelar")
    c.add_argument("codigo")
    v = sub.add_parser("verificar")
    v.add_argument("--ensaio", action="store_true", help="não envia e não grava nada: só mostra o que seria enviado")
    t = sub.add_parser("enviar-teste")
    t.add_argument("email")
    a = ap.parse_args(argv)
    loja = assinaturas.Assinaturas()

    try:
        if a.comando == "assinar":
            nova = loja.criar(a.email, a.perfil, a.cnpjs, verificado=a.verificado, origem=a.origem)
            print(f"Assinatura {nova['id']}: {nova['email']}, perfil {nova['perfil']}, {len(nova['cnpjs'])} CNPJ(s), "
                  + ("e-mail verificado." if nova["email_verificado"] else "e-mail NÃO verificado: nenhum aviso sai até `confirmar`."))
            print(f"Código de cancelamento (vai em todo e-mail): {nova['token']}")
            print("A primeira verificação só tira a foto de hoje; o aviso vem quando algo mudar depois dela.")
        elif a.comando == "confirmar":
            n = loja.marcar_verificado(a.alvo)
            print(f"{n} assinatura(s) com e-mail verificado." if n else "Nada a confirmar para este alvo.")
            return 0 if n else 1
        elif a.comando == "listar":
            for x in loja.listar(so_ativas=True):
                print(f"{x['id']}  {x['email']:30} {x['perfil']:16} {len(x['cnpjs'])} CNPJ(s)  {'verificado' if x.get('email_verificado') else 'NÃO verificado':14} último envio: {x['ultimo_envio'] or 'nunca'}")
        elif a.comando == "cancelar":
            n = loja.cancelar(a.codigo)
            print(f"{n} assinatura(s) cancelada(s)." if n else "Nada encontrado para este código.")
            return 0 if n else 1
        elif a.comando == "enviar-teste":
            print("Enviado:", envio.enviar(envio.mensagem_de_teste(a.email, datetime.now().astimezone())))
        elif a.comando == "verificar":
            for r in monitor.verificar(loja, monitor.FonteGrafo, envio.enviar_aviso, ensaio=a.ensaio):
                if "erro" in r:
                    print(f"[{r['id']}] ERRO {r['erro']}")
                    continue
                print(f"[{r['id']}] {r['eventos']} aviso(s)"
                      + (f", linha de base: {len(r['linha_de_base'])} CNPJ(s)" if r["linha_de_base"] else "")
                      + (f", enviado: {r['enviado_para']}" if r["enviado_para"] else "")
                      + (" (ensaio, nada enviado)" if a.ensaio and r["eventos"] else ""))
                for e in r["lista"] if a.ensaio else []:
                    print(f"    - {e['titulo']}: {e['detalhe']}")
                for aviso in r["avisos"]:
                    print(f"    ! {aviso}")
                if r.get("erro_de_envio"):
                    print(f"    ! envio falhou, tenta de novo na próxima rodada: {r['erro_de_envio']}")
    except assinaturas.ErroDeAssinatura as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
