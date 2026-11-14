import { ArrowLeft, ArrowRight, Clock3, Layers3, MonitorSmartphone } from "lucide-react";
import { useContent, waLink } from "./content";
import { WhatsappIcon } from "./Social";
import ThemeToggle from "./ThemeToggle";
import "./styles/testar.css";

const WA_MSG = "Olá! Gostaria de testar o sistema da FornexIA.";

type Opt = {
  icon: React.ReactNode;
  title: string;
  text: string;
  href: string;
  action: string;
  external: boolean;
  soon: string;
};

export default function Testar() {
  const { trial, contact } = useContent();
  const wa = waLink(contact.whatsapp, WA_MSG);
  const options: Opt[] = [
    {
      icon: <MonitorSmartphone aria-hidden="true" />,
      title: trial[0].title,
      text: trial[0].description,
      href: trial[0].url,
      action: "Acessar agora",
      external: true,
      soon: "Link disponível em breve",
    },
    {
      icon: <WhatsappIcon aria-hidden="true" />,
      title: "Testar pelo WhatsApp",
      text: "Converse com a equipe e faça suas consultas de fornecedores direto pelo aplicativo.",
      href: wa,
      action: "Conversar no WhatsApp",
      external: true,
      soon: "WhatsApp disponível em breve",
    },
  ];

  return (
    <div className="try-page">
      <header className="try-top">
        <div className="container try-top-in">
          <a href="#inicio" className="brand" aria-label="FornexIA — página inicial">
            <span className="brand-mark">
              <Layers3 />
            </span>
            <span className="brand-name">
              Fornex<span>IA</span>
            </span>
          </a>
          <div className="try-top-actions">
            <ThemeToggle />
            <a className="try-back" href="#inicio">
              <ArrowLeft aria-hidden="true" /> Voltar ao site
            </a>
          </div>
        </div>
      </header>

      <main id="principal" className="container try-main">
        <span className="eyebrow">Teste a FornexIA</span>
        <h1>Como você prefere testar o nosso sistema?</h1>
        <p className="try-lead">
          Escolha uma das opções abaixo. Em todas, as respostas trazem a fonte oficial de cada informação.
        </p>

        <div className="try-grid">
          {options.map((o) => {
            const inner = (
              <>
                <span className="try-ic">{o.icon}</span>
                <h2>{o.title}</h2>
                <p>{o.text}</p>
                <span className="try-action">
                  {o.href ? (
                    <>
                      {o.action} <ArrowRight aria-hidden="true" />
                    </>
                  ) : (
                    <>
                      <Clock3 aria-hidden="true" /> {o.soon}
                    </>
                  )}
                </span>
              </>
            );
            return o.href ? (
              <a
                key={o.title}
                className="try-card"
                href={o.href}
                {...(o.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
              >
                {inner}
              </a>
            ) : (
              <div key={o.title} className="try-card off" aria-disabled="true">
                {inner}
              </div>
            );
          })}
        </div>

        <p className="try-note">
          Dúvidas? Veja as <a href="#faq">perguntas frequentes</a> ou fale com a <a href="#contato">equipe</a>.
        </p>
      </main>
    </div>
  );
}
