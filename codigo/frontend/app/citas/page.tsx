"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAviso, Vacio } from "@/components/Aviso";
import { Icono } from "@/components/Icono";
import { Panel } from "@/components/Panel";
import { Riesgo } from "@/components/Riesgo";
import { useSesion } from "@/components/Sesion";
import { api, type Cita, type EstadoCita, type Usuario } from "@/lib/api";
import { cop, ESTADOS, fechaCorta, hoyISO, hora12, TONO_ESTADO } from "@/lib/formato";

type Accion = "cancelar" | "completada" | "inasistencia";
type Grupo = "todas" | "activas" | "completada" | "canceladas";
const GRUPOS: [Grupo, string][] = [["todas", "Todas"], ["activas", "Activas"], ["completada", "Completadas"], ["canceladas", "Canceladas"]];
const esActiva = (c: Cita) => c.status === "pendiente" || c.status === "confirmada";
const cumple = (c: Cita, g: Grupo) =>
  g === "todas" || (g === "activas" && esActiva(c)) || (g === "completada" && c.status === "completada") ||
  (g === "canceladas" && (c.status.startsWith("cancelada") || c.status === "inasistencia"));

function Acciones({ cita, rol, onAccion }: { cita: Cita; rol: Usuario["role"]; onAccion: (a: Accion) => void }) {
  return (
    <div className="acts">
      {esActiva(cita) && <button className="ab red" onClick={() => onAccion("cancelar")}>Cancelar</button>}
      {cita.status === "confirmada" && rol !== "cliente" && (
        <>
          <button className="ab ok" onClick={() => onAccion("completada")}>Completada</button>
          <button className="ab" onClick={() => onAccion("inasistencia")}>No asistió</button>
        </>
      )}
    </div>
  );
}

function ListaCitas({ usuario }: { usuario: Usuario }) {
  const avisar = useAviso();
  const [citas, setCitas] = useState<Cita[] | null>(null);
  const [error, setError] = useState("");
  const [fecha, setFecha] = useState("");
  const [barbero, setBarbero] = useState("");
  const [buscar, setBuscar] = useState("");
  const [grupo, setGrupo] = useState<Grupo>("activas");
  const esAdmin = usuario.role === "administrador";
  const esCliente = usuario.role === "cliente";

  const cargar = useCallback(() => { api.citas().then(setCitas).catch((e: Error) => setError(e.message)); }, []);
  useEffect(cargar, [cargar]);

  async function ejecutar(cita: Cita, accion: Accion) {
    try {
      if (accion === "cancelar") await api.cancelarCita(cita.id);
      else await api.cerrarCita(cita.id, accion);
      avisar(accion === "cancelar" ? "Cita cancelada" : accion === "completada" ? "Cita marcada como completada" : "Cita marcada como no asistida");
      cargar();
    } catch (e) { avisar((e as Error).message, "err"); }
  }

  const hoy = hoyISO();
  const filtradas = useMemo(() => {
    const q = buscar.trim().toLowerCase();
    const lista = (citas ?? []).filter((c) => cumple(c, grupo) && (!fecha || c.date === fecha) && (!barbero || c.barber === barbero) &&
      (!q || c.client.toLowerCase().includes(q) || c.service.toLowerCase().includes(q)));
    // próximas primero (de la más cercana a la más lejana); luego el historial, de lo más reciente a lo más antiguo
    const clave = (c: Cita) => c.date + c.time;
    const prox = lista.filter((c) => c.date >= hoy).sort((a, b) => clave(a).localeCompare(clave(b)));
    const hist = lista.filter((c) => c.date < hoy).sort((a, b) => clave(b).localeCompare(clave(a)));
    return [...prox, ...hist];
  }, [citas, grupo, fecha, barbero, buscar, hoy]);

  function exportar() {
    const filas = [["Fecha", "Hora", "Servicios", "Barbero", "Cliente", "Estado", "Total"],
      ...filtradas.map((c) => [c.date, hora12(c.time), c.service, c.barber, c.client, ESTADOS[c.status], String(c.price)])];
    const csv = "\ufeff" + filas.map((f) => f.map((x) => `"${x.replace(/"/g, '""')}"`).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = `citas-${hoy}.csv`;
    a.click();
  }

  if (error) return <Vacio>{error}</Vacio>;
  if (!citas) return <Vacio>Cargando…</Vacio>;
  const barberos = [...new Set(citas.map((c) => c.barber))];

  return (
    <>
      <div className="cd toolbar">
        <div className="chipsf">
          {GRUPOS.map(([g, n]) => (
            <button key={g} className={`fchip ${grupo === g ? "on" : ""}`} onClick={() => setGrupo(g)}>
              {n} <span>{citas.filter((c) => cumple(c, g)).length}</span>
            </button>
          ))}
        </div>
        {!esCliente && (
          <div className="filtros">
            {esAdmin && <button className="btn line sm" onClick={exportar}><Icono n="bajar" size={15} /> CSV</button>}
            <input type="search" placeholder="Buscar cliente o servicio" value={buscar} onChange={(e) => setBuscar(e.target.value)} />
            <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} aria-label="Fecha" />
            {esAdmin && (
              <select value={barbero} onChange={(e) => setBarbero(e.target.value)} aria-label="Barbero">
                <option value="">Todos los barberos</option>
                {barberos.map((b) => <option key={b}>{b}</option>)}
              </select>
            )}
          </div>
        )}
      </div>

      <div className="info-auto"><Icono n="correo" size={16} /> {esCliente
        ? "Los recordatorios por correo se envían solos antes de cada cita: no tienes que hacer nada."
        : "Los recordatorios se envían solos 40 minutos antes. Las citas con riesgo alto de inasistencia reciben además un aviso 60 minutos antes."}</div>

      <div className="cd tw">
        {filtradas.length ? (
          <table className="rt">
            <thead><tr><th>Fecha y hora</th><th>Servicios</th><th>{esCliente ? "Barbero" : "Cliente"}</th>{!esCliente && <th>Barbero</th>}<th>Total</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              {filtradas.map((c) => (
                <tr key={c.id}>
                  <td data-l="Fecha"><b>{fechaCorta(c.date)}</b><i>{hora12(c.time)}</i></td>
                  <td data-l="Servicios">{c.services.join(" + ")}</td>
                  <td data-l={esCliente ? "Barbero" : "Cliente"}>{esCliente ? c.barber : <>{c.client}{c.walk_in && <i>En el local{c.client_phone ? ` · ${c.client_phone}` : ""}</i>}</>}</td>
                  {!esCliente && <td data-l="Barbero">{c.barber}</td>}
                  <td data-l="Total">{cop(c.price)}</td>
                  <td data-l="Estado">
                    <span className={`pill ${TONO_ESTADO[c.status]}`}><i className="dot" />{ESTADOS[c.status] ?? c.status}</span>
                    {!esCliente && esActiva(c) && <Riesgo cita={c} />}
                  </td>
                  <td><Acciones cita={c} rol={usuario.role} onAccion={(a) => ejecutar(c, a)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <Vacio sinBorde>{citas.length ? "No hay citas con esos filtros." : "Aún no hay citas."}</Vacio>}
      </div>
    </>
  );
}

export default function Citas() {
  return (
    <Panel roles={["cliente", "barbero", "administrador"]} titulo="Citas"
      accion={<AccionesCabecera />}>
      {(usuario) => <ListaCitas usuario={usuario} />}
    </Panel>
  );
}

function AccionesCabecera() {
  const { usuario } = useSesion();
  if (!usuario) return null;
  return usuario.role === "cliente"
    ? <Link className="btn" href="/agendar"><Icono n="mas" size={16} /> Agendar cita</Link>
    : <Link className="btn" href="/citas/nueva"><Icono n="mas" size={16} /> Nueva cita</Link>;
}
