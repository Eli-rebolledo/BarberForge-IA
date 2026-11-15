"use client";

import { Panel } from "@/components/Panel";
import { Reserva } from "@/components/Reserva";

export default function NuevaCita() {
  return (
    <Panel roles={["barbero", "administrador"]} titulo="Nueva cita">
      {(u) => <Reserva usuario={u} />}
    </Panel>
  );
}
