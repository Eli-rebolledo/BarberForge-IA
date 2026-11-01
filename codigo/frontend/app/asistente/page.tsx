"use client";

import { ChatAsistente } from "@/components/ChatAsistente";
import { Icono } from "@/components/Icono";
import { Panel } from "@/components/Panel";
import type { Usuario } from "@/lib/api";

const AYUDA: Record<string, [string, string][]> = {
  cliente: [
    ["calendario", "Agenda y cancela tus citas conversando: escribe «agendar» o «cancelar cita»."],
    ["tijera", "Pregunta por servicios, precios, duración o qué corte te queda mejor."],
    ["reloj", "Tu conversación queda guardada: puedes ir a otra página y volver cuando quieras."],
  ],
  barbero: [
    ["gota", "Procedimientos internos: limpieza y desinfección de máquinas, cuchillas, navajas y cierre del puesto."],
    ["calendario", "Tu agenda de hoy, tus próximas citas y cancelaciones (el calendario lo asigna el administrador)."],
    ["chispa", "Si no sabe algo, guarda tu pregunta para que el administrador se la enseñe; luego te responde aquí."],
  ],
};

function Pagina({ usuario }: { usuario: Usuario }) {
  return (
    <div className="asis">
      <ChatAsistente className="grande" />
      <aside className="cd asis-ayuda">
        <h3>¿Qué puedo preguntar?</h3>
        {(AYUDA[usuario.role] ?? AYUDA.cliente).map(([i, t]) => (
          <div key={t} className="ayuda-i"><span className="ic"><Icono n={i} size={18} /></span><p>{t}</p></div>
        ))}
      </aside>
    </div>
  );
}

export default function Asistente() {
  return (
    <Panel roles={["cliente", "barbero"]} titulo="Asistente personal">
      {(u) => <Pagina usuario={u} />}
    </Panel>
  );
}
