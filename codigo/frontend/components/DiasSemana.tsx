import { DIAS_SEMANA } from "@/lib/formato";

interface Props {
  dias: number[];
  onCambio?: (dias: number[]) => void; // sin esta función solo se muestran
  disabled?: boolean;
}

/** Días de la semana en círculos pequeños (L M X J V S D). Sin `onCambio` es solo lectura. */
export function DiasSemana({ dias, onCambio, disabled }: Props) {
  const alternar = (n: number) => onCambio?.(dias.includes(n) ? dias.filter((d) => d !== n) : [...dias, n].sort());
  return (
    <div className="dias" role="group" aria-label="Días de la semana">
      {DIAS_SEMANA.map((d) => (
        <button key={d.n} type="button" className={`dia ${dias.includes(d.n) ? "on" : ""}`} title={d.nombre}
          aria-pressed={dias.includes(d.n)} aria-label={d.nombre} disabled={disabled || !onCambio}
          onClick={() => alternar(d.n)}>{d.letra}</button>
      ))}
    </div>
  );
}
