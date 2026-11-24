"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Marca as MarcaBarberia } from "@/lib/api";
import { Marca } from "./Icono";

interface ContextoBarberia {
  marca: MarcaBarberia | null;
  recargar: () => void;
}

const Contexto = createContext<ContextoBarberia>({ marca: null, recargar: () => {} });

/** Carga una vez el nombre y el logo de la barbería; el ícono de la pestaña usa su logo si lo tiene. */
export function BarberiaProvider({ children }: { children: ReactNode }) {
  const [marca, setMarca] = useState<MarcaBarberia | null>(null);
  const recargar = useCallback(() => { api.marca().then(setMarca).catch(() => {}); }, []);
  useEffect(recargar, [recargar]);

  // Ícono de la pestaña: el logo de la barbería; si no tiene, la marca de BarberForge (app/icon.svg).
  useEffect(() => {
    if (!marca) return;
    let icono = document.querySelector<HTMLLinkElement>("link[rel='icon']");
    if (!icono) {
      icono = document.createElement("link");
      icono.rel = "icon";
      document.head.appendChild(icono);
    }
    if (marca.logo_url) {
      icono.removeAttribute("type");
      icono.removeAttribute("sizes");
      icono.href = marca.logo_url;
    } else {
      icono.type = "image/svg+xml";
      icono.href = "/icon.svg";
    }
  }, [marca]);

  return <Contexto.Provider value={{ marca, recargar }}>{children}</Contexto.Provider>;
}

export const useBarberia = () => useContext(Contexto);

/** Nombre de la barbería (mientras carga, «BarberForge»). */
export const useNombreBarberia = () => useContext(Contexto).marca?.nombre ?? "BarberForge";

/** Logo de la barbería si lo subió el administrador; si no, la marca de BarberForge. */
export function Logo({ size = 38 }: { size?: number }) {
  const { marca } = useBarberia();
  if (marca?.logo_url) {
    return (
      <span className="logo-img" style={{ width: size, height: size }}>
        <img src={marca.logo_url} alt={marca.nombre} />
      </span>
    );
  }
  return <Marca size={size} />;
}
