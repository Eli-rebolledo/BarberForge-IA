"use client";

import { useCallback, useEffect, useState } from "react";
import { useAviso, Vacio } from "@/components/Aviso";
import { Icono } from "@/components/Icono";
import { Panel } from "@/components/Panel";
import { api, type EstadoPqrs, type Pqrs } from "@/lib/api";

const TIPO: Record<Pqrs["tipo"], [string, string]> = {
  peticion: ["Petición", "blue"], queja: ["Queja", "red"], reclamo: ["Reclamo", "amber"], sugerencia: ["Sugerencia", "green"],
};
const ESTADO: Record<EstadoPqrs, [string, string]> = {
  abierta: ["Abierta", "amber"], en_tramite: ["En trámite", "blue"], cerrada: ["Cerrada", "green"],
};

/** Feature 012: peticiones, quejas, reclamos y sugerencias que llegan por el asistente de voz o el chat.
 *  El administrador cambia su estado y responde; la respuesta le llega por correo a quien la radicó. */
function ListaPqrs() {
  const avisar = useAviso();
  const [lista, setLista] = useState<Pqrs[] | null>(null);
  const [error, setError] = useState("");
  const [abierta, setAbierta] = useState<Pqrs | null>(null);
  const [estado, setEstado] = useState<EstadoPqrs>("en_tramite");
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const cargar = useCallback(() => { api.pqrs().then(setLista).catch((e: Error) => setError(e.message)); }, []);
  useEffect(cargar, [cargar]);

  function gestionar(p: Pqrs) {
    setAbierta(p);
    setEstado(p.estado === "abierta" ? "en_tramite" : p.estado);
    setTexto(p.respuesta ?? "");
  }

  async function guardar() {
    if (!abierta) return;
    setOcupado(true);
    try {
      await api.gestionarPqrs(abierta.id, estado, texto.trim());
      const nueva = texto.trim() && texto.trim() !== (abierta.respuesta ?? "");
      avisar(nueva && abierta.correo ? `Respuesta enviada a ${abierta.correo}.` : `${abierta.radicado}: ${ESTADO[estado][0].toLowerCase()}.`);
      setAbierta(null);
      cargar();
    } catch (x) { avisar((x as Error).message, "err"); }
    setOcupado(false);
  }

  if (error) return <Vacio>{error}</Vacio>;
  if (!lista) return <Vacio>Cargando…</Vacio>;
  if (!lista.length) return <Vacio>Todavía no hay PQRS. Llegan cuando alguien presenta una en el asistente, por voz o escribiendo en el chat (por ejemplo: «Quiero poner una queja: esperé 40 minutos y nadie me avisó»).</Vacio>;
  const pendientes = lista.filter((p) => p.estado !== "cerrada").length;
  return (
    <>
      <p className="mute">{pendientes ? `${pendientes} sin cerrar. ` : "Todas cerradas. "}Llegan desde el asistente, por voz o escribiendo en el chat (por ejemplo: «Quiero poner una queja: …»). Cada una tiene su radicado y también llega por correo. Plazo para responder: 15 días hábiles.</p>
      {abierta && (
        <section className="cd" style={{ marginTop: 12 }}>
          <h3>{abierta.radicado} · {TIPO[abierta.tipo][0]} de {abierta.quien}</h3>
          <p className="mute" style={{ marginBottom: 12 }}>{abierta.descripcion}</p>
          <div className="fgrid">
            <label className="fl">Estado
              <select value={estado} onChange={(e) => setEstado(e.target.value as EstadoPqrs)}>
                {(Object.keys(ESTADO) as EstadoPqrs[]).map((k) => <option key={k} value={k}>{ESTADO[k][0]}</option>)}
              </select>
            </label>
            <label className="fl full">Respuesta {abierta.correo ? `(llega por correo a ${abierta.correo})` : "(la radicó un visitante: queda guardada, sin correo)"}
              <textarea rows={4} maxLength={2000} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Escribe la respuesta para el cliente…" />
            </label>
          </div>
          <div className="act">
            <button className="btn line" disabled={ocupado} onClick={() => setAbierta(null)}>Cancelar</button>
            <button className="btn" disabled={ocupado} onClick={guardar}><Icono n="enviar" size={15} /> Guardar</button>
          </div>
        </section>
      )}
      <div className="cd tw">
        <table className="rt">
          <thead><tr><th>Radicado</th><th>Tipo</th><th>De</th><th>Resumen</th><th>Estado</th><th>Fecha</th><th /></tr></thead>
          <tbody>
            {lista.map((p) => (
              <tr key={p.id}>
                <td data-l="Radicado"><b style={{ whiteSpace: "nowrap" }}>{p.radicado}</b></td>
                <td data-l="Tipo"><span className={`pill ${TIPO[p.tipo][1]}`}>{TIPO[p.tipo][0]}</span></td>
                <td data-l="De">{p.quien}</td>
                <td data-l="Resumen"><b>{p.resumen ?? "—"}</b><i>{p.respuesta ? `Respuesta: ${p.respuesta}` : p.descripcion}</i></td>
                <td data-l="Estado"><span className={`pill ${(ESTADO[p.estado] ?? ESTADO.abierta)[1]}`}>{(ESTADO[p.estado] ?? ESTADO.abierta)[0]}</span></td>
                <td data-l="Fecha" style={{ whiteSpace: "nowrap" }}>{p.created_at ? new Date(p.created_at).toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" }) : "—"}</td>
                <td><button className="btn line sm" onClick={() => gestionar(p)}><Icono n="editar" size={14} /> {p.estado === "cerrada" ? "Ver" : "Responder"}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function PaginaPqrs() {
  return <Panel roles={["administrador"]} titulo="PQRS">{() => <ListaPqrs />}</Panel>;
}
