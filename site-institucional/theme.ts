import { useSyncExternalStore } from "react";

/** Tema do site: "dark" (padrão do projeto) ou "light". Segue o sistema até a pessoa escolher. */
export type Theme = "light" | "dark";

const KEY = "fornexia:theme";
const listeners = new Set<() => void>();

function stored(): Theme | null {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : null;
  } catch {
    return null;
  }
}

const system = (): Theme =>
  typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";

let current: Theme = typeof window === "undefined" ? "dark" : (stored() ?? system());

function apply(t: Theme) {
  document.documentElement.dataset.theme = t;
}

/** Chamar uma vez antes de renderizar, para não piscar o tema errado. */
export function initTheme() {
  apply(current);
  if (typeof matchMedia === "function") {
    matchMedia("(prefers-color-scheme: light)").addEventListener("change", (e) => {
      if (!stored()) setTheme(e.matches ? "light" : "dark", false);
    });
  }
}

export function setTheme(t: Theme, persist = true) {
  current = t;
  if (persist) {
    try {
      localStorage.setItem(KEY, t);
    } catch {
      /* sem armazenamento: vale só nesta visita */
    }
  }
  apply(t);
  listeners.forEach((l) => l());
}

export function useTheme(): Theme {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => current,
    () => "dark" as Theme,
  );
}
