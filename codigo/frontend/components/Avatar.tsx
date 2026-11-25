"use client";

import { useEffect, useState, type KeyboardEvent, type MouseEvent } from "react";
import { createPortal } from "react-dom";
import { COLORES_AVATAR, iniciales } from "@/lib/formato";

interface Props {
  nombre: string;
  foto?: string | null;
  indice?: number;
  className?: string;
  apagado?: boolean;
  /** Si tiene foto, al tocarla se abre en grande (para ver al barbero antes de agendar). */
  ampliable?: boolean;
}

/** Foto del barbero o, si no tiene, sus iniciales sobre un color. */
export function Avatar({ nombre, foto, indice = 0, className = "av", apagado, ampliable }: Props) {
  const [abierta, setAbierta] = useState(false);
  if (foto) {
    const img = <img className={`${className} foto`} src={foto} alt={`Foto de ${nombre}`} loading="lazy" />;
    if (!ampliable) return img;
    // Puede estar dentro de un botón (la lista de barberos al agendar): por eso es un span con rol de botón y el
    // clic no llega al botón de afuera.
    const abrir = (e: MouseEvent | KeyboardEvent) => { e.stopPropagation(); e.preventDefault(); setAbierta(true); };
    return (
      <>
        <span role="button" tabIndex={0} className="foto-amp" title="Ver la foto en grande" aria-label={`Ver la foto de ${nombre}`}
          onClick={abrir} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") abrir(e); }}>
          {img}
          <span className="lupa" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
              <circle cx="11" cy="11" r="6.5" /><path d="m20 20-4.2-4.2M11 8.5v5M8.5 11h5" />
            </svg>
          </span>
        </span>
        {abierta && <FotoGrande nombre={nombre} foto={foto} onCerrar={() => setAbierta(false)} />}
      </>
    );
  }
  return (
    <span className={className} style={apagado ? undefined : { background: COLORES_AVATAR[indice % COLORES_AVATAR.length], color: "#fff" }}>
      {iniciales(nombre)}
    </span>
  );
}

/** La foto en grande sobre la página. Se cierra con Esc, con la X o tocando afuera. */
function FotoGrande({ nombre, foto, onCerrar }: { nombre: string; foto: string; onCerrar: () => void }) {
  useEffect(() => {
    const tecla = (e: globalThis.KeyboardEvent) => { if (e.key === "Escape") onCerrar(); };
    document.addEventListener("keydown", tecla);
    const antes = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", tecla); document.body.style.overflow = antes; };
  }, [onCerrar]);
  const cerrar = (e: MouseEvent) => { e.stopPropagation(); onCerrar(); };
  // En un portal sobre <body>, para que no quede dentro del botón de la lista de barberos.
  return createPortal(
    <div className="foto-modal" role="dialog" aria-modal="true" aria-label={`Foto de ${nombre}`} onClick={cerrar}>
      <figure onClick={(e) => e.stopPropagation()}>
        <img src={foto} alt={`Foto de ${nombre}`} />
        <figcaption>{nombre}</figcaption>
        <button type="button" className="cerrar" aria-label="Cerrar" onClick={cerrar} autoFocus>×</button>
      </figure>
    </div>,
    document.body,
  );
}
