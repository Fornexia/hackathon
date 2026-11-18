"""Simula uma mudança na fonte, SÓ no Neo4j de teste (dados de exemplo), para ensaiar o alerta sem esperar o portal mudar.

    python alertas/simular.py sancao-nova --banco-de-teste
    python alertas/simular.py sancao-encerrada --banco-de-teste
    python alertas/simular.py contrato-novo --banco-de-teste
    python alertas/simular.py restaurar --banco-de-teste          # desfaz tudo o que esta ferramenta criou

Mexe apenas no ente fictício `ex-estado` e no fornecedor `cnpj:33333333000133` ("Obras Exemplares Ltda (fictícia)"), nos nós com prefixo `sim:`.
Recusa rodar sem `--banco-de-teste` e recusa o banco padrão do bot (porta 7689). NEO4J_URI e NEO4J_SENHA vêm do ambiente.
"""

import argparse
import os
import sys

from neo4j import GraphDatabase

FORNECEDOR = "cnpj:33333333000133"
ENTE = "ex-estado"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("acao", choices=["sancao-nova", "sancao-encerrada", "contrato-novo", "restaurar"])
    ap.add_argument("--banco-de-teste", action="store_true", help="confirma que NEO4J_URI aponta para um Neo4j descartável")
    a = ap.parse_args(argv)
    uri = os.environ.get("NEO4J_URI", "")
    if not a.banco_de_teste:
        print("recusado: confirme com --banco-de-teste (isto grava no Neo4j)", file=sys.stderr)
        return 1
    if not uri or uri.rstrip("/").endswith(":7689"):
        print("recusado: NEO4J_URI vazio ou apontando para o banco padrão do bot (7689)", file=sys.stderr)
        return 1
    with GraphDatabase.driver(uri, auth=("neo4j", os.environ.get("NEO4J_SENHA", ""))) as driver, driver.session() as s:
        if a.acao == "sancao-nova":
            s.run("""MATCH (f:Fornecedor {id: $f}), (t:Ente {id: $t})
                     MERGE (e:Evidencia {id: 'sim:e1'}) SET e.tenant = $t, e.trecho = 'SUSPENSAO TEMPORARIA, Obras Exemplares Ltda (simulado)',
                         e.url = 'https://exemplo.invalid/simulado', e.arquivo = 'simulado.json', e.documento_hash = 'x', e.capturado_em = toString(datetime())
                     MERGE (s:Sancao {id: 'sim:sancao:1'}) SET s.tenant = $t, s.sensibilidade = 'publico', s.cadastro = 'ceis', s.tipo = 'Impedimento de licitar (simulado)',
                         s.situacao = 'Vigente', s.publicada_em = '2026-11-16', s.inicio_suspensao = '2026-11-16', s.orgao = 'Órgão de Exemplo'
                     MERGE (f)-[:RECEBEU]->(s) MERGE (s)-[:PROVADO_POR]->(e) MERGE (s)-[:DO_ENTE]->(t)""", f=FORNECEDOR, t=ENTE)
        elif a.acao == "sancao-encerrada":
            s.run("MATCH (s:Sancao {id: 'sim:sancao:1'}) SET s.situacao = 'Encerrada', s.fim_suspensao = '2026-11-17'")
        elif a.acao == "contrato-novo":
            s.run("""MATCH (f:Fornecedor {id: $f}), (t:Ente {id: $t}) MATCH (u:UnidadeJurisdicionada {id: 'ex-estado:uj:exemplo'})
                     MERGE (e:Evidencia {id: 'sim:e2'}) SET e.tenant = $t, e.trecho = 'Contrato 9/2026 (simulado)', e.url = 'https://exemplo.invalid/simulado',
                         e.arquivo = 'simulado.json', e.documento_hash = 'x', e.capturado_em = toString(datetime())
                     MERGE (c:Contrato {id: 'sim:contrato:9'}) SET c.tenant = $t, c.sensibilidade = 'publico', c.numero = '9/2026', c.objeto = 'Drenagem (simulado)',
                         c.valor_contratado = 250000.0, c.inicio = '2026-11-16', c.fim = '2027-11-16', c.tem_aditivo = false
                     MERGE (c)-[:CONTRATA]->(f) MERGE (c)-[:PROVADO_POR]->(e) MERGE (c)-[:DO_ENTE]->(t) MERGE (c)-[:CELEBRADO_POR]->(u)""", f=FORNECEDOR, t=ENTE)
        else:
            s.run("MATCH (n) WHERE n.id STARTS WITH 'sim:' DETACH DELETE n")
        print("ok:", a.acao)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
