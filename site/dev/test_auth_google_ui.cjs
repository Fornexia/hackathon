// GIS simulado no navegador; a API usa o tokeninfo RSA local do executor descartável.
const { chromium } = require(process.env.FORNEX_PLAYWRIGHT_MODULE)
const assert = require('node:assert/strict')
assert(process.env.DB_TEST_DATABASE?.startsWith('fornex_auth_test_'))
const base = process.env.FORNEX_UI_BASE
const desabilitado = process.env.FORNEX_UI_DISABLED_BASE
const credential = process.env.FORNEX_GOOGLE_TEST_CREDENTIAL
;(async () => {
  const browser = await chromium.launch({ channel: process.env.FORNEX_BROWSER_CHANNEL || 'msedge', headless: true })
  try {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } })
    const erros = []
    let scripts = 0
    await ctx.route('**/*', route => {
      const url = route.request().url()
      if (url === 'https://accounts.google.com/gsi/client') {
        scripts++
        return route.fulfill({ contentType: 'application/javascript', body: `
          window.google = { accounts: { id: {
            initialize(config) { window.__gis = config },
            renderButton(alvo) {
              const b = document.createElement('button'); b.type = 'button'; b.textContent = 'Entrar com Google';
              b.onclick = () => window.__gis.callback({ credential: ${JSON.stringify(credential)} }); alvo.append(b)
            }
          } } }` })
      }
      return url.startsWith(base) || url.startsWith(desabilitado) ? route.continue() : route.abort()
    })
    const page = await ctx.newPage()
    page.on('pageerror', e => erros.push(e.message))
    await page.goto(desabilitado + '/chat.html')
    await page.locator('#form-entrar').waitFor({ state: 'visible' })
    assert.equal(await page.locator('.acesso-google:visible').count(), 0)
    assert.equal(scripts, 0)
    await page.goto(base + '/chat.html')
    await page.locator('#form-entrar .botao-google button').waitFor({ state: 'visible' })
    assert.equal(scripts, 1)
    assert.equal(await page.locator('.botao-google button').count(), 2)
    assert((await page.textContent('#form-entrar .acesso-google')).includes('Seu e-mail já vem verificado pelo Google'))
    await page.click('#aba-cadastro')
    await page.click('#form-cadastro .botao-google button')
    await page.locator('#tela-chat').waitFor({ state: 'visible' })
    assert.equal(await page.locator('#link-admin').isVisible(), false)
    const me = await page.evaluate(async () => (await (await fetch('/api/me')).json()))
    assert.equal(me.usuario.email_verificado, true)
    assert(me.plano)
    await page.goto(base + '/conta.html')
    await page.locator('#dado-verificacao').waitFor({ state: 'visible' })
    assert.equal(await page.textContent('#dado-verificacao'), 'E-mail verificado')
    assert.equal(await page.locator('#verificar-agora').isVisible(), false)
    await page.goto(base + '/chat.html')
    await page.locator('#tela-chat').waitFor({ state: 'visible' })
    await page.click('#sair')
    await page.locator('#form-entrar').waitFor({ state: 'visible' })
    await page.click('#form-entrar .botao-google button')
    await page.locator('#tela-chat').waitFor({ state: 'visible' })
    assert.deepEqual(erros, [])
    console.log('GIS simulado validado: duas abas, conta, plano e largura de 390 px; sem rede externa.')
  } finally { await browser.close() }
})().catch(e => { console.error(e.message); process.exitCode = 1 })
