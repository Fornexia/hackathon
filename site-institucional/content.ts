import { useSyncExternalStore } from "react";

/**
 * Conteúdo editável do site (fundadores e imagens).
 *
 * Como funciona hoje (sem servidor):
 *  - "publicado": arquivo /content.json (pasta public/), igual para todos os visitantes.
 *  - "local": alterações feitas na página de admin, salvas só neste navegador (localStorage).
 *  O site mostra o conteúdo local, se existir, senão o publicado.
 *  Para publicar para todos: exporte o JSON no admin e substitua public/content.json.
 */

export type Founder = {
  id: string;
  name: string;
  role: string;
  bio: string;
  /** data URL (jpeg/png/webp) ou "" */
  photo: string;
  /** https://... ou "" */
  linkedin: string;
  /** só dígitos com DDI (ex.: 5587999999999) ou "" */
  whatsapp: string;
};

export type Contact = {
  /** só dígitos com DDI ou "" */
  whatsapp: string;
  /** https://... ou "" */
  instagram: string;
  /** https://... ou "" */
  linkedin: string;
  email: string;
};

/** Opção da página "Testar o nosso sistema" (url vazia = "em breve"). */
export type TrialOption = { title: string; description: string; url: string };

export type SiteImages = {
  /** tela do notebook no início ("" = imagem padrão) */
  hero: string;
  /** tela do notebook em Recursos ("" = imagem padrão) */
  features: string;
};

/** História da empresa: texto livre; parágrafos separados por linha em branco. */
export type History = { title: string; text: string };

export type SiteContent = {
  version: 1;
  founders: Founder[];
  images: SiteImages;
  history: History;
  contact: Contact;
  trial: TrialOption[];
  updatedAt: string;
};

export const LIMITS = { name: 80, role: 80, bio: 1200, url: 300, founders: 12, desc: 200, historyTitle: 80, history: 3000 } as const;

const KEY = "fornexia:content:v1";
const IMG_RE = /^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/;
const MAX_IMG_CHARS = 3_000_000;

export const defaultTrial = (): TrialOption[] => [
  {
    title: "Usar o sistema pelo site",
    description: "Acesse a plataforma no navegador e faça sua primeira consulta de fornecedor.",
    url: "",
  },
];

/** Texto de exemplo (fictício). Deve ser trocado no painel administrativo. */
export const defaultHistory = (): History => ({
  title: "Como tudo começou",
  text:
    "A FornexIA nasceu de uma conversa entre colegas que viviam o mesmo problema: conferir um fornecedor exigia abrir vários portais públicos, comparar informações e registrar tudo à mão.\n\n" +
    "Ao longo de conversas e testes, a equipe percebeu que dados públicos já existiam, mas estavam espalhados. Surgiu a ideia de reuni-los em um só lugar, com a fonte oficial e a data de cada informação.\n\n" +
    "Hoje, o projeto segue com o mesmo propósito: tornar a análise de fornecedores mais rápida, segura e transparente. (Texto de exemplo, a ser substituído pela história real da equipe.)",
});

export const emptyContent = (): SiteContent => ({
  version: 1,
  founders: [],
  images: { hero: "", features: "" },
  history: defaultHistory(),
  contact: { whatsapp: "", instagram: "", linkedin: "", email: "contato@fornexia.com.br" },
  trial: defaultTrial(),
  updatedAt: "",
});

const text = (v: unknown, max: number) => (typeof v === "string" ? v.trim().slice(0, max) : "");
const image = (v: unknown) =>
  typeof v === "string" && v.length < MAX_IMG_CHARS && IMG_RE.test(v) ? v : "";

/** Só aceita links http(s); bloqueia javascript:, data: etc. */
export function safeUrl(v: string): string {
  try {
    const u = new URL(v.trim());
    return u.protocol === "https:" || u.protocol === "http:" ? u.href.slice(0, LIMITS.url) : "";
  } catch {
    return "";
  }
}

/** Telefone só com dígitos e DDI. 10 ou 11 dígitos = Brasil (acrescenta 55). Inválido = "". */
export function phone(v: unknown): string {
  if (typeof v !== "string") return "";
  let d = v.replace(/\D/g, "");
  if (d.length === 10 || d.length === 11) d = "55" + d;
  return /^\d{12,15}$/.test(d) ? d : "";
}

export const waLink = (num: string, msg = "") =>
  num ? `https://wa.me/${num}${msg ? `?text=${encodeURIComponent(msg)}` : ""}` : "";

/** Aceita "@usuario", "usuario" ou um link https. */
export function instagramUrl(v: unknown): string {
  if (typeof v !== "string") return "";
  const s = v.trim();
  if (/^@?[A-Za-z0-9._]{1,30}$/.test(s)) return `https://www.instagram.com/${s.replace(/^@/, "")}/`;
  return safeUrl(s);
}

const email = (v: unknown) => {
  const s = text(v, 120);
  return /^[^\s@<>"]+@[^\s@<>"]+\.[^\s@<>"]+$/.test(s) ? s : "";
};

export const newId = () =>
  globalThis.crypto?.randomUUID?.() ?? `f-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export function blankFounder(): Founder {
  return { id: newId(), name: "", role: "", bio: "", photo: "", linkedin: "", whatsapp: "" };
}

/** Valida e limpa qualquer dado vindo de fora (arquivo, localStorage, JSON publicado). */
export function sanitize(raw: unknown): SiteContent {
  const base = emptyContent();
  if (!raw || typeof raw !== "object") return base;
  const r = raw as Record<string, unknown>;
  const list = Array.isArray(r.founders) ? r.founders.slice(0, LIMITS.founders) : [];
  base.founders = list
    .map((f): Founder | null => {
      if (!f || typeof f !== "object") return null;
      const o = f as Record<string, unknown>;
      const name = text(o.name, LIMITS.name);
      if (!name) return null;
      return {
        id: text(o.id, 60) || newId(),
        name,
        role: text(o.role, LIMITS.role),
        bio: text(o.bio, LIMITS.bio),
        photo: image(o.photo),
        linkedin: typeof o.linkedin === "string" ? safeUrl(o.linkedin) : "",
        whatsapp: phone(o.whatsapp),
      };
    })
    .filter((f): f is Founder => f !== null);
  const imgs = (r.images && typeof r.images === "object" ? r.images : {}) as Record<string, unknown>;
  base.images = { hero: image(imgs.hero), features: image(imgs.features) };
  if (r.history && typeof r.history === "object") {
    const h = r.history as Record<string, unknown>;
    const def = defaultHistory();
    const txt = typeof h.text === "string" ? h.text.replace(/\r\n/g, "\n").trim().slice(0, LIMITS.history) : "";
    base.history = { title: text(h.title, LIMITS.historyTitle) || def.title, text: txt || def.text };
  }
  if (r.contact && typeof r.contact === "object") {
    const c = r.contact as Record<string, unknown>;
    base.contact = {
      whatsapp: phone(c.whatsapp),
      instagram: instagramUrl(c.instagram),
      linkedin: typeof c.linkedin === "string" ? safeUrl(c.linkedin) : "",
      email: email(c.email),
    };
  }
  if (Array.isArray(r.trial)) {
    const d = defaultTrial();
    base.trial = d.map((def, i) => {
      const o = (r.trial as unknown[])[i];
      if (!o || typeof o !== "object") return def;
      const t = o as Record<string, unknown>;
      return {
        title: text(t.title, LIMITS.name) || def.title,
        description: text(t.description, LIMITS.desc) || def.description,
        url: typeof t.url === "string" ? safeUrl(t.url) : "",
      };
    });
  }
  base.updatedAt = text(r.updatedAt, 40);
  return base;
}

/* ---------- armazenamento ---------- */

let published: SiteContent = emptyContent();
let local: SiteContent | null = readLocal();
let snapshot: SiteContent = local ?? published;
const listeners = new Set<() => void>();

function readLocal(): SiteContent | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? sanitize(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

function emit() {
  snapshot = local ?? published;
  listeners.forEach((l) => l());
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

export function useContent(): SiteContent {
  return useSyncExternalStore(subscribe, () => snapshot, () => snapshot);
}

export const hasLocalOverride = () => local !== null;

export function storageUsedKB(): number {
  try {
    return Math.round(((localStorage.getItem(KEY) ?? "").length * 2) / 1024);
  } catch {
    return 0;
  }
}

export function saveLocal(content: SiteContent): { ok: true } | { ok: false; error: string } {
  const clean = sanitize(content);
  clean.updatedAt = new Date().toISOString();
  try {
    localStorage.setItem(KEY, JSON.stringify(clean));
  } catch {
    return {
      ok: false,
      error: "Não foi possível salvar: o espaço do navegador está cheio. Use fotos menores ou remova algumas.",
    };
  }
  local = clean;
  emit();
  return { ok: true };
}

export function resetLocal() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignora */
  }
  local = null;
  emit();
}

async function loadPublished() {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}content.json`, { cache: "no-cache" });
    if (!res.ok) return;
    published = sanitize(await res.json());
    emit();
  } catch {
    /* sem content.json: segue vazio */
  }
}

if (typeof window !== "undefined") {
  void loadPublished();
  window.addEventListener("storage", (e) => {
    if (e.key === KEY) {
      local = readLocal();
      emit();
    }
  });
}

/* ---------- imagens e arquivos ---------- */

/** Redimensiona e recomprime em JPEG (também remove metadados EXIF, como a localização). */
export async function processImage(file: File, maxSide: number): Promise<string> {
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) throw new Error("Use uma imagem JPG, PNG ou WebP.");
  if (file.size > 10 * 1024 * 1024) throw new Error("A imagem passa de 10 MB.");
  const bmp = await createImageBitmap(file);
  const ratio = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const w = Math.max(1, Math.round(bmp.width * ratio));
  const h = Math.max(1, Math.round(bmp.height * ratio));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Seu navegador não conseguiu processar a imagem.");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  ctx.drawImage(bmp, 0, 0, w, h);
  bmp.close?.();
  const out = canvas.toDataURL("image/jpeg", 0.85);
  if (out.length >= MAX_IMG_CHARS) throw new Error("A imagem continua grande demais. Use uma menor.");
  return out;
}

export function downloadJson(content: SiteContent, filename = "content.json") {
  const clean = sanitize(content);
  clean.updatedAt = new Date().toISOString();
  const blob = new Blob([JSON.stringify(clean, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function readJsonFile(file: File): Promise<SiteContent> {
  if (file.size > 12 * 1024 * 1024) throw new Error("O arquivo passa de 12 MB.");
  let parsed: unknown;
  try {
    parsed = JSON.parse(await file.text());
  } catch {
    throw new Error("O arquivo não é um JSON válido.");
  }
  return sanitize(parsed);
}
