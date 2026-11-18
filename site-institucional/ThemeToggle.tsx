import { Moon, Sun } from "lucide-react";
import { setTheme, useTheme } from "./theme";

/** Botão para alternar entre modo claro e escuro. */
export default function ThemeToggle({ className = "" }: { className?: string }) {
  const theme = useTheme();
  const toLight = theme === "dark";
  const label = toLight ? "Ativar modo claro" : "Ativar modo escuro";
  return (
    <button
      type="button"
      className={`theme-toggle ${className}`.trim()}
      onClick={() => setTheme(toLight ? "light" : "dark")}
      aria-label={label}
      title={label}
    >
      {toLight ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
    </button>
  );
}
