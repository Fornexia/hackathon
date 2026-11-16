import { useEffect, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  BriefcaseBusiness,
  Check,
  Clock3,
  Code2,
  Database,
  Layers3,
  Menu,
  Play,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  UsersRound,
  Video,
  X,
  Zap,
} from "lucide-react";
import FornexLaptop from "./components/fornex-laptop/FornexLaptop";
import assistente from "./components/fornex-laptop/assets/assistente-laptop.jpg";
import areaTecnica from "./components/fornex-laptop/assets/area-tecnica.jpg";
import Admin from "./Admin";
import Fundadores from "./Fundadores";
import Testar from "./Testar";
import ThemeToggle from "./ThemeToggle";
import { Contato, Faq, Historia, ParaQuem, QuemSomos, SiteFooter, TestarCta } from "./Sections";
import { useContent } from "./content";
import { useHashRoute, useReveal, useScrolled } from "./hooks";

/** [texto do menu, id da seção]. Os ids precisam existir como id="..." nas seções abaixo. */
const NAV_ITEMS: [string, string][] = [
  ["Quem somos", "quem-somos"],
  ["Solução", "solucao"],
  ["Recursos", "recursos"],
  ["Planos", "planos"],
  ["Fundadores", "fundadores"],
  ["Contato", "contato"],
];

const steps = [
  { icon: Search, title: "1. Pesquise", text: "Informe o CNPJ ou nome do fornecedor." },
  {
    icon: Layers3,
    title: "2. Reúna",
    text: "A plataforma coleta e organiza dados de portais públicos.",
  },
  {
    icon: Sparkles,
    title: "3. Analise com IA",
    text: "Receba um resumo claro, com riscos, histórico e pontos de atenção.",
  },
  {
    icon: ShieldCheck,
    title: "4. Comprove",
    text: "Tenha as evidências com fonte oficial e registre a consulta.",
  },
];

const features = [
  {
    icon: Database,
    title: "Consulta unificada",
    text: "Contratos, pagamentos e sanções em um só lugar.",
  },
  { icon: Sparkles, title: "Resumo com IA", text: "Análises objetivas e rápidas." },
  {
    icon: ShieldCheck,
    title: "Evidências oficiais",
    text: "Cada informação com sua fonte e data.",
  },
  { icon: UsersRound, title: "Controle por perfis", text: "Acesso seguro e personalizado." },
  {
    icon: BarChart3,
    title: "Histórico e relatórios",
    text: "Registre, exporte e acompanhe análises.",
  },
  { icon: Settings2, title: "Integração (API)", text: "Conecte com seus sistemas (em breve)." },
];

// O mesmo plano do produto (fornexia.figueiredo.dev, /api/planos). Se o plano mudar lá, mude aqui também.
// Antes havia três planos (R$ 399, 149 e 999) que o produto não oferece.
const plans = [
  {
    icon: Layers3,
    name: "Único",
    description: "Para compliance, gestoras de terceiros e empresas menores.",
    price: "149",
    items: [
      "Consulta: Estado de Pernambuco e Município de Garanhuns",
      "Site e WhatsApp, com nota de voz e a prova de cada fato",
      "Até 3 números de WhatsApp por conta, liberados no cadastro",
    ],
    action: "Começar agora",
    featured: true,
    tag: "Valor de demonstração",
  },
];

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <a href="#inicio" className="brand">
      <span className="brand-mark">
        <Layers3 />
      </span>
      <span className="brand-name">
        Fornex<span>IA</span>
        {!compact && <small>DADOS PÚBLICOS. DECISÕES SEGURAS.</small>}
      </span>
      <span className="sr-only">, página inicial</span>
    </a>
  );
}

function DashboardMockup({ src }: { src: string }) {
  return (
    <div className="laptop1">
      <FornexLaptop screenSrc={src} screenAlt="Assistente FornexIA" />
    </div>
  );
}

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const route = useHashRoute();
  const scrolled = useScrolled();
  const { images, founders } = useContent();
  // "Fundadores" só aparece no menu quando há fundadores cadastrados no admin
  const navItems = NAV_ITEMS.filter(([, id]) => id !== "fundadores" || founders.length > 0);
  useReveal(route);

  // ao voltar para o site vindo de outra tela, vai até a seção do endereço (ex.: #faq)
  useEffect(() => {
    if (route !== "") {
      window.scrollTo(0, 0);
      return;
    }
    const id = decodeURIComponent(location.hash.slice(1));
    if (!id) return;
    const t = setTimeout(() => document.getElementById(id)?.scrollIntoView(), 60);
    return () => clearTimeout(t);
  }, [route]);

  // Esc fecha o menu no celular
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMenuOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  // título da página por tela (leitores de tela e abas do navegador)
  useEffect(() => {
    const titles: Record<string, string> = {
      admin: "Administração | FornexIA",
      testar: "Testar o nosso sistema | FornexIA",
    };
    document.title = titles[route] ?? "FornexIA | Inteligência em fornecedores com dados públicos";
  }, [route]);

  if (route === "admin") return <Admin />;
  if (route === "testar") return <Testar />;

  return (
    <>
      <a className="skip-link" href="#principal">
        Pular para o conteúdo
      </a>
      <header className={`site-header${scrolled ? " scrolled" : ""}`}>
        <div className="container nav-wrap">
          <Brand />
          <nav id="menu-principal" className={menuOpen ? "nav-open" : ""} aria-label="Navegação principal">
            {navItems.map(([label, id]) => (
              <a key={id} href={`#${id}`} onClick={() => setMenuOpen(false)}>
                {label}
              </a>
            ))}
            <a href="#/testar" className="button button-small">
              Testar o nosso sistema
            </a>
          </nav>
          <ThemeToggle />
          <button
            className="menu-button"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label={menuOpen ? "Fechar menu" : "Abrir menu"}
            aria-expanded={menuOpen}
            aria-controls="menu-principal"
          >
            {menuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </header>

      <main id="principal" tabIndex={-1}>

      <section className="hero" id="inicio">
        <div className="orb orb-one" />
        <div className="orb orb-two" />
        <div className="container hero-grid">
          <div className="hero-copy">
            <span className="eyebrow">Inteligência em Fornecedores</span>
            <h1>
              Investigue fornecedores com dados públicos, <span>IA e evidências oficiais.</span>
            </h1>
            <p>
              Consolide contratos, pagamentos e sanções em um só lugar. Ganhe agilidade, segurança e
              conformidade nas análises de fornecedores.
            </p>
            <div className="hero-actions">
              <a href="#/testar" className="button">
                Testar o nosso sistema <ArrowRight />
              </a>
              <a href="#conteudo" className="button button-outline">
                <Play fill="currentColor" /> Ver como funciona
              </a>
            </div>
            <div className="trust-row">
              <span>
                <ShieldCheck /> Fontes oficiais
              </span>
              <span>
                <Zap /> Análise rápida
              </span>
              <span>
                <Layers3 /> Evidências rastreáveis
              </span>
            </div>
          </div>
          <div className="hero-visual">
            <DashboardMockup src={images.hero || assistente} />
          </div>
        </div>
      </section>

      <section className="benefits" id="solucao">
        <div className="container benefits-grid">
          <h2>
            Quem usa a<br />
            FornexIA resolve:
          </h2>
          {[
            [Clock3, "Reduz o tempo", "de investigação."],
            [ShieldCheck, "Diminui o risco", "de contratação."],
            [SlidersHorizontal, "Padroniza a análise", "de fornecedores."],
            [BarChart3, "Apoia auditorias", "e compliance."],
          ].map(([Icon, title, text]) => {
            const BenefitIcon = Icon as typeof Clock3;
            return (
              <div className="benefit" key={title as string}>
                <BenefitIcon />
                <span>
                  {title as string}
                  <small>{text as string}</small>
                </span>
              </div>
            );
          })}
        </div>
      </section>

      <QuemSomos />

      <Historia />

      <section className="section process" id="conteudo">
        <div className="container">
          <div className="section-heading reveal">
            <h2>Como a FornexIA funciona?</h2>
            <i />
          </div>
          <div className="steps reveal">
            {steps.map(({ icon: Icon, title, text }, index) => (
              <div className="step-wrap" key={title}>
                <article className="step-card">
                  <span className="icon-orb">
                    <Icon />
                  </span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
                {index < steps.length - 1 && <ArrowRight className="step-arrow" />}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section features-section" id="recursos">
        <div className="container feature-layout reveal">
          <div className="feature-mockup">
            <FornexLaptop screenSrc={images.features || areaTecnica} screenAlt="Área técnica" badge={false} />
          </div>
          <div>
            <div className="section-heading align-left">
              <h2>Principais recursos</h2>
              <i />
            </div>
            <div className="feature-grid">
              {features.map(({ icon: Icon, title, text }) => (
                <article className="feature-card" key={title}>
                  <Icon />
                  <div>
                    <h3>{title}</h3>
                    <p>{text}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <ParaQuem />

      <section className="section pricing" id="planos">
        <div className="container pricing-layout">
          <div className="pricing-intro reveal">
            <div className="section-heading align-left">
              <h2>Um plano para começar a investigar hoje</h2>
              <i />
            </div>
            <p>
              Valor de demonstração, ainda não validado. Nada é cobrado nesta versão.
            </p>
          </div>
          <div className={`plans reveal${plans.length === 1 ? " plans-one" : ""}`}>
            {plans.map(({ icon: Icon, name, description, price, items, action, featured, tag }) => (
              <article className={`plan-card ${featured ? "featured" : ""}`} key={name}>
                <span className="popular">{tag}</span>
                <h3>
                  <Icon aria-hidden="true" /> {name}
                </h3>
                <p>{description}</p>
                <div className="price">
                  <small>R$</small> {price}
                  <span>/mês</span>
                </div>
                <ul>
                  {items.map((item) => (
                    <li key={item}>
                      <Check /> {item}
                    </li>
                  ))}
                </ul>
                <a href="#/testar" className={`plan-button ${featured ? "primary" : ""}`}>
                  {action}
                </a>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* A seção "Quem já confia na FornexIA" saiu: os depoimentos (Carlos M., Renata S.) e os números
          (+1.200 consultas, 98% de satisfação, 30% mais agilidade) eram fictícios. Volta só com clientes e dados reais. */}

      <Fundadores />

      <Faq />

      <TestarCta />

      <Contato />

      </main>

      <SiteFooter brand={<Brand />} />
    </>
  );
}
