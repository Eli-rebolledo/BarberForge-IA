"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { fotoCuadrada } from "@/lib/imagen";
import { useAviso } from "./Aviso";
import { Avatar } from "./Avatar";
import { Icono } from "./Icono";

interface Props {
  barberoId: number;
  nombre: string;
  foto?: string | null;
  onCambio?: (foto: string | null) => void;
  indice?: number;
}

/** Foto del barbero con botones para subirla, cambiarla o quitarla (administrador o el mismo barbero). */
export function FotoEditor({ barberoId, nombre, foto, onCambio, indice }: Props) {
  const avisar = useAviso();
  const entrada = useRef<HTMLInputElement>(null);
  const [actual, setActual] = useState(foto ?? null);
  const [subiendo, setSubiendo] = useState(false);

  async function elegir(archivo: File | undefined) {
    if (!archivo) return;
    setSubiendo(true);
    try {
      const r = await api.subirFoto(barberoId, await fotoCuadrada(archivo));
      setActual(r.photo_url);
      onCambio?.(r.photo_url);
      avisar("Foto actualizada. Los clientes ya la ven al elegir barbero.");
    } catch (e) { avisar((e as Error).message, "err"); }
    setSubiendo(false);
    if (entrada.current) entrada.current.value = "";
  }

  async function quitar() {
    setSubiendo(true);
    try {
      await api.quitarFoto(barberoId);
      setActual(null);
      onCambio?.(null);
      avisar("Foto eliminada", "warn");
    } catch (e) { avisar((e as Error).message, "err"); }
    setSubiendo(false);
  }

  return (
    <div className="fotoed">
      <Avatar nombre={nombre} foto={actual} indice={indice} className="av3" />
      <div>
        <b>Foto del barbero</b>
        <small>Los clientes reconocen más a su barbero por la cara que por el nombre.</small>
        <div className="row">
          <button type="button" className="btn line sm" disabled={subiendo} onClick={() => entrada.current?.click()}>
            <Icono n="camara" size={15} /> {subiendo ? "Subiendo…" : actual ? "Cambiar foto" : "Subir foto"}
          </button>
          {actual && <button type="button" className="btn line sm peligro" disabled={subiendo} onClick={quitar}><Icono n="basura" size={15} /> Quitar</button>}
        </div>
      </div>
      <input ref={entrada} type="file" accept="image/*" hidden onChange={(e) => elegir(e.target.files?.[0])} />
    </div>
  );
}
