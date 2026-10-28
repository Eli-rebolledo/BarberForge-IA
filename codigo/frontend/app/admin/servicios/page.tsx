"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useAviso, Modal, Vacio } from "@/components/Aviso";
import { Icono } from "@/components/Icono";
import { Panel } from "@/components/Panel";
import { api, type Servicio, type ServicioIn, type TipoServicio } from "@/lib/api";
import { cop, NOMBRE_TIPO, TIPOS } from "@/lib/formato";

const VACIO: ServicioIn = { name: "", description: "", price_cop: 0, duration_minutes: 0, service_type: "corte" };

function GestionServicios() {
  const avisar = useAviso();
  const [abierto, setAbierto] = useState(false);
  const [servicios, setServicios] = useState<Servicio[] | null>(null);
  const [error, setError] = useState("");
  const [datos, setDatos] = useState<ServicioIn>(VACIO);
  const [editando, setEditando] = useState<number | null>(null);

  const cargar = useCallback(() => {
    api.servicios().then(setServicios).catch((e: Error) => setError(e.message));
  }, []);
  useEffect(cargar, [cargar]);

  const campo = <K extends keyof ServicioIn>(k: K, v: ServicioIn[K]) => setDatos((d) => ({ ...d, [k]: v }));

  function editar(s: Servicio) {
    setEditando(s.id);
    setDatos({ name: s.name, description: s.description ?? "", price_cop: s.price_cop,
      duration_minutes: s.duration_minutes, service_type: s.service_type });
    setAbierto(true);
  }

  function cancelarEdicion() {
    setEditando(null);
    setDatos(VACIO);
    setAbierto(false);
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    try {
      if (editando) await api.editarServicio(editando, datos);
      else await api.crearServicio(datos);
      avisar(editando ? "Servicio actualizado" : "Servicio creado");
      cancelarEdicion();
      cargar();
    } catch (x) {
      avisar((x as Error).message, "err");
    }
  }

  async function alternar(id: number) {
    try {
      await api.alternarServicio(id);
      cargar();
    } catch (x) {
      avisar((x as Error).message, "err");
    }
  }

  if (error) return <Vacio>{error}</Vacio>;
  if (!servicios) return <Vacio>Cargando…</Vacio>;

  return (
    <>
      <div className="toolrow">
        <p className="mute">Lo que cambies aquí se actualiza también en el asistente.</p>
        <button className="btn" onClick={() => { setEditando(null); setDatos(VACIO); setAbierto(true); }}><Icono n="mas" size={16} /> Nuevo servicio</button>
      </div>
      <div className="cd tw">
        <table className="rt">
          <thead><tr><th>Servicio</th><th>Tipo</th><th>Precio</th><th>Duración</th><th>Estado</th><th></th></tr></thead>
          <tbody>
            {servicios.map((s) => (
              <tr key={s.id} className={s.is_active ? "" : "dim"}>
                <td data-l="Servicio"><b>{s.name}</b><i>{s.description}</i></td>
                <td data-l="Tipo">{NOMBRE_TIPO[s.service_type]}</td>
                <td data-l="Precio">{cop(s.price_cop)}</td>
                <td data-l="Duración">{s.duration_minutes} min</td>
                <td data-l="Estado"><span className={`pill ${s.is_active ? "green" : "gray"}`}><i className="dot" />{s.is_active ? "Activo" : "Inactivo"}</span></td>
                <td><div className="acts">
                  <button className="ab" onClick={() => editar(s)}>Editar</button>
                  <button className="ab" onClick={() => alternar(s.id)}>{s.is_active ? "Desactivar" : "Activar"}</button>
                </div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {abierto && (
        <Modal titulo={editando ? "Editar servicio" : "Nuevo servicio"} onCerrar={cancelarEdicion}>
          <form className="form" onSubmit={guardar}>
            <div className="fgrid">
              <label className="fl">Nombre<input required value={datos.name} onChange={(e) => campo("name", e.target.value)} /></label>
              <label className="fl">Tipo
                <select value={datos.service_type} onChange={(e) => campo("service_type", e.target.value as TipoServicio)}>
                  {TIPOS.map((t) => <option key={t} value={t}>{NOMBRE_TIPO[t]}</option>)}
                </select>
              </label>
              <label className="fl full">Descripción<input value={datos.description} onChange={(e) => campo("description", e.target.value)} /></label>
              <label className="fl">Precio (COP)<input type="number" min={1000} required value={datos.price_cop || ""} onChange={(e) => campo("price_cop", Number(e.target.value))} /></label>
              <label className="fl">Duración (min)<input type="number" min={10} required value={datos.duration_minutes || ""} onChange={(e) => campo("duration_minutes", Number(e.target.value))} /></label>
            </div>
            <div className="act"><button type="button" className="btn line" onClick={cancelarEdicion}>Cancelar</button><button className="btn">{editando ? "Guardar cambios" : "Crear servicio"}</button></div>
          </form>
        </Modal>
      )}
    </>
  );
}

export default function Servicios() {
  return <Panel roles={["administrador"]} titulo="Servicios">{() => <GestionServicios />}</Panel>;
}
