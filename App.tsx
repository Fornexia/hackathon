import { useState } from "react";
import {
  ArrowRight,
  BarChart3,
  BriefcaseBusiness,
  Building2,
  Check,
  Clock3,
  Code2,
  Database,
  Layers3,
  Menu,
  Play,
  Quote,
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

const plans = [
  {
    icon: Layers3,
    name: "Essencial",
    description: "Ideal para pequenas operações.",
    price: "149",
    items: [
      "Até 70 consultas/mês",
      "1 usuário",
      "Consultas com IA",
      "Evidências com fontes oficiais",
    ],
    action: "Começar agora",
  },
  {
    icon: Layers3,
    name: "Profissional",
    description: "Para equipes em crescimento.",
    price: "399",
    items: [
      "Até 300 consultas/mês",
      "Até 3 usuários",
      "Relatórios e histórico",
      "Suporte prioritário",
    ],
    action: "Assinar Profissional",
    featured: true,
  },
  {
    icon: Building2,
    name: "Corporativo",
    description: "Para grandes operações.",
    price: "999",
    items: [
      "Até 1.000 consultas/mês",
      "Até 10 usuários",
      "Integração via API (em breve)",
      "Suporte dedicado",
    ],
    action: "Falar com um especialista",
  },
];

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <a href="#inicio" className="brand" aria-label="FornexIA — página inicial">
      <span className="brand-mark">
        <Layers3 />
      </span>
      <span className="brand-name">
        Fornex<span>IA</span>
        {!compact && <small>DADOS PÚBLICOS. DECISÕES SEGURAS.</small>}
      </span>
    </a>
  );
}

function DashboardMockup() {
  return (
    <div className="laptop1">
      <FornexLaptop screenSrc={assistente} screenAlt="Assistente FornexIA" />
    </div>
  );
}

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <main>
      <header className="site-header">
        <div className="container nav-wrap">
          <Brand />
          <nav className={menuOpen ? "nav-open" : ""} aria-label="Navegação principal">
            {["Solução", "Recursos", "Planos", "Clientes", "Conteúdo"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase().replace("ç", "c")}`}
                onClick={() => setMenuOpen(false)}
              >
                {item}
              </a>
            ))}
            <a href="#contato" className="nav-login">
              Entrar
            </a>
            <a href="#planos" className="button button-small">
              Testar grátis
            </a>
          </nav>
          <button
            className="menu-button"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Abrir menu"
          >
            {menuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </header>

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
              <a href="#planos" className="button">
                Testar grátis por 7 dias <ArrowRight />
              </a>
              <a href="#solucao" className="button button-outline">
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
            <DashboardMockup />
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

      <section className="section process" id="conteudo">
        <div className="container">
          <div className="section-heading">
            <h2>Como a FornexIA funciona?</h2>
            <i />
          </div>
          <div className="steps">
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
        <div className="container feature-layout">
          <div className="feature-mockup">
            <FornexLaptop screenSrc={areaTecnica} screenAlt="Área técnica" badge={false}/>
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

      <section className="section pricing" id="planos">
        <div className="container pricing-layout">
          <div className="pricing-intro">
            <div className="section-heading align-left">
              <h2>Escolha o plano ideal para sua equipe</h2>
              <i />
            </div>
            <p>
              Soluções flexíveis para diferentes volumes de análise e necessidades de compliance.
            </p>
          </div>
          <div className="plans">
            {plans.map(({ icon: Icon, name, description, price, items, action, featured }) => (
              <article className={`plan-card ${featured ? "featured" : ""}`} key={name}>
                {featured && <span className="popular">Mais escolhido</span>}
                <h3>
                  <Icon /> {name}
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
                <a href="#contato" className={`plan-button ${featured ? "primary" : ""}`}>
                  {action}
                </a>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section testimonials" id="clientes">
        <div className="container testimonials-grid">
          <div className="section-heading align-left">
            <h2>Quem já confia na FornexIA</h2>
            <i />
          </div>
          <article className="testimonial-card">
            <Quote />
            <p>
              “Conseguimos reduzir drasticamente o tempo de análise de fornecedores, com mais
              segurança e rastreabilidade.”
            </p>
            <div className="person">
              <span>CM</span>
              <div>
                <b>Carlos M.</b>
                <small>Analista de Compliance</small>
              </div>
            </div>
          </article>
          <article className="testimonial-card">
            <Quote />
            <p>
              “A clareza das informações e a organização das evidências nos deram mais confiança nas
              decisões.”
            </p>
            <div className="person person-two">
              <span>RS</span>
              <div>
                <b>Renata S.</b>
                <small>Gestora de Contratos</small>
              </div>
            </div>
          </article>
          <div className="metrics">
            <span>
              <BarChart3 />
              <b>
                +1.200<small>consultas realizadas</small>
              </b>
            </span>
            <span>
              <ShieldCheck />
              <b>
                98%<small>de satisfação</small>
              </b>
            </span>
            <span>
              <Clock3 />
              <b>
                30%<small>mais agilidade na análise</small>
              </b>
            </span>
          </div>
        </div>
      </section>

      <section className="cta-section" id="contato">
        <div className="container">
          <div className="cta-card">
            <Layers3 className="cta-icon" />
            <h2>
              Pronto para tomar decisões
              <br />
              mais seguras com a FornexIA
            </h2>
            <div>
              <a href="mailto:contato@fornexia.com.br" className="button">
                Testar grátis por 7 dias <ArrowRight />
              </a>
              <p>
                <span>
                  <Check /> Sem cartão de crédito
                </span>
                <span>
                  <Check /> Configuração rápida
                </span>
                <span>
                  <Check /> Suporte durante o teste
                </span>
              </p>
            </div>
          </div>
        </div>
      </section>

      <footer>
        <div className="container footer-wrap">
          <Brand />
          <nav>
            {["Solução", "Recursos", "Planos", "Conteúdo", "Contato"].map((item) => (
              <a href={`#${item.toLowerCase().replace("ç", "c")}`} key={item}>
                {item}
              </a>
            ))}
          </nav>
          <div className="socials">
            <a href="#" aria-label="LinkedIn">
              <BriefcaseBusiness />
            </a>
            <a href="#" aria-label="YouTube">
              <Video />
            </a>
            <a href="#" aria-label="GitHub">
              <Code2 />
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}
