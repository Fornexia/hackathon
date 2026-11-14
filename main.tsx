import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import './styles/pro.css'
import './styles/light.css'
import { initTheme } from './theme'

// idioma e título corretos (o index.html usa marcadores do Figma que ficam vazios no desenvolvimento)
document.documentElement.lang = 'pt-BR'
if (!document.title || document.title.includes('figma')) {
  document.title = 'FornexIA | Inteligência em fornecedores com dados públicos'
}
initTheme()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
