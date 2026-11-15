import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  CircleCheck,
  Download,
  FileJson,
  ImagePlus,
  KeyRound,
  Layers3,
  Lock,
  LogOut,
  Plus,
  RotateCcw,
  Save,
  ShieldAlert,
  Trash2,
  TriangleAlert,
  Upload,
  UserRound,
} from "lucide-react";
import {
  LIMITS,
  blankFounder,
  downloadJson,
  hasLocalOverride,
  instagramUrl,
  phone,
  processImage,
  readJsonFile,
  resetLocal,
  safeUrl,
  sanitize,
  saveLocal,
  storageUsedKB,
  useContent,
  type Founder,
  type SiteContent,
} from "./content";
import assistente from "./components/fornex-laptop/assets/assistente-laptop.jpg";
import areaTecnica from "./components/fornex-laptop/assets/area-tecnica.jpg";
import ThemeToggle from "./ThemeToggle";
import "./styles/admin.css";

/* ---------- senha local (NÃO é segurança real: tudo roda no navegador) ---------- */

const AUTH_KEY = "fornexia:admin:v1";
const SESSION_KEY = "fornexia:admin:session";
const hex = (b: ArrayBuffer) => [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");

async function derive(pass: string, salt: string) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(pass), "PBKDF2", false, [
    "deriveBits",
  ]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt: new TextEncoder().encode(salt), iterations: 150_000, hash: "SHA-256" },
    key,
    256,
  );
  return hex(bits);
}

function readAuth(): { salt: string; hash: string } | null {
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    const o = raw ? JSON.parse(raw) : null;
    return o && typeof o.salt === "string" && typeof o.hash === "string" ? o : null;
  } catch {
    return null;
  }
}

function Login({ onOk }: { onOk: () => void }) {
  const stored = useMemo(readAuth, []);
  const [pass, setPass] = useState("");
  const [pass2, setPass2] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const fails = useRef(0);
  const lockedUntil = useRef(0);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    if (!globalThis.crypto?.subtle) {
      setErr("Este navegador não permite a proteção por senha (precisa de https ou localhost).");
      return;
    }
    if (Date.now() < lockedUntil.current) {
      setErr("Muitas tentativas. Aguarde alguns segundos.");
      return;
    }
    setBusy(true);
    try {
      if (!stored) {
        if (pass.length < 8) return setErr("Use pelo menos 8 caracteres.");
        if (pass !== pass2) return setErr("As senhas não conferem.");
        const salt = hex(crypto.getRandomValues(new Uint8Array(16)).buffer);
        localStorage.setItem(AUTH_KEY, JSON.stringify({ salt, hash: await derive(pass, salt) }));
        sessionStorage.setItem(SESSION_KEY, "1");
        onOk();
      } else if ((await derive(pass, stored.salt)) === stored.hash) {
        fails.current = 0;
        sessionStorage.setItem(SESSION_KEY, "1");
        onOk();
      } else {
        fails.current += 1;
        if (fails.current >= 5) {
          lockedUntil.current = Date.now() + 30_000;
          fails.current = 0;
        }
        setErr("Senha incorreta.");
      }
    } catch {
      setErr("Não foi possível salvar a senha neste navegador.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main id="principal" className="admin-login">
      <form className="admin-login-card" onSubmit={submit} noValidate>
        <span className="admin-logo">
          <Layers3 aria-hidden="true" />
        </span>
        <h1>{stored ? "Área administrativa" : "Criar senha de administrador"}</h1>
        <p className="admin-muted">
          {stored
            ? "Digite a senha para editar o conteúdo do site."
            : "Defina uma senha para proteger esta página neste navegador."}
        </p>
        <label>
          Senha
          <input
            type="password"
            autoComplete={stored ? "current-password" : "new-password"}
            value={pass}
            onChange={(e) => setPass(e.target.value)}
            required
          />
        </label>
        {!stored && (
          <label>
            Repita a senha
            <input
              type="password"
              autoComplete="new-password"
              value={pass2}
              onChange={(e) => setPass2(e.target.value)}
              required
            />
          </label>
        )}
        {err && (
          <p className="admin-error" role="alert">
            <TriangleAlert aria-hidden="true" /> {err}
          </p>
        )}
        <button className="admin-btn primary" disabled={busy}>
          <KeyRound aria-hidden="true" /> {stored ? "Entrar" : "Criar senha e entrar"}
        </button>
        <a className="admin-back" href="#inicio">
          <ArrowLeft aria-hidden="true" /> Voltar ao site
        </a>
        <p className="admin-note">
          <ShieldAlert aria-hidden="true" /> Proteção local de demonstração: ela impede acessos casuais,
          mas não substitui um login com servidor.
        </p>
      </form>
    </main>
  );
}

/* ---------- painel ---------- */

type Tab = "fundadores" | "historia" | "contato" | "imagens" | "dados";

function FounderEditor({
  f,
  index,
  total,
  onChange,
  onMove,
  onRemove,
  onError,
}: {
  f: Founder;
  index: number;
  total: number;
  onChange: (f: Founder) => void;
  onMove: (dir: -1 | 1) => void;
  onRemove: () => void;
  onError: (m: string) => void;
}) {
  const file = useRef<HTMLInputElement>(null);

  async function pick(e: ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0];
    e.target.value = "";
    if (!picked) return;
    try {
      onChange({ ...f, photo: await processImage(picked, 640) });
    } catch (err) {
      onError(err instanceof Error ? err.message : "Não foi possível usar esta imagem.");
    }
  }

  const linkBad = f.linkedin.trim() !== "" && !safeUrl(f.linkedin);
  const waBad = f.whatsapp.trim() !== "" && !phone(f.whatsapp);

  return (
    <article className="admin-card">
      <div className="admin-photo">
        {f.photo ? (
          <img src={f.photo} alt={f.name ? `Foto de ${f.name}` : "Foto do fundador"} />
        ) : (
          <UserRound aria-hidden="true" />
        )}
        <input ref={file} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={pick} />
        <button type="button" className="admin-btn small" onClick={() => file.current?.click()}>
          <ImagePlus aria-hidden="true" /> {f.photo ? "Trocar foto" : "Adicionar foto"}
        </button>
        {f.photo && (
          <button type="button" className="admin-btn small ghost" onClick={() => onChange({ ...f, photo: "" })}>
            Remover foto
          </button>
        )}
      </div>

      <div className="admin-fields">
        <label>
          Nome
          <input
            value={f.name}
            maxLength={LIMITS.name}
            onChange={(e) => onChange({ ...f, name: e.target.value })}
            placeholder="Ex.: Maria Silva"
          />
        </label>
        <label>
          Cargo
          <input
            value={f.role}
            maxLength={LIMITS.role}
            onChange={(e) => onChange({ ...f, role: e.target.value })}
            placeholder="Ex.: CEO e cofundadora"
          />
        </label>
        <label className="wide">
          Biografia
          <textarea
            rows={5}
            value={f.bio}
            maxLength={LIMITS.bio}
            onChange={(e) => onChange({ ...f, bio: e.target.value })}
            placeholder="Conte a trajetória e a experiência da pessoa."
          />
          <small>
            {f.bio.length}/{LIMITS.bio}
          </small>
        </label>
        <label>
          WhatsApp (opcional)
          <input
            value={f.whatsapp}
            maxLength={20}
            onChange={(e) => onChange({ ...f, whatsapp: e.target.value })}
            placeholder="(87) 99999-9999"
            inputMode="tel"
            aria-invalid={waBad}
          />
          {waBad ? (
            <small className="bad">Informe com DDD. Ex.: (87) 99999-9999</small>
          ) : (
            <small>Para os visitantes falarem direto com esta pessoa</small>
          )}
        </label>
        <label>
          LinkedIn (opcional)
          <input
            value={f.linkedin}
            maxLength={LIMITS.url}
            onChange={(e) => onChange({ ...f, linkedin: e.target.value })}
            placeholder="https://www.linkedin.com/in/..."
            inputMode="url"
            aria-invalid={linkBad}
          />
          {linkBad && <small className="bad">Use um link que comece com https://</small>}
        </label>
      </div>

      <div className="admin-card-actions">
        <button type="button" className="admin-icon" onClick={() => onMove(-1)} disabled={index === 0} aria-label="Mover para cima">
          <ArrowUp aria-hidden="true" />
        </button>
        <button type="button" className="admin-icon" onClick={() => onMove(1)} disabled={index === total - 1} aria-label="Mover para baixo">
          <ArrowDown aria-hidden="true" />
        </button>
        <button type="button" className="admin-icon danger" onClick={onRemove} aria-label={`Remover ${f.name || "fundador"}`}>
          <Trash2 aria-hidden="true" />
        </button>
      </div>
    </article>
  );
}

function ImageSlot({
  title,
  help,
  value,
  fallback,
  onChange,
  onError,
}: {
  title: string;
  help: string;
  value: string;
  fallback: string;
  onChange: (v: string) => void;
  onError: (m: string) => void;
}) {
  const file = useRef<HTMLInputElement>(null);
  async function pick(e: ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0];
    e.target.value = "";
    if (!picked) return;
    try {
      onChange(await processImage(picked, 1600));
    } catch (err) {
      onError(err instanceof Error ? err.message : "Não foi possível usar esta imagem.");
    }
  }
  return (
    <article className="admin-card slot">
      <div className="slot-preview">
        <img src={value || fallback} alt={`Pré-visualização: ${title}`} />
        {!value && <span className="slot-tag">Imagem padrão</span>}
      </div>
      <div>
        <h2>{title}</h2>
        <p className="admin-muted">{help}</p>
        <input ref={file} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={pick} />
        <div className="admin-row">
          <button type="button" className="admin-btn small" onClick={() => file.current?.click()}>
            <Upload aria-hidden="true" /> Enviar nova imagem
          </button>
          {value && (
            <button type="button" className="admin-btn small ghost" onClick={() => onChange("")}>
              <RotateCcw aria-hidden="true" /> Voltar ao padrão
            </button>
          )}
        </div>
      </div>
    </article>
  );
}

function Panel({ onLogout }: { onLogout: () => void }) {
  const content = useContent();
  const [draft, setDraft] = useState<SiteContent>(content);
  const [tab, setTab] = useState<Tab>("fundadores");
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const importRef = useRef<HTMLInputElement>(null);

  // compara sem a data de atualização, e já normalizado (telefone, links), para o aviso não ficar preso
  const same = (a: SiteContent, b: SiteContent) =>
    JSON.stringify({ ...sanitize(a), updatedAt: "" }) === JSON.stringify({ ...sanitize(b), updatedAt: "" });
  const dirty = useMemo(() => !same(draft, content), [draft, content]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  useEffect(() => {
    if (!msg) return;
    const t = setTimeout(() => setMsg(null), 6000);
    return () => clearTimeout(t);
  }, [msg]);

  const err = (text: string) => setMsg({ kind: "err", text });
  const setFounders = (founders: Founder[]) => setDraft((d) => ({ ...d, founders }));
  const setHistory = (patch: Partial<SiteContent["history"]>) =>
    setDraft((d) => ({ ...d, history: { ...d.history, ...patch } }));
  const setContact = (patch: Partial<SiteContent["contact"]>) =>
    setDraft((d) => ({ ...d, contact: { ...d.contact, ...patch } }));
  const setTrial = (i: number, patch: Partial<SiteContent["trial"][number]>) =>
    setDraft((d) => ({ ...d, trial: d.trial.map((t, k) => (k === i ? { ...t, ...patch } : t)) }));

  function save() {
    const bad = draft.founders.find((f) => f.name.trim() === "");
    if (bad) return err("Todo fundador precisa ter um nome antes de salvar.");
    const badWa = draft.founders.find((f) => f.whatsapp.trim() !== "" && !phone(f.whatsapp));
    if (badWa) return err(`O WhatsApp de ${badWa.name} é inválido. Informe com DDD.`);
    const c = draft.contact;
    if (c.whatsapp.trim() !== "" && !phone(c.whatsapp)) return err("O WhatsApp da empresa é inválido. Informe com DDD.");
    if (c.instagram.trim() !== "" && !instagramUrl(c.instagram)) return err("Instagram inválido. Use @usuario ou um link https.");
    if (c.linkedin.trim() !== "" && !safeUrl(c.linkedin)) return err("O link do LinkedIn precisa começar com https://");
    const clean = sanitize(draft);
    const r = saveLocal(clean);
    if (r.ok) {
      setDraft(clean);
      setMsg({ kind: "ok", text: "Alterações salvas neste navegador." });
    } else err(r.error);
  }

  function move(i: number, dir: -1 | 1) {
    const list = [...draft.founders];
    const j = i + dir;
    if (j < 0 || j >= list.length) return;
    [list[i], list[j]] = [list[j], list[i]];
    setFounders(list);
  }

  function remove(i: number) {
    const f = draft.founders[i];
    if (window.confirm(`Remover ${f.name || "este fundador"}? Isso só vale depois de salvar.`)) {
      setFounders(draft.founders.filter((_, k) => k !== i));
    }
  }

  async function importFile(e: ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0];
    e.target.value = "";
    if (!picked) return;
    try {
      const data = await readJsonFile(picked);
      if (window.confirm("Substituir o conteúdo em edição pelo arquivo importado?")) {
        setDraft(data);
        setMsg({ kind: "ok", text: "Arquivo carregado. Clique em Salvar para aplicar." });
      }
    } catch (error) {
      err(error instanceof Error ? error.message : "Não foi possível ler o arquivo.");
    }
  }

  function discardLocal() {
    if (window.confirm("Descartar tudo que foi salvo neste navegador e voltar ao conteúdo publicado?")) {
      resetLocal();
      setMsg({ kind: "ok", text: "Alterações locais descartadas." });
    }
  }

  // sem alterações locais salvas, o rascunho acompanha o conteúdo publicado
  // (cobre o carregamento do content.json e o "descartar alterações locais")
  useEffect(() => {
    if (!hasLocalOverride()) setDraft(content);
  }, [content]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "fundadores", label: "Fundadores" },
    { id: "historia", label: "História da empresa" },
    { id: "contato", label: "Contato e testes" },
    { id: "imagens", label: "Imagens do site" },
    { id: "dados", label: "Dados e publicação" },
  ];

  return (
    <div className="admin-shell">
      <header className="admin-top">
        <div className="admin-top-in">
          <span className="admin-brand">
            <Layers3 aria-hidden="true" /> Fornex<b>IA</b> <em>Admin</em>
          </span>
          <div className="admin-row">
            <ThemeToggle />
            <a className="admin-btn small ghost" href="#inicio">
              <ArrowLeft aria-hidden="true" /> Ver o site
            </a>
            <button
              className="admin-btn small ghost"
              onClick={() => {
                sessionStorage.removeItem(SESSION_KEY);
                onLogout();
              }}
            >
              <LogOut aria-hidden="true" /> Sair
            </button>
          </div>
        </div>
      </header>

      <main id="principal" className="admin-main">
        <div className="admin-title">
          <div>
            <h1>Painel de conteúdo</h1>
            <p className="admin-muted">Edite fundadores, fotos e imagens do site.</p>
          </div>
          <div className="admin-row">
            {dirty && <span className="admin-dirty">Alterações não salvas</span>}
            <button className="admin-btn ghost" onClick={() => setDraft(content)} disabled={!dirty}>
              Descartar
            </button>
            <button className="admin-btn primary" onClick={save} disabled={!dirty}>
              <Save aria-hidden="true" /> Salvar alterações
            </button>
          </div>
        </div>

        <div className="admin-live" role="status" aria-live="polite">
          {msg && (
            <p className={msg.kind === "ok" ? "admin-ok" : "admin-error"}>
              {msg.kind === "ok" ? <CircleCheck aria-hidden="true" /> : <TriangleAlert aria-hidden="true" />} {msg.text}
            </p>
          )}
        </div>

        <nav className="admin-tabs" aria-label="Seções do painel">
          {tabs.map((t) => (
            <button
              key={t.id}
              aria-current={tab === t.id ? "page" : undefined}
              className={tab === t.id ? "on" : ""}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {tab === "fundadores" && (
          <section aria-label="Fundadores" className="admin-stack">
            {draft.founders.length === 0 && (
              <p className="admin-empty">
                Nenhum fundador cadastrado. O site mostra espaços reservados até você adicionar o primeiro.
              </p>
            )}
            {draft.founders.map((f, i) => (
              <FounderEditor
                key={f.id}
                f={f}
                index={i}
                total={draft.founders.length}
                onChange={(nf) => setFounders(draft.founders.map((x) => (x.id === f.id ? nf : x)))}
                onMove={(d) => move(i, d)}
                onRemove={() => remove(i)}
                onError={err}
              />
            ))}
            <button
              className="admin-btn"
              disabled={draft.founders.length >= LIMITS.founders}
              onClick={() => setFounders([...draft.founders, blankFounder()])}
            >
              <Plus aria-hidden="true" /> Adicionar fundador
            </button>
          </section>
        )}

        {tab === "historia" && (
          <section aria-label="História da empresa" className="admin-stack">
            <article className="admin-card info">
              <h2>História da empresa</h2>
              <p className="admin-muted">
                Aparece na página inicial, na seção “Nossa história”. Conte como a equipe se conheceu e como o projeto
                surgiu. Separe os parágrafos com uma linha em branco. O texto atual é só um exemplo.
              </p>
              <div className="admin-fields">
                <label className="wide">
                  Título da seção
                  <input
                    value={draft.history.title}
                    maxLength={LIMITS.historyTitle}
                    onChange={(e) => setHistory({ title: e.target.value })}
                  />
                </label>
                <label className="wide">
                  Texto
                  <textarea
                    rows={14}
                    value={draft.history.text}
                    maxLength={LIMITS.history}
                    onChange={(e) => setHistory({ text: e.target.value })}
                  />
                  <small>
                    {draft.history.text.length}/{LIMITS.history}
                  </small>
                </label>
              </div>
            </article>
          </section>
        )}

        {tab === "contato" && (
          <section aria-label="Contato e testes" className="admin-stack">
            <article className="admin-card info">
              <h2>Redes sociais e contato da empresa</h2>
              <p className="admin-muted">
                Aparecem no rodapé, na seção “Fale com a gente” e na opção de WhatsApp da página de teste. Campos
                vazios ficam como “em breve”.
              </p>
              <div className="admin-fields">
                <label>
                  WhatsApp da empresa
                  <input
                    value={draft.contact.whatsapp}
                    maxLength={20}
                    inputMode="tel"
                    placeholder="(87) 99999-9999"
                    onChange={(e) => setContact({ whatsapp: e.target.value })}
                  />
                  <small>Informe com DDD. O código do Brasil (55) é acrescentado sozinho.</small>
                </label>
                <label>
                  Instagram
                  <input
                    value={draft.contact.instagram}
                    maxLength={LIMITS.url}
                    placeholder="@fornexia ou https://instagram.com/..."
                    onChange={(e) => setContact({ instagram: e.target.value })}
                  />
                </label>
                <label>
                  LinkedIn da empresa
                  <input
                    value={draft.contact.linkedin}
                    maxLength={LIMITS.url}
                    inputMode="url"
                    placeholder="https://www.linkedin.com/company/..."
                    onChange={(e) => setContact({ linkedin: e.target.value })}
                  />
                </label>
                <label>
                  E-mail
                  <input
                    value={draft.contact.email}
                    maxLength={120}
                    inputMode="email"
                    placeholder="contato@empresa.com.br"
                    onChange={(e) => setContact({ email: e.target.value })}
                  />
                </label>
              </div>
            </article>

            {draft.trial.map((t, i) => (
              <article className="admin-card info" key={i}>
                <h2>Página “Testar o nosso sistema”: cartão do site</h2>
                <p className="admin-muted">
                  {i === 0 ? "Acesso ao sistema pelo site." : "Segundo site (o link pode ser adicionado depois)."} Sem link, o
                  cartão aparece como “em breve”.
                </p>
                <div className="admin-fields">
                  <label>
                    Título
                    <input value={t.title} maxLength={LIMITS.name} onChange={(e) => setTrial(i, { title: e.target.value })} />
                  </label>
                  <label>
                    Link (https://...)
                    <input
                      value={t.url}
                      maxLength={LIMITS.url}
                      inputMode="url"
                      placeholder="https://..."
                      aria-invalid={t.url.trim() !== "" && !safeUrl(t.url)}
                      onChange={(e) => setTrial(i, { url: e.target.value })}
                    />
                  </label>
                  <label className="wide">
                    Descrição
                    <input
                      value={t.description}
                      maxLength={LIMITS.desc}
                      onChange={(e) => setTrial(i, { description: e.target.value })}
                    />
                  </label>
                </div>
              </article>
            ))}
            <p className="admin-note">
              <Lock aria-hidden="true" /> O outro cartão da página de teste é o WhatsApp da empresa, definido acima.
            </p>
          </section>
        )}

        {tab === "imagens" && (
          <section aria-label="Imagens do site" className="admin-stack">
            <ImageSlot
              title="Tela do assistente (início)"
              help="Aparece no notebook da primeira dobra. Recomendado: captura 16:10, até 1600 px."
              value={draft.images.hero}
              fallback={assistente}
              onChange={(v) => setDraft({ ...draft, images: { ...draft.images, hero: v } })}
              onError={err}
            />
            <ImageSlot
              title="Tela da área técnica (recursos)"
              help="Aparece no notebook da seção Principais recursos."
              value={draft.images.features}
              fallback={areaTecnica}
              onChange={(v) => setDraft({ ...draft, images: { ...draft.images, features: v } })}
              onError={err}
            />
          </section>
        )}

        {tab === "dados" && (
          <section aria-label="Dados e publicação" className="admin-stack">
            <article className="admin-card info">
              <h2>Como publicar para todos os visitantes</h2>
              <ol>
                <li>Salve as alterações aqui.</li>
                <li>Clique em <b>Exportar content.json</b>.</li>
                <li>Substitua o arquivo <code>public/content.json</code> do projeto e faça o deploy.</li>
              </ol>
              <p className="admin-muted">
                Sem servidor, o que você salva fica só neste navegador. Para o site atualizar sozinho para todos,
                é preciso integrar um back-end com login (próximo passo recomendado).
              </p>
            </article>
            <article className="admin-card info">
              <div className="admin-row wrap">
                <button className="admin-btn primary" onClick={() => downloadJson(draft)}>
                  <Download aria-hidden="true" /> Exportar content.json
                </button>
                <input ref={importRef} type="file" accept="application/json,.json" hidden onChange={importFile} />
                <button className="admin-btn" onClick={() => importRef.current?.click()}>
                  <FileJson aria-hidden="true" /> Importar arquivo
                </button>
                <button className="admin-btn danger" onClick={discardLocal} disabled={!hasLocalOverride()}>
                  <RotateCcw aria-hidden="true" /> Descartar alterações locais
                </button>
              </div>
              <p className="admin-muted">
                Espaço usado neste navegador: {storageUsedKB()} KB (limite típico de 5 MB).
              </p>
              <p className="admin-note">
                <Lock aria-hidden="true" /> As fotos são reduzidas e recomprimidas ao enviar, o que também remove
                dados ocultos como a localização.
              </p>
            </article>
          </section>
        )}
      </main>
    </div>
  );
}

export default function Admin() {
  const [ok, setOk] = useState(() => {
    try {
      return sessionStorage.getItem(SESSION_KEY) === "1" && readAuth() !== null;
    } catch {
      return false;
    }
  });
  return ok ? <Panel onLogout={() => setOk(false)} /> : <Login onOk={() => setOk(true)} />;
}
