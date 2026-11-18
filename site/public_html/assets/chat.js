// Página do assistente: conta, plano e chat. Tudo que vem do servidor entra na tela por textContent,
// nunca por innerHTML, então um texto malicioso não executa nada.
(() => {
  'use strict'
  // Dentro do painel da página inicial, a página se ajusta ao espaço pequeno.
  if (/[?&]embutido\b/.test(location.search) || window.self !== window.top) document.documentElement.classList.add('embutido')
  const $ = s => document.querySelector(s)
  const ENTES = { 'pe-garanhuns': 'Município de Garanhuns', 'pe-estado': 'Estado de Pernambuco', 'br-uniao': 'União (governo federal)' }
  const ROTULOS = {
    cobertura: 'Verificando o que a base cobre',
    buscar_fornecedor: 'Procurando o fornecedor',
    listar_contratos: 'Listando contratos',
    buscar_contratos: 'Buscando contratos',
    execucao_do_fornecedor: 'Consultando valores pagos',
    contratos_do_fornecedor: 'Consultando os contratos do fornecedor',
    sancoes_do_fornecedor: 'Consultando sanções',
    cadastro_do_fornecedor: 'Consultando o cadastro da empresa',
    conferir_evidencia: 'Conferindo a fonte',
  }
  const SUGESTOES = [
    'Quais contratos temos na base?',
    'Algum fornecedor tem sanção em aberto?',
    'A base de dados é completa?',
  ]
  // Demonstração livre: a conta nova recebe o plano único sem etapa de escolha.
  // A regra de plano continua valendo no servidor. Ligue isto para voltar a pedir a escolha na tela.
  const ESCOLHER_PLANO = false
  const INTERVALO_MS = 700          // o plano pede leitura a cada 0,7 s
  const LIMITE_MS = 130000          // RF-14: depois disso, mensagem legível
  const ESTADOS_FINAIS = ['concluida', 'erro']

  const estado = { usuario: null, plano: null, acompanhando: false, sessao: 0 }
  const embutido = document.documentElement.classList.contains('embutido')

  // ---------- mapa da consulta (grafo.js): acende o caminho que cada pergunta percorreu na base ----------
  const SEM_MAPA = { novaPergunta() {}, consulta() {}, fonte() {}, texto() {}, fim() {}, erro() {}, reiniciar() {} }
  let mapa = SEM_MAPA, entesDoMapa = ''
  const plural = (n, um, varios) => n + ' ' + (n === 1 ? um : varios)
  function montarMapa() {
    if (embutido || !window.MapaConsulta || !estado.plano) return
    const entes = (estado.plano.tenants || []).join(',')
    if (mapa !== SEM_MAPA && entes === entesDoMapa) return
    entesDoMapa = entes
    $('#mapa-area').replaceChildren()
    mapa = window.MapaConsulta.criar($('#mapa-area'), {
      entes: estado.plano.tenants || [],
      aoMudar: n => {
        $('#mapa-perguntas').textContent = plural(n.perguntas, 'pergunta', 'perguntas')
        $('#mapa-nos').textContent = plural(n.nos, 'nó', 'nós')
        $('#mapa-provas').textContent = plural(n.provas, 'prova', 'provas')
      },
    })
  }
  const CHAVE_MAPA = 'fornexia-mapa'
  function mostrarMapa(sim, guardar) {
    const painel = $('#mapa-consulta'), botao = $('#alternar-mapa')
    painel.classList.toggle('fechado', !sim)
    painel.inert = !sim
    $('#caixa-conversa').classList.toggle('larga', !sim)
    botao.setAttribute('aria-expanded', String(sim))
    botao.querySelector('span').textContent = sim ? 'Ocultar mapa' : 'Mostrar mapa'
    if (guardar) try { localStorage.setItem(CHAVE_MAPA, sim ? 'aberto' : 'fechado') } catch { /* sem armazenamento: vale só nesta página */ }
  }
  const mapaGuardado = () => { try { return localStorage.getItem(CHAVE_MAPA) !== 'fechado' } catch { return true } }

  const esperar = ms => new Promise(r => setTimeout(r, ms))
  const el = (tag, classe, texto) => {
    const e = document.createElement(tag)
    if (classe) e.className = classe
    if (texto !== undefined) e.textContent = texto
    return e
  }
  const mostrar = (id, sim) => { $(id).hidden = !sim }
  const nomeDoEnte = id => ENTES[id] || id
  const juntar = nomes => nomes.length > 1 ? nomes.slice(0, -1).join(', ') + ' e ' + nomes[nomes.length - 1] : nomes.join('')     // A, B e C
  const dinheiro = n => n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 0 })

  // ---------- telas ----------
  function tela(nome) {
    for (const t of ['carregando', 'entrar', 'plano', 'chat']) mostrar('#tela-' + t, t === nome)
    document.body.classList.toggle('modo-chat', nome === 'chat')
    mostrar('#topo-acoes', !!estado.usuario)
    mostrar('#topo-links', !!estado.usuario)
    $('#link-admin').hidden = !(estado.usuario && estado.usuario.papel === 'admin')
    if (estado.usuario) $('#quem').textContent = estado.usuario.nome + (ESCOLHER_PLANO && estado.plano ? ' · plano ' + estado.plano.nome : '')
  }

  function erroEm(id, mensagem) {
    const e = $(id)
    e.textContent = mensagem || ''
    e.hidden = !mensagem
  }

  function aplicarConta(dados) {
    estado.usuario = dados.usuario || null
    estado.plano = dados.plano || null
  }

  async function decidirTela() {
    if (!estado.usuario) { tela('entrar'); return }
    if (!estado.plano) {
      if (!ESCOLHER_PLANO && await ativarPlanoPadrao()) { await abrirChat(); return }
      await mostrarPlanos()   // escolha manual, ou saída de emergência se a ativação automática falhar
      return
    }
    await abrirChat()
  }

  // Sem pedir nada, a conta recebe o plano único. Se algo falhar, cai na escolha manual.
  async function ativarPlanoPadrao() {
    const plano = await Api.garantirPlano()
    if (!plano) return false
    estado.plano = plano
    return true
  }

  // ---------- plano no chat ----------
  function mostrarPlanoAtual() {
    $('#plano-info').textContent = juntar(estado.plano.tenants.map(nomeDoEnte))
  }

  // ---------- entrar e criar conta ----------
  async function receberGoogle(resposta) {
    try {
      erroEm('#erro-entrar', ''); erroEm('#erro-cadastro', '')
      aplicarConta(await Api.entrarGoogle(resposta.credential))
      await decidirTela()
    } catch (e) {
      erroEm($('#form-entrar').hidden ? '#erro-cadastro' : '#erro-entrar', e.message)
    }
  }

  // O botão é desenhado pelo Google dentro de um iframe: só aceita tema, formato e largura (máx. 400 px). Por isso ele é
  // redesenhado no tema atual do site (claro/escuro), na largura do cartão e sempre que a aba ou a janela mudam.
  let googlePronto = false
  const temaEscuro = () => (document.documentElement.dataset.tema || (matchMedia('(prefers-color-scheme: light)').matches ? 'claro' : 'escuro')) === 'escuro'

  function desenharGoogle() {
    if (!googlePronto) return
    for (const bloco of document.querySelectorAll('.acesso-google')) {
      const alvo = bloco.querySelector('.botao-google')
      const largura = Math.max(200, Math.min(400, Math.floor(alvo.clientWidth) || 320))   // formulário escondido mede 0: usa 320 e redesenha ao abrir a aba
      alvo.replaceChildren()
      alvo.classList.toggle('escuro', temaEscuro())      // o botão escuro não tem borda: pode ganhar o canto arredondado dos botões do site
      google.accounts.id.renderButton(alvo, {
        type: 'standard', theme: temaEscuro() ? 'filled_black' : 'outline', size: 'large', shape: 'rectangular',
        text: 'continue_with', logo_alignment: 'center', locale: 'pt-BR', width: largura,
      })
    }
  }

  function prepararGoogle(clientId) {
    if (!clientId) return
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = () => {
      if (!window.google?.accounts?.id) return
      google.accounts.id.initialize({ client_id: clientId, callback: receberGoogle, auto_select: false })
      googlePronto = true
      for (const bloco of document.querySelectorAll('.acesso-google')) bloco.hidden = false
      desenharGoogle()
      let espera
      window.addEventListener('tema', desenharGoogle)
      window.addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(desenharGoogle, 150) })
    }
    script.onerror = () => { /* acesso por e-mail e senha permanece disponível */ }
    document.head.append(script)
  }

  function trocarAba(qual) {
    const entrar = qual === 'entrar'
    $('#aba-entrar').setAttribute('aria-selected', String(entrar))
    $('#aba-cadastro').setAttribute('aria-selected', String(!entrar))
    mostrar('#form-entrar', entrar)
    mostrar('#form-cadastro', !entrar)
    erroEm('#erro-entrar', ''); erroEm('#erro-cadastro', '')
    requestAnimationFrame(desenharGoogle)     // a aba que abriu agora passa a ter largura medida
  }

  async function enviarForm(form, botaoTexto, erroId, acao) {
    if (!form.reportValidity()) return
    const botao = form.querySelector('button[type=submit]')
    erroEm(erroId, '')
    botao.disabled = true
    try {
      const dados = await acao()
      if (form.id === 'form-cadastro') {
        form.reset()
        $('#cadastro-status').textContent = dados.mensagem
        mostrar('#cadastro-status', true)
        mostrar('#cadastro-reenvio', true)
        trocarAba('entrar')
        return
      }
      aplicarConta(dados)
      form.reset()
      await decidirTela()
    } catch (e) {
      erroEm(erroId, e.message)
    } finally {
      botao.disabled = false
    }
  }

  // ---------- planos ----------
  async function mostrarPlanos() {
    tela('plano')
    erroEm('#erro-plano', '')
    const lista = $('#lista-planos')
    lista.replaceChildren()
    try {
      const planos = await Api.planos()
      for (const p of planos) {
        const cartao = el('div', 'plano')
        cartao.append(el('h3', '', p.nome))
        const preco = el('p', 'preco', dinheiro(p.preco_mensal) + ' ')
        preco.append(el('small', '', '/ mês'))
        cartao.append(preco)
        const ul = el('ul')
        if (p.franquia > 0) ul.append(el('li', '', p.franquia.toLocaleString('pt-BR') + ' perguntas por mês'))
        if (p.preco_excedente > 0) ul.append(el('li', '', 'Excedente: ' + p.preco_excedente.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) + ' por pergunta'))
        ul.append(el('li', '', 'Consulta: ' + juntar(p.tenants.map(nomeDoEnte))))
        cartao.append(ul)
        const b = el('button', 'botao cheio', 'Ativar plano de demonstração')
        b.type = 'button'
        b.addEventListener('click', () => ativarPlano(p.id, b))
        cartao.append(b)
        lista.append(cartao)
      }
    } catch (e) {
      erroEm('#erro-plano', e.message)
    }
  }

  async function ativarPlano(id, botao) {
    erroEm('#erro-plano', '')
    botao.disabled = true
    try {
      const r = await Api.ativarPlano(id)
      estado.plano = r.plano
      await abrirChat()
    } catch (e) {
      erroEm('#erro-plano', e.message)
      botao.disabled = false
    }
  }

  // ---------- chat ----------
  function boasVindas() {
    const conversa = $('#conversa')
    conversa.replaceChildren()
    const w = el('div', 'boas-vindas')
    w.append(el('h2', '', 'Como posso ajudar?'))
    const comMapa = !embutido && window.matchMedia && window.matchMedia('(min-width: 981px)').matches
    w.append(el('p', 'apoio', 'Pergunte sobre fornecedores. Cada resposta traz a fonte, com o trecho do portal.' + (comMapa ? ' O mapa ao lado mostra o caminho da consulta na base.' : '')))
    conversa.append(w)
  }

  // As sugestões ficam numa linha acima do campo, à vista durante toda a conversa.
  function montarSugestoes() {
    const lista = $('#sugestoes')
    if (lista.children.length) return
    for (const s of SUGESTOES) {
      const b = el('button', 'sugestao', s)
      b.type = 'button'
      b.addEventListener('click', () => { $('#pergunta').value = s; atualizarContador(); enviarPergunta() })
      lista.append(b)
    }
  }

  async function abrirChat() {
    tela('chat')
    mostrarPlanoAtual()
    montarSugestoes()
    montarMapa()
    if (!embutido) mostrarMapa(mapaGuardado(), false)
    travarEntrada(false)
    boasVindas()
    atualizarContador()
    // Se a pergunta anterior ainda está em andamento (a página foi recarregada), volta a acompanhá-la.
    try {
      const { pergunta } = await Api.perguntaAberta()
      if (pergunta) { retomar(pergunta); return }
    } catch (e) {
      if (e.status === 401) { estado.usuario = null; tela('entrar') }
    }
    $('#pergunta').focus()
  }

  function noFim(conversa) {
    return conversa.scrollHeight - conversa.scrollTop - conversa.clientHeight < 80
  }

  function adicionarPergunta(texto) {
    const conversa = $('#conversa')
    conversa.querySelector('.boas-vindas')?.remove()
    conversa.append(el('div', 'msg eu', texto))
    conversa.scrollTop = conversa.scrollHeight
    mapa.novaPergunta()
  }

  function criarResposta() {
    const raiz = el('div', 'msg bot')
    const progresso = el('div', 'progresso')
    const pontos = el('span', 'pontos'); pontos.append(el('i'), el('i'), el('i'))
    const rotulo = el('span', '', 'Enviando sua pergunta…')
    progresso.append(pontos, rotulo)
    const texto = el('div', 'texto-resp')
    const fontes = el('div', 'fontes')
    raiz.append(el('div', 'marca-ia', 'Escrito pela IA'), progresso, texto, fontes)
    $('#conversa').append(raiz)
    return { raiz, progresso, rotulo, texto, fontes, nFontes: 0 }
  }

  const dataBR = iso => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || ''); return m ? `${m[3]}/${m[2]}/${m[1]}` : '' }
  const urlSegura = u => (typeof u === 'string' && /^https?:\/\//i.test(u)) ? u : null   // nunca javascript:

  // Cada fonte é um cartão: o trecho literal do portal, a data da captura e se o hash do arquivo guardado conferiu agora.
  function adicionarFonte(resp, d) {
    resp.nFontes++
    const cartao = el('div', 'fonte-card')
    const cabeca = el('div', 'fonte-cabeca')
    cabeca.append(el('span', '', 'Fonte ' + resp.nFontes))
    cabeca.append(d.hash_confere ? el('span', 'selo-hash', 'hash confere') : el('span', 'selo-hash sem', 'hash não conferido'))
    cartao.append(cabeca)
    cartao.append(el('p', 'fonte-trecho', '“' + String(d.trecho || 'Trecho não informado.') + '”'))
    const meta = el('div', 'fonte-meta')
    const partes = []
    if (d.capturado_em) partes.push('Capturado em ' + dataBR(String(d.capturado_em)))
    if (d.evidencia) partes.push('evidência ' + d.evidencia)
    meta.append(partes.join(' · '))
    const url = urlSegura(d.url)
    if (url) {
      if (partes.length) meta.append(' · ')
      const a = el('a', '', 'Abrir no portal')
      a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'
      meta.append(a)
    }
    cartao.append(meta)
    resp.fontes.append(cartao)
  }

  // Pacote de prova: um ZIP que um terceiro reconfere sem acesso ao sistema. É um link comum; o navegador já manda a sessão.
  function adicionarExportar(resp) {
    if (!resp.id || resp.raiz.querySelector('.exportar')) return
    const a = el('a', 'exportar', 'Exportar prova')
    a.href = '/api/perguntas/' + encodeURIComponent(resp.id) + '/prova'
    a.setAttribute('download', '')
    a.title = 'Baixa a pergunta, a resposta e os trechos da fonte, com os hashes para conferir por fora'
    resp.raiz.append(a)
  }

  // Rede de segurança caso o modelo ainda escreva markdown: tira os símbolos e mantém o texto (continua por textContent).
  // Vem do PR #3 (Isaac).
  const semMarkdown = (t) => t.replace(/\*\*|__/g, '').replace(/^#{1,6}\s+/gm, '')

  function aplicarEvento(ev, resp) {
    const d = ev.dados || {}
    switch (ev.tipo) {
      case 'consulta': {
        const nome = String(d.nome || '').replace(/^mcp__transparencia__/, '')
        resp.rotulo.textContent = (ROTULOS[nome] || 'Consultando a base') + '…'
        mapa.consulta(nome)
        break
      }
      case 'texto':
        if (typeof d.delta === 'string') {
          // O texto chega em pedaços e um ** pode vir partido; por isso a limpeza é refeita sobre o texto inteiro.
          resp.bruto = (resp.bruto || '') + d.delta
          resp.texto.textContent = semMarkdown(resp.bruto)
          mapa.texto()
        }
        break
      case 'fonte':
        adicionarFonte(resp, d)
        mapa.fonte(d)
        break
      case 'fim':
        resp.progresso.hidden = true
        adicionarExportar(resp)
        mapa.fim()
        break
      case 'erro':
        resp.progresso.hidden = true
        resp.raiz.append(el('p', 'erro-resp', typeof d.motivo === 'string' && d.motivo ? d.motivo : 'Não consegui concluir a consulta. Tente novamente.'))
        mapa.erro()
        break
    }
  }

  function travarEntrada(travada) {
    $('#pergunta').disabled = travada
    $('#enviar').disabled = travada
    document.querySelectorAll('.sugestao').forEach(b => { b.disabled = travada })
  }

  async function acompanhar(id) {
    const sessao = estado.sessao
    const resp = criarResposta()
    resp.id = id
    estado.acompanhando = true
    travarEntrada(true)
    const conversa = $('#conversa')
    const inicio = Date.now()
    let desde = 0, falhas = 0, terminou = false
    try {
      while (!terminou && sessao === estado.sessao) {
        if (Date.now() - inicio > LIMITE_MS) {
          aplicarEvento({ tipo: 'erro', dados: { motivo: 'A consulta demorou mais que o esperado. Tente novamente.' } }, resp)
          break
        }
        let dados
        try {
          dados = await Api.eventos(id, desde)
          falhas = 0
        } catch (e) {
          if (e.status === 401) { estado.usuario = null; tela('entrar'); return }
          if (e.status === 404) {
            aplicarEvento({ tipo: 'erro', dados: { motivo: 'Não encontrei essa pergunta. Tente novamente.' } }, resp)
            break
          }
          if (++falhas >= 5) {
            aplicarEvento({ tipo: 'erro', dados: { motivo: 'Perdi a conexão com o serviço. Tente novamente.' } }, resp)
            break
          }
          await esperar(INTERVALO_MS * falhas)
          continue
        }
        if (dados.status === 'fila' && dados.fila > 1) resp.rotulo.textContent = `Você é o ${dados.fila}º da fila…`
        else if (dados.status === 'processando' && !dados.eventos.length && resp.rotulo.textContent.includes('da fila')) resp.rotulo.textContent = 'Consultando a base…'
        const seguir = noFim(conversa)
        for (const ev of dados.eventos) {
          desde = ev.seq
          aplicarEvento(ev, resp)
          if (ev.tipo === 'fim' || ev.tipo === 'erro') terminou = true
        }
        if (ESTADOS_FINAIS.includes(dados.status)) {
          terminou = true
          if (!dados.eventos.some(e => e.tipo === 'fim' || e.tipo === 'erro')) resp.progresso.hidden = true
        }
        if (seguir) conversa.scrollTop = conversa.scrollHeight
        if (!terminou) await esperar(INTERVALO_MS)   // para de consultar assim que termina
      }
    } finally {
      estado.acompanhando = false
      resp.progresso.hidden = true
      if (sessao === estado.sessao) { travarEntrada(false); $('#pergunta').focus() }
    }
  }

  function retomar(pergunta) {
    $('#conversa').replaceChildren()
    adicionarPergunta(pergunta.texto)
    acompanhar(pergunta.id)
  }

  async function enviarPergunta() {
    if (estado.acompanhando) return
    const campo = $('#pergunta')
    const texto = campo.value.trim()
    if (!texto) return
    travarEntrada(true)
    try {
      const { id } = await Api.perguntar(texto)
      campo.value = ''
      atualizarContador()
      adicionarPergunta(texto)
      acompanhar(id)
    } catch (e) {
      travarEntrada(false)
      if (e.status === 401) { estado.usuario = null; tela('entrar'); return }
      if (e.status === 403 && /plano/i.test(e.message)) { estado.plano = null; await decidirTela(); return }
      if (e.status === 409 && e.dados && e.dados.pergunta_id) {
        // já havia uma em andamento: mostra e continua acompanhando
        const { pergunta } = await Api.perguntaAberta()
        if (pergunta) { retomar(pergunta); return }
      }
      const conversa = $('#conversa')
      conversa.querySelector('.boas-vindas')?.remove()
      const aviso = el('p', 'aviso-erro', e.message)
      aviso.setAttribute('role', 'alert')
      conversa.append(aviso)
      conversa.scrollTop = conversa.scrollHeight
    }
  }

  function atualizarContador() {
    const campo = $('#pergunta')
    const n = campo.value.length
    const c = $('#contador')
    c.textContent = n + '/500'
    c.classList.toggle('perto', n >= 450)
    campo.style.height = 'auto'
    campo.style.height = Math.min(campo.scrollHeight, 150) + 'px'
  }

  // ---------- eventos ----------
  $('#aba-entrar').addEventListener('click', () => trocarAba('entrar'))
  $('#aba-cadastro').addEventListener('click', () => trocarAba('cadastro'))
  if (location.hash === '#cadastro') trocarAba('cadastro')   // vindo do site institucional ("Criar conta"); quem já tem sessão vai direto ao chat (Rodrigo, b7dc44b)

  $('#form-entrar').addEventListener('submit', e => {
    e.preventDefault()
    enviarForm(e.target, 'Entrar', '#erro-entrar', () => Api.entrar($('#entrar-email').value, $('#entrar-senha').value))
  })
  $('#form-cadastro').addEventListener('submit', e => {
    e.preventDefault()
    enviarForm(e.target, 'Criar conta', '#erro-cadastro', () => Api.cadastrar($('#cad-nome').value, $('#cad-email').value, $('#cad-senha').value, $('#cad-confirmacao').value))
  })

  $('#sair').addEventListener('click', async () => {
    estado.sessao++   // interrompe qualquer acompanhamento em andamento
    try { await Api.sair() } catch { /* sai mesmo assim */ }
    estado.usuario = null; estado.plano = null
    mapa.reiniciar()
    tela('entrar')
    trocarAba('entrar')
  })

  $('#alternar-mapa').addEventListener('click', () => mostrarMapa($('#mapa-consulta').classList.contains('fechado'), true))

  $('#form-pergunta').addEventListener('submit', e => { e.preventDefault(); enviarPergunta() })
  $('#pergunta').addEventListener('input', atualizarContador)
  $('#pergunta').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); enviarPergunta() }
  })

  // ---------- início ----------
  Api.me().then(dados => { prepararGoogle(dados.google_client_id); aplicarConta(dados) }).then(decidirTela).catch(e => {
    tela('entrar')
    erroEm('#erro-entrar', e.message)
  })
})()
