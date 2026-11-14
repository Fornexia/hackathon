import { useEffect, useRef, useState } from "react";
import type { CSSProperties, MouseEvent } from "react";
import "./FornexLaptop.css";

type Props = {
  className?: string;
  /** ms entre as trocas de tela (0 desliga) */
  interval?: number;
  /** inclina o laptop conforme o mouse */
  parallax?: boolean;
  /** imagem da tela do site; sem ela, mostra a interface demo embutida */
  screenSrc?: string;
  screenAlt?: string;
  /** parte vertical da imagem visível: "top" (padrão), "center", "bottom" ou porcentagem, ex. "45%" */
  screenPosition?: string;
  /** ícone flutuante com brilho ciano */
  badge?: boolean;
};

const Icon = ({ id }: { id: string }) => (
  <svg className="fx-ic" aria-hidden="true">
    <use href={`#fx-${id}`} />
  </svg>
);

const NAV = [
  ["home", "Início"],
  ["search", "Consultas"],
  ["building", "Fornecedores"],
  ["chart", "Relatórios"],
  ["users", "Equipe"],
] as const;

const TILES = [
  ["doc", "Contratos"],
  ["db", "Pagamentos"],
  ["gavel", "Sanções"],
  ["spark", "Resumo IA"],
] as const;

const ROWS = [
  ["doc", "Contratos", "12 registros encontrados"],
  ["db", "Pagamentos", "8 registros encontrados"],
  ["gavel", "Sanções", "Nenhum registro"],
  ["spark", "Resumo com IA", "Análise concluída"],
] as const;

export default function FornexLaptop({
  className = "",
  interval = 4500,
  parallax = true,
  screenSrc,
  screenAlt = "Tela do FornexIA",
  screenPosition = "top",
  badge = true,
}: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [view, setView] = useState(0);
  const [scale, setScale] = useState(1);
  const [tilt, setTilt] = useState({ rx: 0, ry: 0 });

  // troca automática de tela
  useEffect(() => {
    if (!interval || screenSrc) return;
    const id = setInterval(() => setView((v) => (v + 1) % 2), interval);
    return () => clearInterval(id);
  }, [interval, screenSrc]);

  // escala conforme a largura do container
  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setScale(Math.min(1, entry.contentRect.width / 940)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const style = {
    "--s": scale,
    "--rx": `${tilt.rx}deg`,
    "--ry": `${tilt.ry}deg`,
    height: 680 * scale,
  } as CSSProperties;

  const onMove = (e: MouseEvent<HTMLDivElement>) => {
    if (!parallax) return;
    const r = e.currentTarget.getBoundingClientRect();
    setTilt({
      ry: ((e.clientX - r.left) / r.width - 0.5) * 10,
      rx: ((e.clientY - r.top) / r.height - 0.5) * -6,
    });
  };

  return (
    <div
      ref={rootRef}
      className={`fx ${className}`}
      style={style}
      onMouseMove={onMove}
      onMouseLeave={() => setTilt({ rx: 0, ry: 0 })}
      onClick={() => !screenSrc && setView((v) => (v + 1) % 2)}
    >
      <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
        <symbol id="fx-home" viewBox="0 0 24 24"><path d="M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z" /></symbol>
        <symbol id="fx-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></symbol>
        <symbol id="fx-building" viewBox="0 0 24 24"><path d="M5 21V5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v16M15 10h4a1 1 0 0 1 1 1v10M3 21h18M9 8h2M9 12h2M9 16h2" /></symbol>
        <symbol id="fx-chart" viewBox="0 0 24 24"><path d="M4 20V4M4 20h16M8 16v-5M12 16V8M16 16v-3" /></symbol>
        <symbol id="fx-users" viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6" /><circle cx="17" cy="9" r="2.5" /><path d="M17.5 14c2.6.2 4.5 2 4.5 5" /></symbol>
        <symbol id="fx-doc" viewBox="0 0 24 24"><path d="M7 3h7l4 4v14H7zM14 3v4h4M9.5 12h6M9.5 16h6" /></symbol>
        <symbol id="fx-db" viewBox="0 0 24 24"><ellipse cx="12" cy="6" rx="7" ry="3" /><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3" /></symbol>
        <symbol id="fx-gavel" viewBox="0 0 24 24"><path d="M13 3.5l5.5 5.5-3 3L10 6.5zM11.5 8L4 15.5l3 3L14.5 11M3 21h10" /></symbol>
        <symbol id="fx-spark" viewBox="0 0 24 24"><path d="M12 2l2.2 6.3L21 10l-6.8 1.7L12 18l-2.2-6.3L3 10l6.8-1.7zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z" /></symbol>
        <symbol id="fx-check" viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" /></symbol>
        <symbol id="fx-layers" viewBox="0 0 24 24"><path d="M12 3l9 5-9 5-9-5zM3 12.5l9 5 9-5M3 17l9 5 9-5" /></symbol>
      </svg>

      <div className="fx-stage">
        <div className="fx-scene">
          <div className="fx-shadow" />
          <div className="fx-laptop" style={{ transform: `translateZ(-150px) rotateX(${-12 + tilt.rx}deg) rotateY(${-28 + tilt.ry}deg)` }}>
            <div className="fx-top" style={{ transformOrigin: "top", transform: "rotateX(90deg)" }}>
              <div className="fx-hinge" />
              <div className="fx-deck" />
              <div className="fx-pad" />
            </div>
            <div className="fx-front" style={{ transform: "translateZ(430px)" }} />
            <div className="fx-sl" style={{ transformOrigin: "left top", transform: "rotateY(-90deg)" }} />
            <div className="fx-sr" style={{ transformOrigin: "left top", transform: "rotateY(-90deg)" }} />

            <div className="fx-lid">
              <div className="fx-back" />
              {Array.from({ length: 10 }, (_, i) => (
                <div key={i} className="fx-slab" style={{ transform: `translateZ(-${i + 1}px)` }} />
              ))}
              <div className="fx-screen">
                {screenSrc ? (
                  <img className="fx-shot" src={screenSrc} alt={screenAlt} draggable={false} style={{ objectPosition: `50% ${{ top: "0%", center: "50%", bottom: "100%" }[screenPosition] ?? screenPosition}` }} />
                ) : (
                <div className="fx-ui">
                  <aside className="fx-side">
                    <div className="fx-logo">
                      <Icon id="layers" />
                      <span>Fornex<b>IA</b></span>
                    </div>
                    <ul className="fx-nav">
                      {NAV.map(([icon, label], i) => (
                        <li key={label} className={(view === 0 ? i === 0 : i === 1) ? "fx-on" : ""}>
                          <Icon id={icon} />
                          {label}
                        </li>
                      ))}
                    </ul>
                  </aside>

                  <section className="fx-main">
                    <div className={`fx-view ${view === 0 ? "fx-on" : ""}`}>
                      <h2>Consultar fornecedor</h2>
                      <div className="fx-search">
                        <span>Informe o CNPJ ou nome do fornecedor</span>
                        <i><Icon id="search" /></i>
                      </div>
                      <div className="fx-tiles">
                        {TILES.map(([icon, label]) => (
                          <div key={label} className="fx-tile">
                            <Icon id={icon} />
                            {label}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className={`fx-view ${view === 1 ? "fx-on" : ""}`}>
                      <h2>Resultado da consulta</h2>
                      <div className="fx-rows">
                        {ROWS.map(([icon, title, info]) => (
                          <div key={title} className={`fx-row ${icon === "spark" ? "fx-ia" : ""}`}>
                            <Icon id={icon} />
                            <div className="fx-t"><strong>{title}</strong></div>
                            <small>{info}</small>
                            <span className="fx-ok"><Icon id="check" /></span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </section>
                </div>
                )}
              </div>
            </div>

            {badge && (
              <>
                <div className="fx-badge-glow" />
                <div className="fx-badge"><Icon id="layers" /></div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
