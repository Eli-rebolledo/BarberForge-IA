"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useAviso, Modal, Vacio } from "@/components/Aviso";
import { Avatar } from "@/components/Avatar";
import { DiasSemana } from "@/components/DiasSemana";
import { FotoEditor } from "@/components/FotoEditor";
import { Icono } from "@/components/Icono";
import { Panel } from "@/components/Panel";
import { api, type Barbero, type BarberoIn, type Servicio } from "@/lib/api";
import { fotoCuadrada } from "@/lib/imagen";

const DIAS_BASE = [0, 1, 2, 3, 4, 5];
const VACIO = { full_name: "", email: "", password: "", specialties: "" };

function GestionBarberos() {
  const avisar = useAviso();
  const [barberos, setBarberos] = useState<Barbero[] | null>(null);
  const [servicios, setServicios] = useState<Servicio[]>([]);
  const [error, setError] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [datos, setDatos] = useState(VACIO);
  const [elegidos, setElegidos] = useState<number[]>([]);
  const [dias, setDias] = useState<number[]>(DIAS_BASE);
  const [foto, setFoto] = useState<File | null>(null);
  // edición y eliminación
  const [editando, setEditando] = useState<Barbero | null>(null);
  const [edit, setEdit] = useState({ full_name: "", email: "", password: "", specialties: "" });
  const [editServicios, setEditServicios] = useState<number[]>([]);
  const [cargandoEdit, setCargandoEdit] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [porEliminar, setPorEliminar] = useState<Barbero | null>(null);
  const [eliminando, setEliminando] = useState(false);

  const cargar = useCallback(() => {
    Promise.all([api.barberos(), api.servicios()])
      .then(([b, s]) => { setBarberos(b); setServicios(s); setElegidos(s.filter((x) => x.is_active).map((x) => x.id)); })
      .catch((e: Error) => setError(e.message));
  }, []);
  useEffect(cargar, [cargar]);

  const campo = (k: keyof typeof VACIO, v: string) => setDatos((d) => ({ ...d, [k]: v }));
  const alternarServicio = (id: number) => setElegidos((e) => (e.includes(id) ? e.filter((x) => x !== id) : [...e, id]));

  async function crear(e: FormEvent) {
    e.preventDefault();
    if (!dias.length) return avisar("Elige al menos un día de trabajo", "warn");
    try {
      const nuevo: BarberoIn = { ...datos, service_ids: elegidos, work_days: dias };
      const { id } = await api.crearBarbero(nuevo);
      let extra = "";
      if (foto) {
        try { await api.subirFoto(id, await fotoCuadrada(foto)); }
        catch (x) { extra = ` No se pudo guardar la foto (${(x as Error).message}); súbela desde «Editar».`; }
      }
      avisar(`Barbero creado: ${datos.full_name} ya puede iniciar sesión con ${datos.email}.${extra}`, extra ? "warn" : "ok");
      setDatos(VACIO); setDias(DIAS_BASE); setFoto(null); setAbierto(false);
      cargar();
    } catch (x) { avisar((x as Error).message, "err"); }
  }

  async function abrirEdicion(b: Barbero) {
    setEditando(b);
    setCargandoEdit(true);
    setEdit({ full_name: b.full_name, email: "", password: "", specialties: b.specialties });
    setEditServicios(b.service_ids);
    try {
      const d = await api.barbero(b.id); // el correo solo lo ve el administrador
      setEdit({ full_name: d.full_name, email: d.email, password: "", specialties: d.specialties });
      setEditServicios(d.service_ids);
    } catch (x) { avisar((x as Error).message, "err"); setEditando(null); }
    setCargandoEdit(false);
  }

  async function guardarEdicion(e: FormEvent) {
    e.preventDefault();
    if (!editando) return;
    setGuardando(true);
    try {
      await api.editarBarbero(editando.id, { ...edit, service_ids: editServicios });
      avisar(edit.password ? "Barbero actualizado. La contraseña nueva ya está activa." : "Barbero actualizado.");
      setEditando(null);
      cargar();
    } catch (x) { avisar((x as Error).message, "err"); }
    setGuardando(false);
  }

  async function eliminar() {
    if (!porEliminar) return;
    setEliminando(true);
    try {
      await api.eliminarBarbero(porEliminar.id);
      avisar(`${porEliminar.full_name} fue eliminado.`, "warn");
      setPorEliminar(null);
      cargar();
    } catch (x) { avisar((x as Error).message, "err"); }
    setEliminando(false);
  }

  async function cambiarDias(id: number, nuevos: number[]) {
    if (!nuevos.length) return avisar("Un barbero debe trabajar al menos un día", "warn");
    try { await api.actualizarDias(id, nuevos); avisar("Días habituales actualizados"); cargar(); }
    catch (x) { avisar((x as Error).message, "err"); }
  }

  async function alternar(b: Barbero) {
    try {
      const r = await api.alternarBarbero(b.id);
      let msg = b.is_active ? `${b.full_name} quedó inactivo y no recibirá citas.` : `${b.full_name} quedó activo y ya puede recibir citas.`;
      if (r.reasignadas) msg += ` ${r.reasignadas} ${r.reasignadas === 1 ? "cita pasó" : "citas pasaron"} a otro barbero y se avisó a los clientes por correo.`;
      if (r.canceladas) msg += ` ${r.canceladas} ${r.canceladas === 1 ? "cita se canceló" : "citas se cancelaron"} porque ningún otro barbero estaba libre; se avisó a los clientes.`;
      avisar(msg, b.is_active ? "warn" : "ok");
      cargar();
    } catch (x) { avisar((x as Error).message, "err"); }
  }

  if (error) return <Vacio>{error}</Vacio>;
  if (!barberos) return <Vacio>Cargando…</Vacio>;

  return (
    <>
      <div className="toolrow">
        <p className="mute">Aquí defines quién trabaja, su foto y sus días habituales. El calendario de cada barbero lo asignas tú en <Link href="/admin/disponibilidad">Calendario</Link> (los barberos no lo pueden cambiar).</p>
        <button className="btn" onClick={() => setAbierto(true)}><Icono n="mas" size={16} /> Nuevo barbero</button>
      </div>

      <div className="bgrid">
        {barberos.map((b, i) => (
          <article key={b.id} className={`bcard ${b.is_active ? "on" : "off"}`}>
            <div className="bhead">
              <Avatar nombre={b.full_name} foto={b.photo_url} indice={i} apagado={!b.is_active} className="av grande" />
              <div><b>{b.full_name}</b><small>{b.specialties || "Sin especialidades"}</small></div>
              <button type="button" role="switch" aria-checked={b.is_active} aria-label={b.is_active ? "Desactivar" : "Activar"}
                className={`switch ${b.is_active ? "on" : ""}`} onClick={() => alternar(b)}><i /></button>
            </div>
            <span className={`pill ${b.is_active ? "green" : "red"}`}><i className="dot" />{b.is_active ? "Activo" : "Inactivo"}</span>
            <div className="tags">{servicios.filter((s) => b.service_ids.includes(s.id)).map((s) => <span key={s.id} className="tag">{s.name}</span>)}</div>
            <div className="bdias"><small>Días habituales</small><DiasSemana dias={b.work_days} onCambio={(n) => cambiarDias(b.id, n)} /></div>
            <Link className="btn line sm full" href={`/admin/disponibilidad?barbero=${b.id}`}><Icono n="calendario" size={15} /> Ver calendario</Link>
            <div className="bacts">
              <button type="button" className="btn line sm" onClick={() => abrirEdicion(b)}><Icono n="editar" size={15} /> Editar</button>
              <button type="button" className="btn line sm peligro" onClick={() => setPorEliminar(b)}><Icono n="basura" size={15} /> Eliminar</button>
            </div>
          </article>
        ))}
        {!barberos.length && <Vacio>Aún no hay barberos. Crea el primero.</Vacio>}
      </div>

      {abierto && (
        <Modal titulo="Nuevo barbero" onCerrar={() => setAbierto(false)}>
          <form className="form" onSubmit={crear}>
            <div className="fgrid">
              <label className="fl">Nombre<input required value={datos.full_name} onChange={(e) => campo("full_name", e.target.value)} /></label>
              <label className="fl">Correo<input type="email" required value={datos.email} onChange={(e) => campo("email", e.target.value)} /></label>
              <label className="fl">Contraseña (mín. 8)<input type="password" minLength={8} required value={datos.password} onChange={(e) => campo("password", e.target.value)} /></label>
              <label className="fl">Especialidades<input placeholder="Ej.: fade, barba clásica" value={datos.specialties} onChange={(e) => campo("specialties", e.target.value)} /></label>
            </div>
            <label className="fl">Foto (opcional)
              <input type="file" accept="image/*" onChange={(e) => setFoto(e.target.files?.[0] ?? null)} />
            </label>
            <div className="fl"><span>Días habituales de trabajo</span><DiasSemana dias={dias} onCambio={setDias} /></div>
            <div className="fl"><span>Servicios que ofrece</span>
              <div className="chipsf">
                {servicios.filter((s) => s.is_active).map((s) => (
                  <button key={s.id} type="button" className={`fchip ${elegidos.includes(s.id) ? "on" : ""}`} onClick={() => alternarServicio(s.id)}>{s.name}</button>
                ))}
              </div>
            </div>
            <div className="act"><button type="button" className="btn line" onClick={() => setAbierto(false)}>Cancelar</button><button className="btn">Crear barbero</button></div>
          </form>
        </Modal>
      )}

      {editando && (
        <Modal titulo={`Editar a ${editando.full_name}`} onCerrar={() => setEditando(null)}>
          {cargandoEdit ? <Vacio>Cargando…</Vacio> : (
            <form className="form" onSubmit={guardarEdicion}>
              <FotoEditor barberoId={editando.id} nombre={editando.full_name} foto={editando.photo_url}
                onCambio={(url) => setBarberos((l) => l && l.map((x) => (x.id === editando.id ? { ...x, photo_url: url } : x)))} />
              <div className="credenciales"><Icono n="correo" size={16} /> Con este correo inicia sesión el barbero. Si no recuerda su contraseña, escribe una nueva abajo.</div>
              <div className="fgrid">
                <label className="fl">Nombre<input required value={edit.full_name} onChange={(e) => setEdit((d) => ({ ...d, full_name: e.target.value }))} /></label>
                <label className="fl">Correo<input type="email" required value={edit.email} onChange={(e) => setEdit((d) => ({ ...d, email: e.target.value }))} /></label>
                <label className="fl">Contraseña nueva (opcional)<input type="password" minLength={8} autoComplete="new-password" placeholder="Déjala vacía para no cambiarla" value={edit.password} onChange={(e) => setEdit((d) => ({ ...d, password: e.target.value }))} /></label>
                <label className="fl">Especialidades<input placeholder="Ej.: fade, barba clásica" value={edit.specialties} onChange={(e) => setEdit((d) => ({ ...d, specialties: e.target.value }))} /></label>
              </div>
              <div className="fl"><span>Servicios que ofrece</span>
                <div className="chipsf">
                  {servicios.filter((s) => s.is_active || editServicios.includes(s.id)).map((s) => (
                    <button key={s.id} type="button" className={`fchip ${editServicios.includes(s.id) ? "on" : ""}`}
                      onClick={() => setEditServicios((e) => (e.includes(s.id) ? e.filter((x) => x !== s.id) : [...e, s.id]))}>{s.name}</button>
                  ))}
                </div>
              </div>
              <div className="act"><button type="button" className="btn line" onClick={() => setEditando(null)}>Cancelar</button><button className="btn" disabled={guardando}>Guardar cambios</button></div>
            </form>
          )}
        </Modal>
      )}

      {porEliminar && (
        <Modal titulo="Eliminar barbero" onCerrar={() => setPorEliminar(null)}>
          <div className="confirma">
            <p>¿Seguro que quieres eliminar a <b>{porEliminar.full_name}</b>? Se borrarán su cuenta y su calendario. Esta acción no se puede deshacer.</p>
            <small>Si el barbero ya tiene citas en el historial no se puede eliminar; en ese caso puedes desactivarlo con el interruptor de su tarjeta.</small>
            <div className="act"><button type="button" className="btn line" onClick={() => setPorEliminar(null)}>Cancelar</button>
              <button type="button" className="btn danger" disabled={eliminando} onClick={eliminar}>Sí, eliminar</button></div>
          </div>
        </Modal>
      )}
    </>
  );
}

export default function Barberos() {
  return <Panel roles={["administrador"]} titulo="Barberos">{() => <GestionBarberos />}</Panel>;
}
