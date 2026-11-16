// Os links mantêm o segredo no fragmento, fora dos logs HTTP. Nenhum GET consome o token.
(() => {
  'use strict'
  const $ = id => document.getElementById(id)
  let modo = 'recuperar'
  let token = ''
  function configurar() {
    const fragmento = location.hash.slice(1)
    const link = /^(verificar|redefinir)=([a-f0-9]{64})$/.exec(fragmento)
    modo = link ? link[1] : fragmento === 'reenviar' ? 'reenviar' : 'recuperar'
    token = link ? link[2] : ''
    if (link) history.replaceState(null, '', location.pathname)
    $('status').hidden = $('erro').hidden = true
    $('form-acesso').hidden = false
    $('form-acesso').reset()
    const pedirEmail = !link
    $('campo-email').hidden = !pedirEmail
    $('email').disabled = !pedirEmail
    $('campos-senha').hidden = modo !== 'redefinir'
    for (const id of ['senha', 'confirmacao']) {
      $(id).disabled = modo !== 'redefinir'
      $(id).required = modo === 'redefinir'
    }
    const textos = {
      recuperar: ['Recuperar senha', 'Informe o e-mail da sua conta para receber as instruções.', 'Enviar instruções'],
      reenviar: ['Verificar e-mail', 'Informe o Gmail usado no cadastro para receber um novo link.', 'Reenviar verificação'],
      verificar: ['Confirmar e-mail', 'Confirme abaixo a verificação do seu endereço no FORNEX.', 'Verificar meu e-mail'],
      redefinir: ['Criar nova senha', 'Depois da alteração, todas as sessões anteriores serão encerradas.', 'Salvar nova senha'],
    }
    ;[$('titulo').textContent, $('descricao').textContent, $('confirmar').textContent] = textos[modo]
    if (!link && /^(verificar|redefinir)/.test(fragmento)) {
      $('erro').textContent = 'Link inválido. Solicite outro link de verificação ou recuperação.'
      $('erro').hidden = false
    }
  }
  configurar()
  window.addEventListener('hashchange', configurar)
  $('form-acesso').addEventListener('submit', async e => {
    e.preventDefault()
    if (!e.target.reportValidity()) return
    $('erro').hidden = $('status').hidden = true
    $('confirmar').disabled = true
    try {
      let resposta
      if (modo === 'verificar') resposta = await Api.verificarEmail(token)
      else if (modo === 'redefinir') resposta = await Api.redefinirSenha(token, $('senha').value, $('confirmacao').value)
      else if (modo === 'reenviar') resposta = await Api.reenviarVerificacao($('email').value)
      else resposta = await Api.recuperarSenha($('email').value)
      $('status').textContent = resposta.mensagem
      $('status').hidden = false
      e.target.reset()
      e.target.hidden = true
      token = ''
    } catch (erro) {
      $('erro').textContent = erro.message
      $('erro').hidden = false
    } finally { $('confirmar').disabled = false }
  })
})()
