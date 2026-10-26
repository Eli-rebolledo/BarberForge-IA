"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

export type PreferenciaTema = "claro" | "oscuro" | "sistema";
const CLAVE = "bf_tema";

interface Ctx { preferencia: PreferenciaTema; oscuro: boolean; elegir: (t: PreferenciaTema) => void; alternar: () => void }
const Contexto = createContext<Ctx>({ preferencia: "sistema", oscuro: false, elegir: () => {}, alternar: () => {} });

/** Se ejecuta antes de pintar para evitar el parpadeo de claro a oscuro. */
export const SCRIPT_TEMA = `try{var p=localStorage.getItem("${CLAVE}")||"sistema";var o=p==="oscuro"||(p==="sistema"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.dataset.t=o?"dark":"light"}catch(e){}`;

export function TemaProvider({ children }: { children: ReactNode }) {
  const [preferencia, setPreferencia] = useState<PreferenciaTema>("sistema");
  const [oscuro, setOscuro] = useState(false);

  const aplicar = useCallback((p: PreferenciaTema) => {
    const o = p === "oscuro" || (p === "sistema" && matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.dataset.t = o ? "dark" : "light";
    setOscuro(o);
  }, []);

  useEffect(() => {
    let p: PreferenciaTema = "sistema";
    try { p = (localStorage.getItem(CLAVE) as PreferenciaTema) || "sistema"; } catch { /* sin almacenamiento */ }
    setPreferencia(p);
    aplicar(p);
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const cambio = () => aplicar((localStorage.getItem(CLAVE) as PreferenciaTema) || "sistema");
    mq.addEventListener("change", cambio);
    return () => mq.removeEventListener("change", cambio);
  }, [aplicar]);

  const elegir = useCallback((t: PreferenciaTema) => {
    try { localStorage.setItem(CLAVE, t); } catch { /* sin almacenamiento */ }
    setPreferencia(t);
    aplicar(t);
  }, [aplicar]);

  return (
    <Contexto.Provider value={{ preferencia, oscuro, elegir, alternar: () => elegir(oscuro ? "claro" : "oscuro") }}>
      {children}
    </Contexto.Provider>
  );
}

export const useTema = () => useContext(Contexto);
