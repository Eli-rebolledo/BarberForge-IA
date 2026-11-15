import { Icono } from "./Icono";
import type { Servicio } from "@/lib/api";
import { cop, ICONO_TIPO, minutosTexto } from "@/lib/formato";

export function ServicioCard({ servicio, onAgendar }: { servicio: Servicio; onAgendar: () => void }) {
  return (
    <div className={`sc t-${servicio.service_type}`}>
      <div className="ic"><Icono n={ICONO_TIPO[servicio.service_type]} size={22} /></div>
      <h3>{servicio.name}</h3>
      <p>{servicio.description}</p>
      <div className="pr"><b>{cop(servicio.price_cop)}</b><small><Icono n="reloj" size={13} /> {minutosTexto(servicio.duration_minutes)}</small></div>
      <button className="btn sm full" onClick={onAgendar}>Agendar este servicio</button>
    </div>
  );
}
