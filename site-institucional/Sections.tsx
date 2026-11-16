import {
  ArrowRight,
  BadgeCheck,
  Building2,
  ChevronDown,
  ClipboardCheck,
  Eye,
  FileSearch,
  Gavel,
  Handshake,
  Layers3,
  Mail,
  Scale,
  Target,
} from "lucide-react";
import { instagramUrl, useContent, waLink } from "./content";
import { InstagramIcon, LinkedinIcon, WhatsappIcon } from "./Social";

const WA_MSG = "Olá! Vim pelo site da FornexIA e gostaria de conversar com a equipe.";

/* ---------- Quem somos ---------- */
export function QuemSomos() {
  const pillars = [
    {
      icon: Target,
      title: "Nossa missão",
      text: "Tornar a análise de fornecedores mais rápida, segura e transparente, com dados públicos organizados em um só lugar.",
    },
    {
      icon: FileSearch,
      title: "Como trabalhamos",
      text: "Reunimos informações de portais oficiais e mostramos a fonte e a data de cada dado, para que tudo possa ser conferido.",
    },
    {
      icon: Eye,
      title: "Nosso compromisso",
      text: "A IA resume e apoia a análise. A comprovação vem sempre da evidência oficial, e a decisão final é da sua equipe.",
    },
  ];
  const values = ["Transparência", "Rastreabilidade", "Clareza", "Responsabilidade"];
  return (
    <section className="section about" id="quem-somos">
      <div className="container">
        <div className="section-heading reveal">
          <h2>Quem somos</h2>
          <i />
          <p className="section-sub">
            A FornexIA é uma plataforma de inteligência em fornecedores. Consolidamos contratos, pagamentos e
            sanções de dados públicos e usamos IA para entregar resumos claros, com evidências oficiais.
          </p>
        </div>
        <div className="about-grid reveal">
          {pillars.map(({ icon: Icon, title, text }) => (
            <article className="about-card" key={title}>
              <span className="icon-orb static">
                <Icon aria-hidden="true" />
              </span>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
        <ul className="values reveal" aria-label="Nossos valores">
          {values.map((v) => (
            <li key={v}>
              <BadgeCheck aria-hidden="true" /> {v}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ---------- Nossa história (texto editável no admin) ---------- */
export function Historia() {
  const { history } = useContent();
  const paragraphs = history.text.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
  if (!paragraphs.length) return null;   // sem a história real escrita no admin, a seção não aparece
  return (
    <section className="section story" id="historia" aria-labelledby="historia-titulo">
      <div className="container story-grid">
        <div className="story-head reveal">
          <span className="eyebrow">Nossa história</span>
          <h2 id="historia-titulo">{history.title}</h2>
          <i aria-hidden="true" />
        </div>
        <div className="story-body reveal">
          {paragraphs.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- Para quem é ---------- */
export function ParaQuem() {
  const items = [
    { icon: ClipboardCheck, title: "Compliance e integridade", text: "Padronize a análise de terceiros e registre cada consulta." },
    { icon: Building2, title: "Compras e licitações", text: "Verifique fornecedores antes de contratar, com histórico e fontes." },
    { icon: Scale, title: "Auditoria e controle", text: "Apoie auditorias com evidências rastreáveis e relatórios." },
    { icon: Gavel, title: "Jurídico e contratos", text: "Consulte sanções e contratos em um só lugar, sem juízo de valor." },
  ];
  return (
    <section className="section audience" id="para-quem">
      <div className="container">
        <div className="section-heading reveal">
          <h2>Para quem é a FornexIA</h2>
          <i />
          <p className="section-sub">Equipes que precisam decidir sobre fornecedores com mais segurança e menos retrabalho.</p>
        </div>
        <div className="audience-grid reveal">
          {items.map(({ icon: Icon, title, text }) => (
            <article className="audience-card" key={title}>
              <Icon aria-hidden="true" />
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- Perguntas frequentes ---------- */
const FAQ = [
  {
    q: "De onde vêm os dados?",
    a: "De portais públicos oficiais. Cada informação mostra a fonte e a data da captura, para que você possa conferir.",
  },
  {
    q: "A IA substitui a análise da minha equipe?",
    a: "Não. A IA organiza e resume as informações. A decisão é sempre da sua equipe, com as evidências à mão.",
  },
  {
    q: "Uma sanção em aberto significa irregularidade?",
    a: "Não necessariamente. Mostramos o que a fonte oficial informa, sem julgamento, e indicamos onde conferir.",
  },
  {
    q: "Como posso testar o sistema?",
    a: "Pelo botão “Testar o nosso sistema”, que leva à plataforma no site. Com a conta criada, você também cadastra seus números para consultar pelo WhatsApp.",
  },
  {
    q: "Posso integrar com os meus sistemas?",
    a: "A integração via API está em breve. Fale com a equipe para saber mais sobre o andamento.",
  },
  {
    q: "Como falo com a equipe?",
    a: "Pelos canais da seção de contato.",
  },
];

export function Faq() {
  return (
    <section className="section faq" id="faq">
      <div className="container faq-wrap">
        <div className="section-heading reveal">
          <h2>Perguntas frequentes</h2>
          <i />
        </div>
        <div className="faq-list reveal">
          {FAQ.map(({ q, a }) => (
            <details key={q}>
              <summary>
                {q} <ChevronDown aria-hidden="true" />
              </summary>
              <p>{a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- Chamada para testar + contato ---------- */
export function TestarCta() {
  return (
    <section className="cta-section" id="testar">
      <div className="container">
        <div className="cta-card cta-simple reveal">
          <Layers3 className="cta-icon" aria-hidden="true" />
          <h2>
            Veja a FornexIA
            <br />
            em funcionamento
          </h2>
          <div>
            <a href="#/testar" className="button">
              Testar o nosso sistema <ArrowRight aria-hidden="true" />
            </a>
            <p>
              <span>
                <BadgeCheck aria-hidden="true" /> Use pelo site
              </span>
              <span>
                <BadgeCheck aria-hidden="true" /> Ou pelo WhatsApp
              </span>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

type Channel = { icon: typeof Mail; label: string; hint: string; href: string; action: string };

export function Contato() {
  const { contact } = useContent();
  const channels: Channel[] = [
    {
      icon: WhatsappIcon as unknown as typeof Mail,
      label: "WhatsApp",
      hint: "Converse direto com a equipe",
      href: waLink(contact.whatsapp, WA_MSG),
      action: "Chamar no WhatsApp",
    },
    {
      icon: InstagramIcon as unknown as typeof Mail,
      label: "Instagram",
      hint: "Acompanhe as novidades",
      href: instagramUrl(contact.instagram),
      action: "Ver o Instagram",
    },
    {
      icon: LinkedinIcon as unknown as typeof Mail,
      label: "LinkedIn",
      hint: "Conheça a empresa e a equipe",
      href: contact.linkedin,
      action: "Ver o LinkedIn",
    },
    {
      icon: Mail,
      label: "E-mail",
      hint: contact.email || "Envie sua mensagem",
      href: contact.email ? `mailto:${contact.email}` : "",
      action: "Enviar e-mail",
    },
  ].filter((c) => c.href);   // canal sem endereço no admin não aparece (antes mostrava "Canal será divulgado em breve")
  return (
    <section className="section contact" id="contato">
      <div className="container">
        <div className="section-heading reveal">
          <h2>Fale com a gente</h2>
          <i />
          <p className="section-sub">
            Quer conhecer melhor a FornexIA ou conversar com a equipe? Escolha o canal que for mais prático
            para você.
          </p>
        </div>
        <div className="contact-grid reveal">
          {channels.map(({ icon: Icon, label, hint, href, action }) => {
            const body = (
              <>
                <span className="contact-ic">
                  <Icon aria-hidden="true" />
                </span>
                <h3>{label}</h3>
                <p>{href ? hint : "Em breve"}</p>
                <span className="contact-action">
                  {href ? action : "Canal será divulgado em breve"}
                  {href && <ArrowRight aria-hidden="true" />}
                  {href.startsWith("http") && <span className="sr-only"> (abre em nova aba)</span>}
                </span>
              </>
            );
            return href ? (
              <a
                className="contact-card"
                href={href}
                key={label}
                {...(href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}
              >
                {body}
              </a>
            ) : (
              <div className="contact-card off" key={label} aria-disabled="true">
                {body}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ---------- Rodapé ---------- */
export function SiteFooter({ brand }: { brand: React.ReactNode }) {
  const { contact, founders, history } = useContent();
  const wa = waLink(contact.whatsapp, WA_MSG);
  const ig = instagramUrl(contact.instagram);
  const li = contact.linkedin;
  const socials = [
    { label: "Instagram", href: ig, icon: InstagramIcon },
    { label: "WhatsApp", href: wa, icon: WhatsappIcon },
    { label: "LinkedIn", href: li, icon: LinkedinIcon },
  ].filter((s) => s.href);   // rede sem endereço no admin não aparece
  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div className="footer-about">
          {brand}
          <p>
            Inteligência em fornecedores com dados públicos, IA e evidências oficiais. Análises mais rápidas,
            seguras e rastreáveis.
          </p>
          {socials.length > 0 && (
            <div className="socials" aria-label="Redes sociais">
              {socials.map(({ label, href, icon: Icon }) => (
                <a key={label} href={href} target="_blank" rel="noopener noreferrer" aria-label={`${label} da FornexIA (abre em nova aba)`}>
                  <Icon />
                </a>
              ))}
            </div>
          )}
        </div>
        <nav aria-label="Empresa">
          <h3>Empresa</h3>
          <a href="#quem-somos">Quem somos</a>
          {history.text.trim() && <a href="#historia">Nossa história</a>}
          {founders.length > 0 && <a href="#fundadores">Fundadores</a>}
          <a href="#faq">Perguntas frequentes</a>
          <a href="#contato">Contato</a>
        </nav>
        <nav aria-label="Produto">
          <h3>Produto</h3>
          <a href="#conteudo">Como funciona</a>
          <a href="#recursos">Recursos</a>
          <a href="#planos">Planos</a>
          <a href="#/testar">Testar o nosso sistema</a>
        </nav>
        <div className="footer-contact">
          <h3>Contato</h3>
          {contact.email && <a href={`mailto:${contact.email}`}>{contact.email}</a>}
          {wa && (
            <a href={wa} target="_blank" rel="noopener noreferrer">
              WhatsApp
            </a>
          )}
          {!contact.email && !wa && <span>Canais em breve</span>}
          <a className="footer-btn" href="#/testar">
            Testar o nosso sistema <ArrowRight aria-hidden="true" />
          </a>
        </div>
      </div>
      <div className="container footer-bottom">
        <span>© {new Date().getFullYear()} FornexIA. Todos os direitos reservados.</span>
        <span className="footer-note">
          <Handshake aria-hidden="true" /> Dados públicos. Decisões seguras.
        </span>
        <a href="#/admin">Área administrativa</a>
      </div>
    </footer>
  );
}
