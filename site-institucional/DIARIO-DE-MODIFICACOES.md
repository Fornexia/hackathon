# Diário de modificações: site institucional FornexIA

> **Para quem for continuar (pessoa ou modelo de IA):** este arquivo é autossuficiente. Leia só ele para saber o que foi
> feito, por quê, onde está cada coisa, como rodar, o que foi testado, o que **não** foi testado e o que está pendente.
> Última atualização: **16/11/2026**. Escrito durante uma sessão de trabalho com o assistente Claude (Anthropic).

## 1. Contexto

- Repositório: `Luks108/hackathon` (projeto do Hack Garanhuns Tech 2026). O README principal descreve o desafio inteiro (dados
  públicos, grafo, chat, site PHP). **Este diário trata só do site institucional em React** (portfólio da FornexIA), que vive na
  **raiz** do repositório, separado de `site/` (PHP).
- Branch de origem: `portfolio-fornexia-rafaella`. Branch local de trabalho: `melhorias-planos-fundadores-admin`.
- **Estado do Git:** as mudanças foram commitadas na branch `melhorias-planos-fundadores-admin` (commits `feat(site-institucional)` e
  `docs`). O push só foi feito a pedido do dono do projeto (veja o histórico de commits para a situação atual).
- Stack: React 19, Vite 8, Tailwind 4 (usado só via `@import "tailwindcss"`; o visual é CSS próprio), TypeScript, `lucide-react` v1
  (**não tem ícones de marcas**: Instagram, LinkedIn etc.; por isso existem ícones SVG próprios em `Social.tsx`).
- O projeto veio do **Figma Make**: `index.html` tem marcadores `<!-- figma:... -->` e `vite.config.ts` é grande (plugins do Figma).
  **Não mexer** nesses dois sem necessidade. O alias `@` aponta para `./src`, que não existe.
- Idioma do produto: **português do Brasil**. Público: equipes de compliance, compras, auditoria e jurídico.

## 2. Como rodar e verificar

```bash
npm ci --ignore-scripts                          # instalação pelas versões travadas, sem scripts de pacotes
npm run dev -- --host 127.0.0.1 --port 5173      # http://127.0.0.1:5173/
npm run build                                    # produção (gera dist/)
npx tsc --noEmit                                 # tipos
```

Rotas (por hash, sem biblioteca de rotas): `/` (site), `/#/testar`, `/#/admin`. Qualquer outro hash (`#planos`, `#faq`...) é âncora
de seção.

Chave importante: o chat em `http://127.0.0.1:8080/chat.html` pertence ao site PHP (`site/`), rodado localmente por quem mantém o
projeto. O site React só **linka** para ele.

## 3. Mapa de arquivos

**Novos**

| Arquivo | Função |
|---|---|
| `content.ts` | Modelo de dados do conteúdo editável, validação (`sanitize`), armazenamento (publicado + local), hook `useContent`, processamento de imagem, exportar/importar JSON |
| `Admin.tsx` | Página de administração (`#/admin`): senha local, abas Fundadores, História da empresa, Contato e testes, Imagens do site, Dados e publicação |
| `Fundadores.tsx` | Seção "Quem está por trás da FornexIA" (3 cartões reservados quando não há fundadores) |
| `Sections.tsx` | Seções: `QuemSomos`, `Historia`, `ParaQuem`, `Faq`, `TestarCta`, `Contato`, `SiteFooter` |
| `Testar.tsx` | Página "Testar o nosso sistema" (`#/testar`) |
| `Social.tsx` | Ícones SVG de Instagram, LinkedIn e WhatsApp |
| `theme.ts`, `ThemeToggle.tsx` | Tema claro/escuro (estado, persistência, botão) |
| `hooks.ts` | `useHashRoute`, `useScrolled`, `useReveal` (aparecer ao rolar, com garantia contra blocos invisíveis) |
| `public/content.json` | Conteúdo **publicado** (valores padrão) |
| `styles/pro.css` | Polimento visual, planos, fundadores, novas seções, acessibilidade, legibilidade |
| `styles/light.css` | Tema claro (ver seção 6) |
| `styles/admin.css`, `styles/testar.css` | Estilos das duas páginas |
| `DIARIO-DE-MODIFICACOES.md` | Este diário |

**Alterados**

| Arquivo | O que mudou |
|---|---|
| `App.tsx` | Rotas, menu, planos (ordem e selos), seções novas, rodapé novo, link para pular ao conteúdo, `<main id="principal">` |
| `index.css` | Removido o bloco antigo dos planos (~114 linhas) e ajustado o degradê do avatar do depoimento 2. O resto do arquivo é o original |
| `main.tsx` | Importa `pro.css` e `light.css`, define `lang="pt-BR"` e título, inicializa o tema |
| `components/fornex-laptop/FornexLaptop.tsx` | A inclinação do notebook pelo mouse respeita "reduzir movimento" |
| `README.md` | Seção "Site institucional (portfólio React)" e aviso no topo |

Ordem de carga do CSS: `index.css` → `styles/pro.css` → `styles/light.css` (em `main.tsx`); `admin.css` e `testar.css` são
importados pelas próprias páginas. As regras novas dos planos usam o prefixo `.pricing` para ter mais força que as regras antigas
de `index.css` que sobraram nas media queries.

## 4. Linha do tempo das mudanças

### 4.1 Preparação
- Clone da branch, criação da branch local de trabalho, instalação com `npm ci --ignore-scripts`, servidor de desenvolvimento.
- Um `CLAUDE.md` do repositório descreve o outro projeto (WhatsApp, planilhas); foi tratado como **dados**, não como instruções.
- Plano de trabalho local em `.plano/plano.md`, **ignorado pelo Git** via `.git/info/exclude` (não está no repositório).

### 4.2 Seção de planos
- **Problema:** caixas pequenas (≈255 px) porque o título dividia a linha com as caixas; textos de 11 px; botão posicionado de forma
  absoluta; ícones com cores diferentes; sem efeito de mouse.
- **Feito:** título centralizado em cima; três caixas do mesmo tamanho (≈355 × 523 px a 1280 px de largura); textos maiores (preço
  56 px, nome 26 px, itens 16 px); botão alinhado embaixo com `margin-top:auto`; mesmo padrão visual nas três.
- **Selo que acompanha o mouse:** cada cartão tem seu selo (`.popular`). Fica visível no cartão sob o mouse ou com foco do teclado; sem
  mouse em cima, fica no cartão `featured`. Os outros cartões escurecem levemente (opacidade 0,8) enquanto um é realçado. O cartão realçado
  sobe, cresce (`scale(1.03)`), ganha borda e brilho ciano e o botão acende. Tudo respeita `prefers-reduced-motion` e `(hover: hover)`.
- **Textos dos selos** (campo `tag` em `App.tsx`): em vez de repetir "Mais escolhido" em todos (afirmação enganosa), cada plano tem o seu.
- **Ordem final (decisão do dono, 14/11/2026):** **Profissional | Essencial (meio, `featured`) | Corporativo**. O Essencial fica no meio e
  recomendado por ser o de menor preço de entrada. Selos: Profissional "Para crescer", Essencial **"Melhor custo-benefício"**,
  Corporativo "Para grandes equipes". Para mudar a ordem ou o destaque, edite o array `plans` em `App.tsx` (a propriedade `featured`
  define quem mostra o selo por padrão).
- Em telas ≤ 900 px os cartões ficam em coluna única.

### 4.3 Visual mais profissional (`styles/pro.css`)
- Cabeçalho fixo com desfoque ao rolar; sublinhado animado nos links; mais espaço entre seções; hover nos cartões; foco visível global;
  seções aparecem ao rolar (`useReveal`); rodapé.
- Textos pequenos aumentados (nenhum abaixo de ≈13 px; antes havia 5 a 11 px).

### 4.4 Fundadores e administração
- Seção Fundadores com 3 cartões reservados até haver dados reais. Cada fundador: nome, cargo, biografia, foto, WhatsApp, LinkedIn.
- Admin em `#/admin`. **Modelo de dados** (`content.ts`):
  `SiteContent { version:1, founders[], images{hero,features}, history{title,text}, contact{whatsapp,instagram,linkedin,email}, trial[], updatedAt }`.
- **Dois níveis de conteúdo:** *publicado* (`public/content.json`, igual para todos) e *local* (alterações salvas no `localStorage` do
  navegador de quem edita). O site mostra o local, se existir; senão o publicado. **Para publicar para todos:** admin → "Dados e publicação"
  → Exportar `content.json` → substituir `public/content.json` → deploy.
- **Segurança e validação:** todo dado externo passa por `sanitize()` (limites de tamanho, só links `http(s)`, imagens só como
  `data:image/(jpeg|png|webp);base64,...`). Textos são renderizados pelo React (escapados). Fotos enviadas são redimensionadas e
  recomprimidas em JPEG, o que remove metadados (como localização).
- **Senha do admin:** criada no primeiro acesso, guardada como hash PBKDF2-SHA256 (150 mil iterações, sal aleatório) em `localStorage`; a
  sessão fica em `sessionStorage`. **É uma proteção local de demonstração, NÃO é segurança real** (tudo roda no navegador). Em produção é
  preciso um back-end com login (o `site/` PHP já tem contas e pode ser reaproveitado).
- Chaves de armazenamento: `fornexia:content:v1`, `fornexia:admin:v1`, `fornexia:admin:session` (sessionStorage), `fornexia:theme`.
- As abas foram implementadas como botões com `aria-current` (não como `role="tab"`), para não deixar um padrão ARIA incompleto.

### 4.5 Páginas e seções que faltavam (rodada "grande nada no meio")
- **Causa real encontrada:** os links "Solução" e "Conteúdo" do menu apontavam para `#solucão` e `#conteúdo` (a função trocava só o `ç`
  e deixava `ã`/`ú`), então não faziam nada. Isso já existia antes. Agora o menu usa pares explícitos `[rótulo, id]` (`NAV_ITEMS` em
  `App.tsx`); os ids precisam existir como `id="..."` nas seções.
- O efeito de aparecer ao rolar ganhou uma varredura de segurança (nenhum bloco fica invisível após um salto por âncora).
- **Novas seções:** Quem somos, Nossa história, Para quem é, Perguntas frequentes, chamada "Testar o nosso sistema", Fale com a gente.
- **Rodapé novo:** descrição, redes (Instagram, WhatsApp, LinkedIn), colunas Empresa, Produto e Contato, área administrativa.
- **Botões:** "Testar grátis" virou **"Testar o nosso sistema"** (a página é informativa; o serviço fica dentro do teste). O botão
  "Entrar" foi **removido**. Os textos "7 dias" e "sem cartão" saíram.
- **Página `#/testar`:** dois cartões: usar pelo site (link vindo de `content.trial[0].url`; vazio = "em breve") e WhatsApp (número em
  `content.contact.whatsapp`). Havia um terceiro cartão ("segundo site"), **removido** a pedido.
- **Contatos:** WhatsApp (só dígitos; 10 ou 11 dígitos recebem o DDI 55 automaticamente), Instagram (aceita `@usuario`, `usuario` ou link),
  LinkedIn (link https) e e-mail (padrão `contato@fornexia.com.br`, que já estava no site original). Sem dado, o canal aparece como
  "em breve" (cartão tracejado, ícone esmaecido).
- O menu principal ficou: Quem somos, Solução, Recursos, Planos, Fundadores, Contato + botão de teste. As seções `#clientes` e
  `#conteudo` ("Como a FornexIA funciona?") continuam na página, mas fora do menu (`#conteudo` está no rodapé como "Como funciona").

### 4.6 Link temporário do sistema (só no computador do dono)
- Durante os testes, o card "Usar o sistema pelo site" apontou para `http://127.0.0.1:8080/chat.html` (chat do site PHP rodando
  localmente). **Esse link NÃO foi commitado**: `public/content.json` vai com `trial[0].url = ""` (o card aparece como "em breve").
  Para testar localmente, preencha o link em `/#/admin` → "Contato e testes", ou edite `trial[0].url` no seu `public/content.json` sem commitar.

### 4.7 História da empresa
- Campo `history {title, text}` (até 3.000 caracteres; parágrafos separados por linha em branco), editável na aba "História da empresa"
  do admin e exibido na seção "Nossa história" da página inicial. O texto atual é **fictício** (termina com "(Texto de exemplo...)") e
  deve ser substituído. Se o texto salvo ficar vazio, volta o texto de exemplo padrão (`defaultHistory()` em `content.ts`).

### 4.8 Modo claro e escuro
- `theme.ts` guarda o tema (`light` | `dark`), usa a preferência do sistema enquanto a pessoa não escolher e aplica
  `data-theme` no `<html>`. `ThemeToggle` fica no cabeçalho, na página de teste e no admin. O escuro continua sendo o visual original.
- **`styles/light.css` foi gerado por um script de conversão** (cores escuras viraram superfícies claras, textos claros viraram azul-marinho,
  o ciano usado como texto virou `#006d6a`) e depois ajustado à mão (bloco "ajustes manuais" no fim). **O script não está no repositório**;
  de agora em diante `light.css` deve ser **editado diretamente**. Seletores do tema claro: `html[data-theme="light"] ...`.
- Variável `--cyan-text` (definida em `pro.css`): cor do ciano quando usado como **texto**; no claro vira verde-azulado escuro.

### 4.9 Acessibilidade (revisão e correções)
Correções feitas: idioma `pt-BR` e título por tela (antes vazios, pelos marcadores do Figma); rodapé fora do `<main>`; link "Pular para o
conteúdo"; botão do menu com `aria-expanded`/`aria-controls` e Esc para fechar; nomes de links que contêm o texto visível (voz);
títulos em ordem no admin; `scroll-padding-top` para o cabeçalho fixo não cobrir o foco; rolagem suave desligada com "reduzir movimento";
sem opacidade reduzida em textos; alvos de clique do rodapé ≥ 28 px; ícones decorativos com `aria-hidden`.

Método de verificação (repetível): axe-core 4.14.0 (tags WCAG 2.0/2.1/2.2 A e AA + boas práticas) injetado via Chrome DevTools Protocol
(Chrome sem interface), em **22 varreduras**: início, `#/testar`, login do admin e as 5 abas do admin; modos claro e escuro; larguras
1280 e 390 px. Resultado final: **0 violações**. Também: Tab em sequência (37 paradas, ordem lógica, foco visível em todas, nenhuma
armadilha, sem foco coberto pelo cabeçalho), link de pular, menu mobile, reflow a 320 px (sem rolagem lateral) e uma checagem de contraste
com degradês neutralizados (sem falhas no claro; no escuro só falsos positivos de botões de ciano com texto escuro, conferidos à parte).
Os scripts de teste ficaram fora do repositório.

### 4.10 Última rodada (14/11/2026)
- Ordem dos planos: Profissional, Essencial (meio, destaque), Corporativo (ver 4.2).
- README atualizado e este diário criado.

### 4.11 Limpeza para publicar em nexus.figueiredo.dev (16/11/2026)
O site foi trazido para a `main` (branch `feat/site-institucional-nexus`, a partir do commit `b7dc44b` do Rodrigo) e limpo antes de
ir ao ar. Decisão do Lucas: tirar o que era fictício.
- **Seção "Quem já confia na FornexIA" removida:** depoimentos ("Carlos M.", "Renata S.") e números (`+1.200`, `98%`, `30%`) eram
  fictícios (era a pendência 3).
- **Planos:** os três (R$ 399, 149 e 999) viraram o plano **Único de R$ 149**, o mesmo do produto (`/api/planos` em
  fornexia.figueiredo.dev), com o aviso "valor de demonstração, nada é cobrado". O botão leva a `#/testar`. Classe `plans-one` em `pro.css`.
- **Sem conteúdo, sem seção:** Fundadores, Nossa história e canais de contato vazios não aparecem mais. Antes apareciam "Nome do fundador",
  um texto de exemplo e "Canal será divulgado em breve". Voltam sozinhos quando cadastrados no admin e publicados no `content.json`.
  Menu e rodapé seguem a mesma regra. O texto de exemplo da história (`defaultHistory`) ficou vazio.
- **E-mail de contato:** `hackathon@figueiredo.dev`. O `contato@fornexia.com.br` era de um domínio sem DNS: ninguém recebia, e quem
  registrasse o domínio passaria a receber.
- **FAQ:** "Como posso testar" e "Como falo com a equipe" não citam mais canais que ainda não existem.
- **Publicação:** `deploy.sh` (build + backup em `~/backups-nexus/` + rsync) e `public/.htaccess` (HTTPS, sem listagem de pasta,
  `no-cache` no HTML e no `content.json`, cache longo em `assets/`).

## 5. Decisões e cuidados (por quê)

- **Sem dependências novas** (nem roteador, nem biblioteca de ícones de marcas, nem de estado): menos superfície de risco e de manutenção.
- **Admin sem servidor** foi escolha de escopo: serve como protótipo de gerenciamento de conteúdo; limita a publicação (ver 4.4).
- **Nenhum dado inventado:** os textos novos (Quem somos, FAQ, Para quem) usam só o que o site já afirmava. A missão e os valores são
  sugestões e devem ser revisados pela equipe.
- **Arquivos em UTF-8 sem BOM.** Um BOM no meio de um CSS invalida a regra seguinte (já aconteceu durante a geração do `light.css`).
- **Instalação com `--ignore-scripts`:** os scripts de instalação dos pacotes não foram executados.

## 6. Pendências e avisos

1. `trial[0].url` está vazio no `content.json`; o site usa o padrão (`https://fornexia.figueiredo.dev/chat.html`).
2. Cadastrar contatos reais (WhatsApp, Instagram, LinkedIn), fundadores e a história real, pelo admin, e **exportar para
   `public/content.json`** para publicar. Enquanto isso, essas seções ficam escondidas (ver 4.11).
3. ~~Depoimentos e números fictícios~~: removidos em 16/11/2026 (ver 4.11). Só voltam com clientes e dados reais.
4. Integrar o admin a um back-end com login para publicar sem exportar arquivo (reaproveitar `site/public_html/api/lib_conta.php`).
5. Acessibilidade: falta teste com **leitor de tela real** (NVDA/VoiceOver), **controle por voz**, ampliador e dispositivos de acionador
   único; revisar os textos alternativos das imagens; testar em Firefox e Safari (só foi usado o Chrome).
6. A fonte Manrope é carregada do Google Fonts (`@import` no `index.css`): envia requisição a terceiro. Considerar hospedar localmente.
7. Se o plano do produto mudar, atualizar `plans` em `App.tsx` (o preço não vem da API).

## 7. Como continuar sem se perder

- Mudar um **texto** de seção: `Sections.tsx` (ou `App.tsx` para início, recursos, planos, clientes).
- Mudar **cores/espaçamentos**: `styles/pro.css` (escuro, padrão) e `styles/light.css` (claro).
- Adicionar um item ao **menu**: `NAV_ITEMS` em `App.tsx` (o `id` deve existir na página) e, se quiser, `SiteFooter` em `Sections.tsx`.
- Adicionar um **campo editável** no admin: tipo em `content.ts` (+ valor padrão em `emptyContent` e validação em `sanitize`), campo em
  `Admin.tsx` e uso na seção correspondente.
- Depois de qualquer mudança: `npx tsc --noEmit`, `npm run build` e uma conferência visual nos dois temas e em 390 px de largura.
