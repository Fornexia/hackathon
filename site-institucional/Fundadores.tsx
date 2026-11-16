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

export default function Fundadores() {
  const { founders } = useContent();
  // Sem fundadores cadastrados no admin, a seção não aparece (antes mostrava 3 cartões "Nome do fundador").
  if (!founders.length) return null;
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
          {founders.map((f) => <FounderCard f={f} key={f.id} />)}
        </div>
      </div>
    </section>
  );
}
