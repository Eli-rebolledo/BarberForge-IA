"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { Icono } from "./Icono";

type TipoAviso = "ok" | "err" | "warn";
type Avisar = (mensaje: string, tipo?: TipoAviso) => void;

interface AvisoItem { id: number; mensaje: string; tipo: TipoAviso }

const Contexto = createContext<Avisar>(() => {});
let siguienteId = 0;
const ICONO = { ok: "check", err: "x", warn: "alerta" } as const;
const TITULO = { ok: "Listo", err: "Algo salió mal", warn: "Atención" } as const;

/** Notificaciones flotantes (arriba a la derecha) que desaparecen solas. */
export function AvisoProvider({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<AvisoItem[]>([]);
  const cerrar = (id: number) => setAvisos((a) => a.filter((x) => x.id !== id));

  const avisar = useCallback<Avisar>((mensaje, tipo = "ok") => {
    const id = ++siguienteId;
    setAvisos((a) => [...a, { id, mensaje, tipo }]);
    setTimeout(() => setAvisos((a) => a.filter((x) => x.id !== id)), 5000);
  }, []);

  return (
    <Contexto.Provider value={avisar}>
      {children}
      <div className="toasts" aria-live="polite">
        {avisos.map((a) => (
          <div key={a.id} className={`toast ${a.tipo}`} role="status">
            <span className="ti"><Icono n={ICONO[a.tipo]} size={16} /></span>
            <div><b>{TITULO[a.tipo]}</b><span>{a.mensaje}</span></div>
            <button type="button" aria-label="Cerrar" onClick={() => cerrar(a.id)}><Icono n="x" size={14} /></button>
          </div>
        ))}
      </div>
    </Contexto.Provider>
  );
}

export const useAviso = () => useContext(Contexto);

/** Mensaje en línea para estados vacíos, de carga o de error. */
export function Vacio({ children, sinBorde }: { children: ReactNode; sinBorde?: boolean }) {
  return <div className="empty" style={sinBorde ? { border: 0 } : undefined}>{children}</div>;
}

/** Ventana modal centrada (se cierra con Esc o tocando fuera). */
export function Modal({ titulo, onCerrar, children }: { titulo: string; onCerrar: () => void; children: ReactNode }) {
  return (
    <div className="modal-bg" onMouseDown={(e) => e.target === e.currentTarget && onCerrar()}
      onKeyDown={(e) => e.key === "Escape" && onCerrar()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={titulo}>
        <div className="modal-h"><h3>{titulo}</h3>
          <button type="button" className="ico-btn" aria-label="Cerrar" onClick={onCerrar}><Icono n="x" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}
