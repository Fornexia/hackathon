// Mapa da consulta: acende, na ontologia da base, o caminho que a pergunta percorreu.
// Recebe os mesmos eventos que o chat recebe do worker (consulta, fonte, texto, fim, erro); nada é inventado aqui.
// O SVG é montado com createElementNS (sem innerHTML). Uso:
//   const mapa = MapaConsulta.criar(elemento, { entes: ['pe-estado', 'pe-garanhuns'], aoMudar: n => {...} })
//   mapa.novaPergunta(); mapa.consulta('sancoes_do_fornecedor'); mapa.fonte({ hash_confere: true }); mapa.texto(); mapa.fim()
(() => {
  'use strict'
  const NS = 'http://www.w3.org/2000/svg'

  // [x, y, raio, rótulo] numa área de 640 × 420
  const NOS = {
    P: [52, 210, 16, 'Pergunta'], F: [176, 210, 22, 'Fornecedor'],
    C: [310, 90, 14, 'Contrato'], S: [310, 170, 14, 'Sanção'], Cad: [310, 250, 14, 'Cadastro'], Pg: [310, 330, 14, 'Pagamentos'],
    L: [450, 42, 12, 'Licitação'], O: [450, 122, 12, 'Órgão'], Ev: [450, 290, 16, 'Evidência'],
    E1: [590, 72, 11, 'Estado de PE'], E2: [590, 132, 11, 'Garanhuns'], E3: [590, 192, 11, 'União'], R: [590, 330, 18, 'Resposta'],
  }
  // As relações da ontologia (esquema/neo4j.cypher), no sentido em que a consulta anda
  const ARESTAS = {
    pf: ['P', 'F'], pc: ['P', 'C'], fc: ['F', 'C'], fs: ['F', 'S'], fcad: ['F', 'Cad'], fpg: ['F', 'Pg'],
    cl: ['C', 'L'], co: ['C', 'O'], cev: ['C', 'Ev'], sev: ['S', 'Ev'], cadev: ['Cad', 'Ev'], pgev: ['Pg', 'Ev'],
    oe1: ['O', 'E1'], oe2: ['O', 'E2'], oe3: ['O', 'E3'], evr: ['Ev', 'R'],
  }
  const ENTE_NO = { 'pe-estado': 'E1', 'pe-garanhuns': 'E2', 'br-uniao': 'E3' }
  const ENTE_ARESTA = { E1: 'oe1', E2: 'oe2', E3: 'oe3' }
  const DADO_ARESTA = { C: 'cev', S: 'sev', Cad: 'cadev', Pg: 'pgev' }      // de qual nó a evidência foi aberta
  const PRECISA_FORNECEDOR = { contratos_do_fornecedor: 1, sancoes_do_fornecedor: 1, cadastro_do_fornecedor: 1, execucao_do_fornecedor: 1 }
  const FERRAMENTAS = {
    buscar_fornecedor: [{ no: ['F'], ar: ['pf'] }],
    listar_contratos: [{ no: ['C'], ar: ['pc'] }, { no: ['O', 'L'], ar: ['co', 'cl'] }],
    buscar_contratos: [{ no: ['C'], ar: ['pc'] }, { no: ['O', 'L'], ar: ['co', 'cl'] }],
    contratos_do_fornecedor: [{ no: ['C'], ar: ['fc'] }, { no: ['O', 'L'], ar: ['co', 'cl'] }],
    sancoes_do_fornecedor: [{ no: ['S'], ar: ['fs'] }],
    cadastro_do_fornecedor: [{ no: ['Cad'], ar: ['fcad'] }],
    execucao_do_fornecedor: [{ no: ['Pg'], ar: ['fpg'] }],
  }
  const PASSO_MS = 650          // intervalo mínimo entre dois passos: os eventos chegam em lotes a cada 0,7 s
  const LUZ_MS = 950            // quanto o pulso leva para percorrer uma ligação

  const calmo = () => !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  const svgEl = (tag, attrs) => {
    const e = document.createElementNS(NS, tag)
    for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v)
    return e
  }

  function criar(alvo, opcoes = {}) {
    const entes = (opcoes.entes || []).map(t => ENTE_NO[t]).filter(Boolean)
    const svg = svgEl('svg', { viewBox: '0 0 640 420', preserveAspectRatio: 'xMidYMid meet', role: 'img', class: 'mapa-svg' })
    const gBase = svgEl('g'), gLuz = svgEl('g')
    const arestas = {}, nos = {}
    for (const [k, [a, b]] of Object.entries(ARESTAS)) {
      const [x1, y1] = NOS[a], [x2, y2] = NOS[b]
      const p = { x1, y1, x2, y2, pathLength: 100 }
      arestas[k] = { base: svgEl('line', { ...p, class: 'aresta' }), luz: svgEl('line', { ...p, class: 'luz' }), estado: '' }
      gBase.append(arestas[k].base); gLuz.append(arestas[k].luz)
    }
    svg.append(gBase, gLuz)
    for (const [k, [x, y, r, rotulo]] of Object.entries(NOS)) {
      const g = svgEl('g', { class: 'no' })
      g.append(svgEl('circle', { class: 'onda', cx: x, cy: y, r }), svgEl('circle', { class: 'miolo', cx: x, cy: y, r }))
      if (k === 'Ev') g.append(svgEl('path', { class: 'check', d: `M${x - 7} ${y} l5 5 l9 -10` }))
      const t = svgEl('text', { class: 'rot', x, y: y + r + (r > 16 ? 20 : 18) })
      t.textContent = rotulo
      g.append(t)
      nos[k] = { g, estado: '' }
      svg.append(g)
    }
    // Entes fora do plano ficam tracejados: o mapa mostra também o que a pessoa não enxerga.
    if (entes.length) for (const e of ['E1', 'E2', 'E3']) if (!entes.includes(e)) { nos[e].g.classList.add('fora'); arestas[ENTE_ARESTA[e]].base.classList.add('fora') }
    alvo.append(svg)

    const s = { perguntas: 0, provas: 0, fila: [], timer: null, ultimo: 0, desta: new Set(), escreveu: false, provaDesta: false }

    function pintarNo(k, estado) {
      const n = nos[k]
      if (!n || n.estado === estado) return
      n.estado = estado
      const fora = n.g.classList.contains('fora')
      n.g.setAttribute('class', 'no' + (estado ? ' ' + estado : '') + (fora ? ' fora' : ''))
    }
    function pintarAresta(k, estado) {
      const a = arestas[k]
      if (!a) return
      a.estado = estado
      const fora = a.base.classList.contains('fora')
      a.base.setAttribute('class', 'aresta' + (estado === 'corre' || estado === 'feito' ? ' feito' : estado ? ' ' + estado : '') + (fora ? ' fora' : ''))
      a.luz.setAttribute('class', 'luz' + (k === 'evr' ? ' violeta' : ''))
      if (estado === 'corre' && !calmo()) {
        void a.luz.getBoundingClientRect()      // recomeça a animação do pulso
        a.luz.setAttribute('class', 'luz corre' + (k === 'evr' ? ' violeta' : ''))
        setTimeout(() => { if (a.estado === 'corre') pintarAresta(k, 'feito') }, LUZ_MS)
      }
    }
    function avisar() {
      const acesos = Object.keys(nos).filter(k => nos[k].estado)
      svg.setAttribute('aria-label', 'Mapa da consulta. Nós acesos: ' + (acesos.length ? acesos.map(k => NOS[k][3]).join(', ') : 'nenhum ainda') + '.')
      if (opcoes.aoMudar) opcoes.aoMudar({ perguntas: s.perguntas, nos: acesos.length, provas: s.provas })
    }

    function aplicar(p) {
      for (const [k, n] of Object.entries(nos)) if (n.estado === 'ativo') pintarNo(k, 'visto')
      for (const k of p.no || []) {
        pintarNo(k, k === 'R' ? 'ia' : (k === 'Ev' && p.prova) || (k === 'Ev' && s.provaDesta) ? 'prova' : 'ativo')
      }
      for (const k of p.ar || []) pintarAresta(k, 'corre')
      if (p.fim) for (const [k, n] of Object.entries(nos)) if (n.estado === 'ativo') pintarNo(k, 'visto')
      avisar()
    }
    function andar() {
      s.timer = null
      if (!s.fila.length) return
      aplicar(s.fila.shift())
      s.ultimo = Date.now()
      if (s.fila.length) s.timer = setTimeout(andar, calmo() ? 0 : PASSO_MS)
    }
    function enfileirar(...passos) {
      for (const p of passos) for (const k of p.no || []) s.desta.add(k)     // o que esta pergunta já percorreu ou vai percorrer
      s.fila.push(...passos)
      if (s.timer) return
      const espera = calmo() ? 0 : Math.max(0, PASSO_MS - (Date.now() - s.ultimo))
      s.timer = setTimeout(andar, espera)
    }
    function despejar() {          // aplica na hora o que estava na fila (pergunta nova chegou antes)
      clearTimeout(s.timer); s.timer = null
      while (s.fila.length) aplicar(s.fila.shift())
    }

    const api = {
      novaPergunta() {
        despejar()
        for (const [k, n] of Object.entries(nos)) if (n.estado && n.estado !== 'prova') pintarNo(k, 'antigo')
        for (const [k, a] of Object.entries(arestas)) if (a.estado) pintarAresta(k, 'antigo')
        s.desta = new Set(); s.escreveu = false; s.provaDesta = false
        s.perguntas++
        enfileirar({ no: ['P'] })
      },
      consulta(nome) {
        nome = String(nome || '').replace(/^mcp__transparencia__/, '')
        if (nome === 'cobertura') {
          const alvo = entes.length ? entes : ['E1', 'E2']
          enfileirar({ no: ['F'], ar: ['pf'] }, { no: ['C', 'S', 'Cad', 'Pg'], ar: ['fc', 'fs', 'fcad', 'fpg'] },
            { no: ['L', 'O'], ar: ['cl', 'co'] }, { no: alvo, ar: alvo.map(e => ENTE_ARESTA[e]) })
          return
        }
        if (nome === 'conferir_evidencia') { api.fonte({}); return }
        const passos = FERRAMENTAS[nome]
        if (!passos) return
        if (PRECISA_FORNECEDOR[nome] && !s.desta.has('F')) enfileirar({ no: ['F'], ar: ['pf'] })
        enfileirar(...passos)
      },
      fonte(d) {
        const confere = !!(d && d.hash_confere)
        if (confere) { s.provas++; s.provaDesta = true }
        const de = Object.keys(DADO_ARESTA).filter(k => s.desta.has(k)).map(k => DADO_ARESTA[k])
        // A fonte pode chegar depois de a resposta começar a ser escrita: aí a ligação até a Resposta acende junto.
        enfileirar({ no: ['Ev'], ar: s.escreveu ? de.concat(['evr']) : de, prova: confere })
      },
      texto() {
        if (s.escreveu) return
        s.escreveu = true
        enfileirar({ no: ['R'], ar: s.desta.has('Ev') || s.provaDesta ? ['evr'] : [] })
      },
      fim() { enfileirar({ fim: true }) },
      erro() { enfileirar({ fim: true }) },
      reiniciar() {
        clearTimeout(s.timer); s.timer = null; s.fila = []
        for (const k of Object.keys(nos)) pintarNo(k, '')
        for (const k of Object.keys(arestas)) pintarAresta(k, '')
        Object.assign(s, { perguntas: 0, provas: 0, desta: new Set(), escreveu: false, provaDesta: false })
        avisar()
      },
    }
    avisar()
    return api
  }

  window.MapaConsulta = { criar }
})()
