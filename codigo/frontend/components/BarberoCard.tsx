import type { Barbero, Servicio } from "@/lib/api";
import { primerNombre } from "@/lib/formato";
import { Avatar } from "./Avatar";
import { DiasSemana } from "./DiasSemana";

interface Props { barbero: Barbero; servicios: Servicio[]; indice: number; onAgendar: () => void }

export function BarberoCard({ barbero, servicios, indice, onAgendar }: Props) {
  return (
    <div className="bc">
      <Avatar nombre={barbero.full_name} foto={barbero.photo_url} indice={indice} className="av2" ampliable />
      <h3>{barbero.full_name}</h3>
      <div className="esp">{barbero.specialties || "Barbero profesional"}</div>
      <div className="tags">
        {servicios.filter((s) => barbero.service_ids.includes(s.id)).map((s) => <span key={s.id} className="tag">{s.name}</span>)}
      </div>
      <DiasSemana dias={barbero.work_days} />
      <button className="btn sm full" onClick={onAgendar}>Agendar con {primerNombre(barbero.full_name)}</button>
    </div>
  );
}
