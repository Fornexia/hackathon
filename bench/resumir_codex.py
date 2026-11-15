"""Resume uma rodada medida, sem confundir limite semanal com janela de 5h."""
import argparse
import collections
import datetime as dt
import json
from pathlib import Path
import statistics


def brl(n):
    return ('R$ ' + f'{n:,.4f}').replace(',', '_').replace('.', ',').replace('_', '.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rodada', type=Path)
    ap.add_argument('--relatorio', type=Path, required=True)
    args = ap.parse_args()
    pasta = args.rodada.resolve()
    resumo = json.loads((pasta/'resumo.json').read_text())
    meta = json.loads((pasta/'metadados.json').read_text())
    rs = [json.loads(f.read_text()) for f in sorted(pasta.glob('consulta-*.json'))]
    antes = resumo['antes']['rateLimits']['primary']
    depois = resumo['depois']['rateLimits']['primary']
    assert antes['resetsAt'] == depois['resetsAt'], 'A janela virou durante a rodada: não extrapolar diferenças.'
    assert antes['windowDurationMins'] == depois['windowDurationMins']
    delta = depois['usedPercent']-antes['usedPercent']
    assert delta >= 0
    janela_dias = antes['windowDurationMins']/1440
    total = len(rs)
    preco = meta['preco_mensal_codex_brl_premissa']
    vps = meta['preco_mensal_vps_brl_premissa']
    t = resumo['duracao_total_s']
    evidencia, hashes_ok, tool_erros = 0, 0, 0
    for r in rs:
        for i in r['itens']:
            if i.get('type') != 'mcpToolCall': continue
            if i.get('error') or i.get('status') != 'completed': tool_erros += 1
            if i.get('tool') != 'conferir_evidencia': continue
            for c in (i.get('result') or {}).get('content', []):
                if c.get('type') != 'text': continue
                try: d = json.loads(c['text'])
                except (ValueError, KeyError): continue
                if isinstance(d, dict) and 'hash_confere' in d:
                    evidencia += 1
                    hashes_ok += bool(d['hash_confere'])
    d = {'total':total, 'sucessos_operacionais':resumo['sucessos_operacionais'], 'delta_pp':delta,
         'janela_minutos':antes['windowDurationMins'], 'antes_percentual':antes['usedPercent'],
         'depois_percentual':depois['usedPercent'], 'duracao_s':t,
         'perguntas_em_5h_por_vazao_observada':total*18000/t,
         'evidencias_conferidas':evidencia, 'hashes_ok':hashes_ok, 'tool_erros':tool_erros,
         'perguntas_por_tipo':dict(collections.Counter(x['tipo'] for x in rs)), 'tokens':resumo['tokens']}
    if delta:
        d.update({'perguntas_por_1pp_estimativa':total/delta,
                  'perguntas_por_janela_estimativa':100*total/delta,
                  'perguntas_por_mes_estimativa':100*total/delta*30/janela_dias})
        d['custo_codex_por_pergunta_em_plena_utilizacao_estimativa'] = preco/d['perguntas_por_mes_estimativa']
        d['media_sustentavel_por_5h_por_rateio_da_cota'] = d['perguntas_por_janela_estimativa']*300/antes['windowDurationMins']
    else:
        d['capacidade_por_janela_limite_inferior_condicional'] = 100*total
        d['capacidade_por_mes_limite_inferior_condicional'] = 100*total*30/janela_dias
        d['custo_codex_por_pergunta_limite_superior_condicional'] = preco/d['capacidade_por_mes_limite_inferior_condicional']
    (pasta/'analise.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
    linhas = [
        '# Custo do Codex no FornexIA — medição de 06/11/2026', '',
        f'Rodada: `{pasta.relative_to(Path(__file__).resolve().parents[1])}`. Modelo `{meta["modelo"]}`, raciocínio `{meta["esforco"]}`, autenticação ChatGPT `{meta["plano"]}`, cliente `{meta["cli"]}`.', '',
        f'Foram executadas {total} perguntas únicas, em sessões independentes, com até {meta["paralelismo"]} em paralelo e acesso somente às oito consultas MCP do projeto. O site e o worker de produção não foram trocados para Codex.', '',
        '| Medida | Resultado |', '|---|---|',
        f'| Perguntas respondidas | {sum(x.get("status") == "completed" and bool(x["resposta"]) for x in rs)}/{total} |',
        f'| Perguntas com resposta e chamada MCP concluída | {resumo["sucessos_operacionais"]}/{total} |',
        f'| Janela efetivamente informada pela conta | {antes["windowDurationMins"]} minutos ({janela_dias:g} dias) |',
        f'| Consumo antes → depois | {antes["usedPercent"]}% → {depois["usedPercent"]}% |',
        f'| Variação visível | {delta} ponto(s) percentual(is) |',
        f'| Tempo total da rodada | {t:.1f} segundos ({t/60:.2f} minutos) |',
        f'| Latência média / mediana por pergunta | {resumo["latencia_media_s"]:.2f} s / {resumo["latencia_mediana_s"]:.2f} s |',
        f'| Perguntas em 5h, extrapoladas pela vazão com {meta["paralelismo"]} simultâneas | {d["perguntas_em_5h_por_vazao_observada"]:.0f} |',
        f'| Conferências de evidência / hashes válidos | {evidencia} / {hashes_ok} |', '',
        'A pergunta 100, sobre CPF, foi recusada conforme a regra de proteção de dados, sem chamar uma ferramenta. Houve uma falha em buscar_fornecedor na pergunta 6; a sessão terminou com resposta baseada na consulta de cobertura. Não foi feita uma auditoria factual integral.', '',
        '## O que significa a janela de 5 horas', '',
        'A conta medida não retornou uma janela de 300 minutos: retornou uma janela semanal, sem janela secundária. Não existe base medida para dizer quantas perguntas consomem 1% de uma franquia de 5h desta conta. A documentação atual também informa que planos Pro não têm limite de cinco horas. A projeção acima de perguntas em 5h mede velocidade de processamento e não garante franquia disponível.', '',
        '## Conversão do consumo em capacidade', '',
    ]
    if delta:
        q=d['perguntas_por_janela_estimativa']; mensal=d['perguntas_por_mes_estimativa']
        linhas += [f'Estimativa central: {total} / {delta} = **{total/delta:g} perguntas por ponto percentual da janela medida**. Isso projeta **{q:.0f} perguntas por {janela_dias:g} dias**, ou **{mensal:.0f} por mês de 30 dias**.', '',
            f'Distribuindo a cota uniformemente pelo tempo, seriam **{d["media_sustentavel_por_5h_por_rateio_da_cota"]:.0f} perguntas a cada 5h em média**. Isso não cria nem representa uma franquia de 5h.', '',
            f'Com plena utilização dessa capacidade, o rateio do Codex seria **{brl(preco/mensal)} por pergunta**, e Codex + VPS seria **{brl((preco+vps)/mensal)} por pergunta**.', '',
            f'O painel tem resolução de 1 ponto percentual. A diferença real pode estar aproximadamente entre max(0, {delta}-1) e {delta}+1 pontos; não trate a estimativa central como capacidade contratual.']
    else:
        linhas += [f'O painel não mudou na resolução exibida. **0 ponto visível não significa consumo zero**. Não é possível calcular uma capacidade central dividindo {total} por zero.', '',
            f'Se a leitura foi atualizada, não houve uso externo nem reset e a medição inteira tem resolução de 1 ponto, o teste sugere consumo inferior a 1 ponto semanal para {total} perguntas. Sob essas condições e mantendo o mesmo padrão de consultas, isso indica **mais de {100*total:.0f} perguntas por semana**, sem permitir determinar o teto exato.', '',
            f'O rateio em plena utilização seria, condicionalmente, **inferior a {brl(d["custo_codex_por_pergunta_limite_superior_condicional"])} por pergunta**, usando um mês de 30 dias. Essa é uma desigualdade baseada na resolução do painel, não um custo unitário medido.']
    linhas += ['', '## Custo conforme o volume utilizado', '',
        f'Premissas herdadas do pitch: Codex = R$ {preco}/mês e VPS = R$ {vps}/mês. O tipo de plano retornado pela conta não revela o valor pago. Estes valores não foram confirmados em fatura. O custo unitário é rateio da assinatura; não é cobrança adicional por chamada.', '',
        '| Perguntas/mês | Só Codex | Codex + VPS |', '|---:|---:|---:|']
    for n in [1000,5000,13200]:
        linhas.append(f'| {n} | {brl(preco/n)} | {brl((preco+vps)/n)} |')
    linhas += ['', 'Fórmulas: perguntas por ponto = N / Δp; capacidade da janela = 100 × N / Δp; capacidade mensal = capacidade da janela × 30 / dias da janela; rateio unitário = custo mensal / perguntas efetivamente atendidas no mês. O cálculo de 5h por vazão usa N × 18.000 / tempo total em segundos.', '',
        '## Limites da medição', '',
        '- O limite é compartilhado com outros usos da conta. A variação antes/depois não isola eventuais sessões externas. Esta conversa também pode contribuir para o consumo compartilhado.',
        '- Percentual inteiro e eventual atraso de atualização limitam a precisão. Os snapshots completos e as notificações de limite estão preservados junto aos resultados.',
        '- Capacidade extrapolada depende de modelo, raciocínio, contexto, cache, ferramentas e distribuição das perguntas. Foram usados pedidos curtos e sem histórico de conversa.',
        '- Sucesso operacional significa resposta concluída e consulta à base; não equivale a uma auditoria factual integral. Conferências de hash validam a integridade do trecho, não a correção de toda a interpretação.',
        '- Não foram incluídos API oficial do WhatsApp, impostos, suporte ou equipe. As hipóteses mensais supõem disponibilidade e uso da capacidade; o notebook e três consultas simultâneas não validam uma VPS específica.',
        '- Tentativas de configuração anteriores foram descartadas: uma falhou antes de chamar o modelo, uma foi recusada por incompatibilidade do CLI antigo e duas não conseguiram consultar o MCP. O baseline desta rodada foi capturado depois delas.', '',
        'Fontes: [limites e preços do Codex](https://learn.chatgpt.com/docs/pricing) e [protocolo do App Server](https://learn.chatgpt.com/docs/app-server). Os snapshots observados desta conta prevalecem para a descrição da janela efetivamente medida.', '',
        'Dados brutos e perguntas reais ficam em `dados/bench/`, ignorados pelo Git. Este relatório não inclui dados pessoais nem credenciais.', '']
    args.relatorio.write_text('\n'.join(linhas))
    print(json.dumps(d,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
