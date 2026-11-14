import { useEffect, useState } from "react";

/** Rota por hash: "#/admin" -> "admin"; qualquer outro hash (ex.: "#planos") -> "" (site). */
export function useHashRoute(): string {
  const read = () => (location.hash.startsWith("#/") ? location.hash.slice(2).split("?")[0] : "");
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const on = () => setRoute(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

/** true depois de rolar a página mais que `px` pixels. */
export function useScrolled(px = 24): boolean {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > px);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, [px]);
  return scrolled;
}

/** Revela elementos ".reveal" quando entram na tela. Respeita "reduzir movimento". */
export function useReveal(dep: unknown) {
  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>(".reveal:not(.in)"));
    if (!els.length) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || !("IntersectionObserver" in window)) {
      els.forEach((e) => e.classList.add("in"));
      return;
    }
    document.documentElement.classList.add("js-reveal");
    const show = (el: Element) => el.classList.add("in");
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((en) => {
          if (en.isIntersecting) {
            show(en.target);
            io.unobserve(en.target);
          }
        }),
      { threshold: 0, rootMargin: "0px 0px 120px 0px" },
    );
    els.forEach((e) => io.observe(e));

    // Garantia extra: nenhum bloco pode ficar invisível depois de um salto por link (âncora).
    // Revela tudo que estiver na tela ou acima dela, mesmo que o observador não tenha disparado.
    let timer = 0;
    const sweep = () => {
      els.forEach((e) => {
        if (!e.classList.contains("in") && e.getBoundingClientRect().top < window.innerHeight + 160) show(e);
      });
    };
    const onMove = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(sweep, 120);
    };
    window.addEventListener("scroll", onMove, { passive: true });
    window.addEventListener("hashchange", onMove);
    window.addEventListener("resize", onMove);
    timer = window.setTimeout(sweep, 400);
    return () => {
      io.disconnect();
      window.clearTimeout(timer);
      window.removeEventListener("scroll", onMove);
      window.removeEventListener("hashchange", onMove);
      window.removeEventListener("resize", onMove);
    };
  }, [dep]);
}
