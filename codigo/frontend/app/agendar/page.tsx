"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Vacio } from "@/components/Aviso";
import { Panel } from "@/components/Panel";
import { Reserva } from "@/components/Reserva";

function Flujo({ usuario }: { usuario: Parameters<typeof Reserva>[0]["usuario"] }) {
  const p = useSearchParams();
  return <Reserva usuario={usuario} preServicio={Number(p.get("servicio")) || undefined} preBarbero={Number(p.get("barbero")) || undefined} />;
}

export default function Agendar() {
  return (
    <Panel roles={["cliente"]} titulo="Agendar cita">
      {(u) => <Suspense fallback={<Vacio>Cargando…</Vacio>}><Flujo usuario={u} /></Suspense>}
    </Panel>
  );
}
