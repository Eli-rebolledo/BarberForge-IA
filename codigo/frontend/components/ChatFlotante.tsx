"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { ChatAsistente } from "./ChatAsistente";
import { Icono } from "./Icono";
import { useSesion } from "./Sesion";

export const EVENTO_ABRIR_CHAT = "bf:abrir-chat";

/** Abre el asistente flotante desde cualquier botón de la página. */
export const abrirChat = () => window.dispatchEvent(new Event(EVENTO_ABRIR_CHAT));

// Páginas donde el asistente ya está incrustado: ahí no hace falta el botón flotante.
const CON_CHAT = ["/", "/asistente", "/admin/asistente"];

/** Botón flotante con el asistente (visitantes, clientes y barberos). En las páginas que ya lo incrustan, el
 *  botón solo lo enfoca. La conversación de los usuarios registrados se guarda en el servidor. */
export function ChatFlotante() {
  const ruta = usePathname();
  const { usuario } = useSesion();
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    const abrir = () => {
      if (CON_CHAT.includes(ruta)) document.getElementById("asistente")?.scrollIntoView({ behavior: "smooth", block: "center" });
      else setAbierto(true);
    };
    window.addEventListener(EVENTO_ABRIR_CHAT, abrir);
    return () => window.removeEventListener(EVENTO_ABRIR_CHAT, abrir);
  }, [ruta]);

  if (CON_CHAT.includes(ruta) || usuario?.role === "administrador") return null;
  return (
    <>
      {/* Siempre montado (oculto con CSS) para no perder la conversación al cerrarlo. */}
      <ChatAsistente className={`floating ${abierto ? "on" : ""}`} onCerrar={() => setAbierto(false)} />
      <button className="fab" onClick={() => setAbierto((a) => !a)} title="Asistente" aria-label="Abrir asistente">
        <Icono n={abierto ? "x" : "chat"} size={24} />
      </button>
    </>
  );
}
