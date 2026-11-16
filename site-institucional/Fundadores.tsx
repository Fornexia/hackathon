import { UserRound } from "lucide-react";
import { useContent, waLink, type Founder } from "./content";
import { LinkedinIcon, WhatsappIcon } from "./Social";

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

function FounderCard({ f }: { f: Founder }) {
  return (
    <article className="founder-card">
      <div className="founder-photo">
        {f.photo ? (
          <img src={f.photo} alt={`Foto de ${f.name}`} loading="lazy" width={320} height={320} />
        ) : (
          <span aria-hidden="true">{initials(f.name)}</span>
        )}
      </div>
      <h3>{f.name}</h3>
      {f.role && <p className="founder-role">{f.role}</p>}
      {f.bio && <p className="founder-bio">{f.bio}</p>}
      {(f.whatsapp || f.linkedin) && (
        <div className="founder-links">
          {f.whatsapp && (
            <a
              className="founder-link"
              href={waLink(f.whatsapp, `Olá, ${f.name}! Vim pelo site da FornexIA.`)}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Conversar com ${f.name} no WhatsApp (abre em nova aba)`}
            >
              <WhatsappIcon /> WhatsApp
            </a>
          )}
          {f.linkedin && (
            <a
              className="founder-link"
              href={f.linkedin}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`LinkedIn de ${f.name} (abre em nova aba)`}
            >
              <LinkedinIcon /> LinkedIn
            </a>
          )}
        </div>
      )}
    </article>
  );
}

function Placeholder({ n }: { n: number }) {
  return (
    <article className="founder-card founder-placeholder" aria-label={`Espaço reservado ${n}`}>
      <div className="founder-photo">
        <UserRound aria-hidden="true" />
      </div>
      <h3>Nome do fundador</h3>
      <p className="founder-role">Cargo</p>
      <p className="founder-bio">A biografia e a foto serão adicionadas em breve.</p>
    </article>
  );
}

export default function Fundadores() {
  const { founders } = useContent();
  return (
    <section className="section founders" id="fundadores">
      <div className="container">
        <div className="section-heading reveal">
          <h2>Quem está por trás da FornexIA</h2>
          <i />
          <p className="section-sub">
            Uma equipe que une dados públicos, tecnologia e compliance para tornar a análise de
            fornecedores mais simples e confiável.
          </p>
        </div>
        <div className="founders-grid reveal">
          {founders.length > 0
            ? founders.map((f) => <FounderCard f={f} key={f.id} />)
            : [1, 2, 3].map((n) => <Placeholder n={n} key={n} />)}
        </div>
      </div>
    </section>
  );
}
