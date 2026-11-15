"use client";

import { useState } from "react";
import { Icono } from "./Icono";
import { hoyISO, isoFecha, MESES } from "@/lib/formato";

interface Props {
  seleccion: string[];
  onToggle: (iso: string) => void;
  /** Días con marca (punto) y, opcionalmente, un número. */
  marcas?: Record<string, number>;
  /** Si se define, solo estos días se pueden elegir. */
  habilitados?: Set<string>;
  permitirPasado?: boolean;
  onMes?: (mes: string) => void; // AAAA-MM
  mesInicial?: string;
}

const CABECERA = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];

/** Calendario mensual. Sirve para elegir un día (cliente) o varios (administrador). */
export function Calendario({ seleccion, onToggle, marcas = {}, habilitados, permitirPasado, onMes, mesInicial }: Props) {
  const hoy = hoyISO();
  const base = (mesInicial ?? hoy).slice(0, 7).split("-").map(Number);
  const [vista, setVista] = useState({ y: base[0], m: base[1] - 1 });
  const primero = new Date(vista.y, vista.m, 1);
  const hueco = (primero.getDay() + 6) % 7; // lunes primero
  const dias = new Date(vista.y, vista.m + 1, 0).getDate();

  function mover(delta: number) {
    const d = new Date(vista.y, vista.m + delta, 1);
    setVista({ y: d.getFullYear(), m: d.getMonth() });
    onMes?.(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }

  return (
    <div className="cal">
      <div className="cal-h">
        <button type="button" className="ico-btn" onClick={() => mover(-1)} aria-label="Mes anterior"><Icono n="izq" /></button>
        <b>{MESES[vista.m]} {vista.y}</b>
        <button type="button" className="ico-btn" onClick={() => mover(1)} aria-label="Mes siguiente"><Icono n="der" /></button>
      </div>
      <div className="cal-g">
        {CABECERA.map((c) => <span key={c} className="cal-d">{c}</span>)}
        {Array.from({ length: hueco }, (_, i) => <span key={"v" + i} />)}
        {Array.from({ length: dias }, (_, i) => {
          const iso = isoFecha(vista.y, vista.m, i + 1);
          const bloqueado = (!permitirPasado && iso < hoy) || (habilitados ? !habilitados.has(iso) : false);
          const sel = seleccion.includes(iso);
          return (
            <button key={iso} type="button" disabled={bloqueado} onClick={() => onToggle(iso)}
              className={`cal-c ${sel ? "sel" : ""} ${iso === hoy ? "hoy" : ""} ${marcas[iso] ? "mk" : ""}`}
              aria-pressed={sel} aria-label={iso}>
              {i + 1}
            </button>
          );
        })}
      </div>
    </div>
  );
}
