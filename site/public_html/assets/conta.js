// Página "Minha conta": dados, plano, telefones do WhatsApp e o token MCP com o guia para conectar o Claude ou o Codex.
(() => {
  'use strict'
  const { el, formatarTelefone, dataHora, nomesDosEntes } = window.U
  const $ = s => document.querySelector(s)
  const ATUALIZAR_MS = 10000     // atualiza bloqueios e liberações sem recarregar a página
  const STATUS = {
    aprovado: ['Liberado', 'Número liberado. O acesso ao assistente no WhatsApp é atualizado em até 15 segundos.'],
    revogado: ['Bloqueado', 'O administrador bloqueou este número.'],
  }

  let confirmando = null          // id do telefone que está esperando a confirmação de remoção
  let temporizador = null

  const mostrar = (id, sim) => { $(id).hidden = !sim }
  function mensagem(id, texto) { $(id).textContent = texto || ''; mostrar(id, !!texto) }
  function limparMensagens() { mensagem('#erro-tel', ''); mensagem('#ok-tel', '') }

  // ---------- dados e plano ----------
  function desenharDados(me) {
    $('#dado-nome').textContent = me.usuario.nome
    $('#dado-email').textContent = me.usuario.email
    $('#dado-verificacao').textContent = me.usuario.email_verificado ? 'E-mail verificado' : 'E-mail não verificado'
    $('#verificar-agora').hidden = me.usuario.email_verificado
    $('#dado-plano').textContent = me.plano ? me.plano.nome : 'Sem plano ativo'
    $('#dado-entes').textContent = me.plano ? nomesDosEntes(me.plano.tenants) : 'Nada ainda: abra o assistente para ativar o acesso.'
  }

  // ---------- telefones ----------
  function itemDoTelefone(t) {
    const li = el('li', 'item')
    const [rotulo, explicacao] = STATUS[t.status] || [t.status, '']
    const principal = el('div', 'principal')
    principal.append(el('span', 'status ' + t.status, rotulo), el('div', 'numero', formatarTelefone(t.numero)), el('div', 'detalhe', explicacao))
    const criado = dataHora(t.criado_em)
    if (criado) principal.append(el('div', 'detalhe', 'Cadastrado em ' + criado))

    const acoes = el('div', 'acoes-item')
    const remover = el('button', 'botao pequeno perigo', confirmando === t.id ? 'Confirmar remoção' : 'Remover')
    remover.type = 'button'
    remover.setAttribute('aria-label', (confirmando === t.id ? 'Confirmar a remoção do telefone ' : 'Remover o telefone ') + formatarTelefone(t.numero))
    remover.addEventListener('click', () => removerTelefone(t, remover))
    acoes.append(remover)
    li.append(principal, acoes)
    return li
  }

  async function carregarTelefones() {
    let lista
    try {
      lista = await Api.telefones()
    } catch (e) {
      if (e.status === 401) { location.replace('chat.html'); return }
      mensagem('#erro-tel', e.message)
      return
    }
    // Não redesenha no meio de uma confirmação de remoção.
    if (confirmando === null) {
      $('#lista-tel').replaceChildren(...lista.map(itemDoTelefone))
      mostrar('#vazio-tel', lista.length === 0)
    }
  }

  async function removerTelefone(t, botao) {
    limparMensagens()
    if (confirmando !== t.id) {
      // Remover um número tira o acesso: pede um segundo clique.
      confirmando = t.id
      botao.textContent = 'Confirmar remoção'
      setTimeout(() => { if (confirmando === t.id) { confirmando = null; botao.textContent = 'Remover' } }, 5000)
      return
    }
    botao.disabled = true
    try {
      await Api.removerTelefone(t.id)
      confirmando = null
      mensagem('#ok-tel', 'Telefone removido.')
    } catch (e) {
      confirmando = null
      mensagem('#erro-tel', e.message)
    }
    await carregarTelefones()
  }

  async function cadastrarTelefone(e) {
    e.preventDefault()
    limparMensagens()
    const campo = $('#tel-numero'), botao = $('#tel-enviar')
    if (!campo.value.trim()) { mensagem('#erro-tel', 'Informe o celular com DDD, como (87) 99999-9999.'); campo.focus(); return }
    botao.disabled = true
    try {
      const novo = await Api.cadastrarTelefone(campo.value)
      campo.value = ''
      mensagem('#ok-tel', `Telefone ${formatarTelefone(novo.numero)} cadastrado e liberado. O acesso ao WhatsApp será atualizado em até 15 segundos.`)
    } catch (e2) {
      mensagem('#erro-tel', e2.message)
    } finally {
      botao.disabled = false
    }
    await carregarTelefones()
  }

  // ---------- MCP: token e guia de instalação ----------
  let mcpUrl = ''
  let tokenNovo = null            // { id, token }: só existe logo depois de gerar; não volta do servidor
  let confirmandoMcp = null
  function mensagemMcp(erro, ok) { mensagem('#erro-mcp', erro); mensagem('#ok-mcp', ok) }

  function comandos(token) {
    const t = token || 'SEU_TOKEN', url = mcpUrl
    // O --header do Claude Code aceita vários valores: precisa vir depois do nome e do endereço, senão os engole.
    const claude = `claude mcp add --transport http --scope user fornexia ${url} --header "Authorization: Bearer ${t}"`
    const codex = `codex mcp add fornexia --url ${url} --bearer-token-env-var FORNEXIA_TOKEN`
    return {
      claude,
      codex: `export FORNEXIA_TOKEN="${t}"\n${codex}`,
      agente: [
        'Instale o servidor MCP remoto do FornexIA neste computador.',
        '- Nome: fornexia',
        `- Endereço (HTTP streamable): ${url}`,
        `- Autenticação: cabeçalho Authorization: Bearer ${t}`,
        '',
        `Se você é o Claude Code, rode: ${claude}`,
        `Se você é o Codex, grave a variável de ambiente FORNEXIA_TOKEN com o token (no ~/.bashrc ou ~/.zshrc; no Windows, com setx) e rode: ${codex}`,
        '',
        'Depois, confirme que o fornexia aparece na lista de servidores MCP, chame a ferramenta "cobertura" dele e me diga quais entes e datas a base cobre.',
        'Não grave o token em nenhum arquivo de projeto nem em repositório.',
      ].join('\n'),
    }
  }

  function desenharGuia() {
    const c = comandos(tokenNovo && tokenNovo.token)
    $('#cmd-claude').textContent = c.claude
    $('#cmd-codex').textContent = c.codex
    $('#cmd-agente').textContent = c.agente
    $('#mcp-url').textContent = mcpUrl
    $('#guia-dica').textContent = tokenNovo
      ? 'Os comandos abaixo já estão com o seu token novo.'
      : 'Gere um token: os comandos abaixo saem preenchidos com ele. Sem token, eles mostram SEU_TOKEN no lugar.'
  }

  function itemDoToken(t) {
    const li = el('li', 'item')
    const principal = el('div', 'principal')
    principal.append(el('span', 'status aprovado', 'Ativo'), el('div', 'numero', `Token ${t.prefixo}…`))
    const criado = dataHora(t.criado_em)
    if (criado) principal.append(el('div', 'detalhe', 'Gerado em ' + criado))
    const acoes = el('div', 'acoes-item')
    const revogar = el('button', 'botao pequeno perigo', confirmandoMcp === t.id ? 'Confirmar revogação' : 'Revogar')
    revogar.type = 'button'
    revogar.setAttribute('aria-label', (confirmandoMcp === t.id ? 'Confirmar a revogação do token ' : 'Revogar o token ') + t.prefixo)
    revogar.addEventListener('click', () => revogarToken(t, revogar))
    acoes.append(revogar)
    li.append(principal, acoes)
    return li
  }

  async function carregarMcp() {
    let dados
    try {
      dados = await Api.mcp()
    } catch (e) {
      if (e.status === 401) { location.replace('chat.html'); return }
      mensagemMcp(e.message, '')
      return
    }
    mcpUrl = dados.url
    desenharGuia()
    if (confirmandoMcp === null) {
      $('#lista-mcp').replaceChildren(...dados.tokens.map(itemDoToken))
      mostrar('#vazio-mcp', dados.tokens.length === 0)
    }
    $('#mcp-gerar').disabled = dados.tokens.length >= dados.limite
  }

  async function gerarToken() {
    mensagemMcp('', '')
    const botao = $('#mcp-gerar')
    botao.disabled = true
    try {
      const novo = await Api.gerarTokenMcp()
      tokenNovo = { id: novo.id, token: novo.token }
      mcpUrl = novo.url
      $('#mcp-token').textContent = novo.token
      mostrar('#mcp-novo', true)
      mensagemMcp('', 'Token gerado. Ele passa a funcionar em até 15 segundos.')
    } catch (e) {
      mensagemMcp(e.message, '')
    }
    await carregarMcp()
  }

  async function revogarToken(t, botao) {
    mensagemMcp('', '')
    if (confirmandoMcp !== t.id) {
      // Revogar corta o acesso da IA que usa o token: pede um segundo clique.
      confirmandoMcp = t.id
      botao.textContent = 'Confirmar revogação'
      setTimeout(() => { if (confirmandoMcp === t.id) { confirmandoMcp = null; botao.textContent = 'Revogar' } }, 5000)
      return
    }
    botao.disabled = true
    try {
      await Api.revogarTokenMcp(t.id)
      if (tokenNovo && tokenNovo.id === t.id) { tokenNovo = null; mostrar('#mcp-novo', false); $('#mcp-token').textContent = '' }
      mensagemMcp('', 'Token revogado. O acesso cai em até 15 segundos.')
    } catch (e) {
      mensagemMcp(e.message, '')
    }
    confirmandoMcp = null
    await carregarMcp()
  }

  function trocarAba(aba) {
    document.querySelectorAll('[aria-labelledby="t-mcp"] [role="tab"]').forEach(b => {
      const sim = b === aba
      b.setAttribute('aria-selected', String(sim))
      $('#' + b.getAttribute('aria-controls')).hidden = !sim
    })
  }

  async function copiar(botao) {
    const texto = $(botao.dataset.copiar).textContent
    const original = botao.textContent
    try {
      await navigator.clipboard.writeText(texto)
      botao.textContent = 'Copiado'
    } catch {
      // Sem acesso à área de transferência: seleciona o texto para a pessoa copiar com Ctrl+C.
      const faixa = document.createRange()
      faixa.selectNodeContents($(botao.dataset.copiar))
      const sel = getSelection(); sel.removeAllRanges(); sel.addRange(faixa)
      botao.textContent = 'Selecionado: use Ctrl+C'
    }
    setTimeout(() => { botao.textContent = original }, 2500)
  }

  // ---------- início ----------
  async function iniciar() {
    let me
    try {
      me = await Api.me()
    } catch (e) {
      $('#carregando').textContent = e.message
      return
    }
    if (!me.usuario) { location.replace('chat.html'); return }
    if (!me.plano) me.plano = await Api.garantirPlano()   // sem ele o cadastro de telefone é recusado
    Topo.montar(me.usuario, 'conta')
    desenharDados(me)
    mostrar('#carregando', false)
    mostrar('#pagina', true)
    await Promise.all([carregarTelefones(), carregarMcp()])
    temporizador = setInterval(() => { if (document.visibilityState === 'visible') carregarTelefones() }, ATUALIZAR_MS)
  }

  $('#form-tel').addEventListener('submit', cadastrarTelefone)
  $('#mcp-gerar').addEventListener('click', gerarToken)
  document.querySelectorAll('[aria-labelledby="t-mcp"] [role="tab"]').forEach(b => b.addEventListener('click', () => trocarAba(b)))
  document.querySelectorAll('[data-copiar]').forEach(b => b.addEventListener('click', () => copiar(b)))
  $('#verificar-agora').addEventListener('click', async e => {
    e.target.disabled = true
    const status = $('#verificacao-status')
    try { status.textContent = (await Api.verificarConta()).mensagem; e.target.hidden = true }
    catch (erro) { status.textContent = erro.message }
    finally { status.hidden = false; e.target.disabled = false }
  })
  iniciar()
})()
