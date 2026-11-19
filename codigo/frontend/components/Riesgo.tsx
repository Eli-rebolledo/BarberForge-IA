import { Icono } from "@/components/Icono";
import type { Cita } from "@/lib/api";

/** Feature 011: insignia para las citas que el modelo marca con riesgo alto de inasistencia. */
export function Riesgo({ cita }: { cita: Cita }) {
  if (!cita.riesgo_alto || cita.riesgo == null) return null;
  return (
    <span className="pill red riesgo" title="Probabilidad estimada de que el cliente no llegue. Recibe un aviso extra 60 minutos antes.">
      <Icono n="alerta" size={13} /> Riesgo {Math.round(cita.riesgo * 100)} %
    </span>
  );
}
