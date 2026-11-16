// Executado pelo test_auth.py, exclusivamente no banco descartável. Sem e-mails reais.
const { chromium } = require(process.env.FORNEX_PLAYWRIGHT_MODULE)
const assert = require('node:assert/strict')
const { execFileSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')
const raiz = path.resolve(__dirname, '../..')
const base = process.env.FORNEX_UI_BASE
assert(process.env.DB_TEST_DATABASE?.startsWith('fornex_auth_test_'))
const senha = 'frase exclusiva do FORNEX 2026!'
const novaSenha = 'outra frase exclusiva do FORNEX!'
const email = 'fornextest.' + require('node:crypto').randomBytes(8).toString('hex') + '@gmail.com'
function link(finalidade) {
  execFileSync(process.env.PHP_BIN || 'php', [path.join(raiz, 'site/enviar-emails.php')], { stdio: 'pipe' })
  const msgs = fs.readFileSync(process.env.AUTH_MAIL_CAPTURE, 'utf8').trim().split('\n').map(JSON.parse)
  const texto = msgs.reverse().find(m => m.email === email && m.texto.includes('#' + finalidade + '='))?.texto
  const token = texto?.match(new RegExp('#' + finalidade + '=([a-f0-9]{64})'))?.[1]
  assert(token, 'Mensagem não capturada')
  return base + '/acesso.html#' + finalidade + '=' + token
}
async function esperar(page, seletor) { await page.locator(seletor).waitFor({ state: 'visible' }) }
async function entrar(page, valor) {
  await page.goto(base + '/chat.html')
  await esperar(page, '#form-entrar')
  await page.fill('#entrar-email', email)
  await page.fill('#entrar-senha', valor)
  await page.click('#form-entrar button[type=submit]')
  await esperar(page, '#tela-chat')
}
;(async () => {
  const browser = await chromium.launch({ channel: process.env.FORNEX_BROWSER_CHANNEL || 'msedge', headless: true })
  try {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
    // Nenhuma fonte externa ou chamada a serviços reais durante o teste.
    await context.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort())
    const page = await context.newPage()
    const erros = []
    page.on('pageerror', e => erros.push(e.message))
    await page.goto(base + '/chat.html#cadastro')
    await esperar(page, '#form-cadastro')
    await page.fill('#cad-nome', '<script>teste</script>')
    await page.fill('#cad-email', email)
    await page.fill('#cad-senha', senha)
    await page.fill('#cad-confirmacao', 'uma confirmacao diferente')
    await page.click('#form-cadastro button[type=submit]')
    await esperar(page, '#erro-cadastro')
    assert((await page.textContent('#erro-cadastro')).includes('iguais'))
    await page.fill('#cad-confirmacao', senha)
    await page.click('#form-cadastro button[type=submit]')
    await esperar(page, '#cadastro-status')
    assert.equal(await page.evaluate(async () => (await (await fetch('/api/me')).json()).usuario), null)
    await page.goto(link('verificar'))
    assert.equal(new URL(page.url()).hash, '')
    await page.click('#confirmar')
    await esperar(page, '#status')
    assert((await page.textContent('#status')).includes('verificado'))
    await entrar(page, senha)
    assert.equal(await page.locator('#link-admin').isVisible(), false)
    assert((await page.textContent('#quem')).includes('<script>teste</script>'))
    assert.equal(await page.evaluate(async () => (await fetch('/api/admin/telefones')).status), 403)
    const capturas = path.join(raiz, 'logs/auth-ui')
    fs.mkdirSync(capturas, { recursive: true })
    await page.screenshot({ path: path.join(capturas, 'chat-desktop.png'), fullPage: true })
    const context2 = await browser.newContext({ viewport: { width: 390, height: 844 } })
    await context2.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort())
    const page2 = await context2.newPage()
    page2.on('pageerror', e => erros.push(e.message))
    await entrar(page2, senha)
    await page.goto(base + '/acesso.html')
    await page.fill('#email', email)
    await page.click('#confirmar')
    await esperar(page, '#status')
    await page2.goto(link('redefinir'))
    await page2.fill('#senha', novaSenha)
    await page2.fill('#confirmacao', novaSenha)
    await page2.screenshot({ path: path.join(capturas, 'redefinir-mobile.png'), fullPage: true })
    assert(await page2.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page2.click('#confirmar')
    await esperar(page2, '#status')
    assert((await page2.textContent('#status')).includes('atualizada'))
    assert.equal(await page.evaluate(async () => (await (await fetch('/api/me')).json()).usuario), null)
    await entrar(page, novaSenha)
    await page.click('#sair')
    await esperar(page, '#form-entrar')
    assert.deepEqual(erros, [])
    console.log('Interface validada: cadastro, verificação, login, perfis, recuperação, sessão e largura móvel.')
  } finally { await browser.close() }
})().catch(e => { console.error(e.message); process.exitCode = 1 })
