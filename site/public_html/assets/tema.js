// Tema claro/escuro. Sem escolha guardada, vale o do sistema (CSS: prefers-color-scheme). Com escolha, o atributo data-tema
// na <html> manda, e ela fica guardada neste navegador (localStorage). Este arquivo roda no <head>, antes de a página aparecer,
// para a tela não piscar no tema errado. Os botões são qualquer elemento com data-tema-botao.
(() => {
  const CHAVE = 'fornexia-tema'
  const COR_DO_NAVEGADOR = { escuro: '#03162d', claro: '#f2f7fb' }
  const raiz = document.documentElement

  const guardado = () => {
    try { const v = localStorage.getItem(CHAVE); return v === 'claro' || v === 'escuro' ? v : null } catch { return null }
  }
  const claroDoSistema = () => !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches)
  const atual = () => raiz.dataset.tema || (claroDoSistema() ? 'claro' : 'escuro')

  const SOL = '<svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
  const LUA = '<svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 14.5A8 8 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5z"/></svg>'

  // O botão mostra o tema para o qual vai trocar (sol no escuro, lua no claro) e diz isso por escrito para leitores de tela.
  function rotular() {
    const escuro = atual() === 'escuro'
    const texto = escuro ? 'Mudar para o modo claro' : 'Mudar para o modo escuro'
    document.querySelectorAll('[data-tema-botao]').forEach(b => {
      b.innerHTML = escuro ? SOL : LUA
      b.setAttribute('aria-label', texto)
      b.title = texto
    })
  }

  function aplicar(tema) {
    raiz.dataset.tema = tema
    document.querySelectorAll('meta[name="theme-color"]').forEach(m => m.setAttribute('content', COR_DO_NAVEGADOR[tema]))
    rotular()
    window.dispatchEvent(new Event('tema'))   // o grafo (canvas) escuta e se redesenha
  }

  function alternar() {
    const novo = atual() === 'escuro' ? 'claro' : 'escuro'
    try { localStorage.setItem(CHAVE, novo) } catch { /* sem armazenamento: vale só nesta página */ }
    aplicar(novo)
  }

  function ligar() {
    document.querySelectorAll('[data-tema-botao]').forEach(b => {
      if (b.dataset.ligado) return
      b.dataset.ligado = '1'
      b.type = 'button'
      b.addEventListener('click', alternar)
    })
    rotular()
  }

  const inicial = guardado()
  if (inicial) raiz.dataset.tema = inicial
  document.addEventListener('DOMContentLoaded', () => { if (inicial) aplicar(inicial); else rotular(); ligar() })
  // O assistente da página inicial é um iframe: troca feita numa janela vale na outra.
  window.addEventListener('storage', e => { if (e.key === CHAVE) { const v = guardado(); if (v) aplicar(v) } })
  if (window.matchMedia) window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => { if (!raiz.dataset.tema) { rotular(); window.dispatchEvent(new Event('tema')) } })

  window.Tema = { ligar, alternar, atual }
})()
