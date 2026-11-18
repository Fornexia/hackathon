"""O resumo de api/medir.py: contas certas, sem inventar custo."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import medir  # noqa: E402


def linha(porta, status, ms, **extra):
    return {"ts": "2026-11-18T10:00:00.000-03:00", "evento": "requisicao", "porta": porta, "status": status, "duracao_ms": ms,
            "cliente": extra.pop("cliente", "a"), **extra}


class TestMedir(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.pasta = Path(self.d.name)

    def tearDown(self):
        self.d.cleanup()

    def grava(self, nome, registros):
        (self.pasta / nome).write_text("\n".join(json.dumps(r) for r in registros) + "\nlixo que nao e json\n", encoding="utf-8")

    def test_resumo_por_porta_com_erro_mediana_e_custo(self):
        self.grava("api.jsonl", [linha("rest", 200, 10, tool="cobertura"), linha("rest", 200, 30, tool="cobertura"), linha("rest", 400, 20),
                                 linha("mcp", 200, 50),
                                 linha("pergunta", 200, 4000, custo_usd=0.02, tokens_entrada=1000, fontes=2),
                                 linha("pergunta", 200, 6000, custo_usd=0.04, tokens_entrada=3000, fontes=0),
                                 linha("pergunta", 502, 100000)])
        r = {x["porta"]: x for x in medir.resumo(medir.ler(self.pasta, None, None))}
        self.assertEqual((r["rest"]["chamadas"], r["rest"]["erros"], r["rest"]["taxa_de_erro"], r["rest"]["mediana_ms"]), (3, 1, 33.3, 20))
        self.assertEqual(r["mcp"]["chamadas"], 1)
        p = r["pergunta"]
        self.assertEqual((p["chamadas"], p["erros"]), (3, 1))
        self.assertEqual((p["custo_total_usd"], p["custo_medio_usd"], p["perguntas_sem_custo_informado"]), (0.06, 0.03, 1))
        self.assertEqual(p["tokens_entrada_medio"], 2000)

    def test_pergunta_sem_custo_informado_nao_vira_custo_zero_inventado(self):
        self.grava("api.jsonl", [linha("pergunta", 200, 100, custo_usd=None, tokens_entrada=None, fontes=1)])
        p = medir.resumo(medir.ler(self.pasta, None, None))[0]
        self.assertIsNone(p["custo_medio_usd"])
        self.assertEqual(p["perguntas_sem_custo_informado"], 1)

    def test_filtra_por_data_e_cliente_e_le_arquivos_girados(self):
        self.grava("api.jsonl", [linha("rest", 200, 10, cliente="a")])
        self.grava("api.jsonl.1", [linha("rest", 200, 10, cliente="b"), {**linha("rest", 200, 10), "ts": "2026-11-01T10:00:00.000-03:00"}])
        self.assertEqual(len(medir.ler(self.pasta, None, None)), 3)
        self.assertEqual(len(medir.ler(self.pasta, "2026-11-18", None)), 2)
        self.assertEqual(len(medir.ler(self.pasta, None, "b")), 1)

    def test_ignora_o_que_nao_e_requisicao_de_porta(self):
        self.grava("api.jsonl", [{"evento": "recusada", "porta": "mcp"}, {"evento": "falha"}, linha("rest", 200, 5)])
        self.assertEqual(len(medir.ler(self.pasta, None, None)), 1)


if __name__ == "__main__":
    unittest.main()
