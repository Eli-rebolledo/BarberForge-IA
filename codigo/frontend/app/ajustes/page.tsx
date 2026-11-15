"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useAviso } from "@/components/Aviso";
import { Logo, useBarberia } from "@/components/Barberia";
import { Icono } from "@/components/Icono";
import { Panel } from "@/components/Panel";
import { useTema, type PreferenciaTema } from "@/components/Tema";
import { api, type Ajustes as AjustesApi, type Usuario } from "@/lib/api";
import { logoAjustado } from "@/lib/imagen";

/** El administrador personaliza la barbería: logo, nombre, dirección, horario y descripción. */
function IdentidadBarberia() {
  const avisar = useAviso();
  const { marca, recargar } = useBarberia();
  const entrada = useRef<HTMLInputElement>(null);
  const [datos, setDatos] = useState({ nombre: "", direccion: "", horario: "", descripcion: "" });
  const [ocupado, setOcupado] = useState(false);
  const cargado = useRef(false);
  useEffect(() => {
    if (marca && !cargado.current) {
      cargado.current = true;
      setDatos({ nombre: marca.nombre, direccion: marca.direccion, horario: marca.horario, descripcion: marca.descripcion });
    }
  }, [marca]);
  const campo = (k: keyof typeof datos, v: string) => setDatos((d) => ({ ...d, [k]: v }));

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setOcupado(true);
    try { await api.actualizarMarca(datos); recargar(); avisar("Datos de la barbería actualizados. El asistente también los usa."); }
    catch (x) { avisar((x as Error).message, "err"); }
    setOcupado(false);
  }

  async function subir(archivo: File | undefined) {
    if (!archivo) return;
    setOcupado(true);
    try { await api.subirLogo(await logoAjustado(archivo)); recargar(); avisar("Logo actualizado en toda la página."); }
    catch (x) { avisar((x as Error).message, "err"); }
    setOcupado(false);
    if (entrada.current) entrada.current.value = "";
  }

  async function quitar() {
    setOcupado(true);
    try { await api.quitarLogo(); recargar(); avisar("Logo quitado: se muestra el de BarberForge.", "warn"); }
    catch (x) { avisar((x as Error).message, "err"); }
    setOcupado(false);
  }

  return (
    <section className="cd ancho identidad">
      <div className="aj-h"><span className="ic"><Icono n="tijera" size={18} /></span><h3>Tu barbería</h3></div>
      <p className="mute">El logo y los datos aparecen en la barra superior, el pie de página, el asistente, los correos y el ícono de la pestaña.</p>
      <div className="logo-ed">
        <div className="logo-prev"><Logo size={88} /></div>
        <div>
          <b>Logo</b>
          <small>PNG con fondo transparente se ve mejor. Se ajusta solo a 512 px.</small>
          <div className="row">
            <button type="button" className="btn line sm" disabled={ocupado} onClick={() => entrada.current?.click()}>
              <Icono n="camara" size={15} /> {marca?.logo_url ? "Cambiar logo" : "Subir logo"}
            </button>
            {marca?.logo_url && <button type="button" className="btn line sm peligro" disabled={ocupado} onClick={quitar}><Icono n="basura" size={15} /> Quitar</button>}
          </div>
        </div>
        <input ref={entrada} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(e) => subir(e.target.files?.[0])} />
      </div>
      <form className="form" onSubmit={guardar}>
        <div className="fgrid">
          <label className="fl">Nombre<input required maxLength={80} value={datos.nombre} onChange={(e) => campo("nombre", e.target.value)} /></label>
          <label className="fl">Dirección<input maxLength={160} value={datos.direccion} placeholder="Ej.: Cra 6 #4-20, Popayán" onChange={(e) => campo("direccion", e.target.value)} /></label>
          <label className="fl">Horario<input maxLength={160} value={datos.horario} placeholder="Ej.: Lunes a sábado de 9:00 a 19:00" onChange={(e) => campo("horario", e.target.value)} /></label>
          <label className="fl">Descripción<input maxLength={400} value={datos.descripcion} onChange={(e) => campo("descripcion", e.target.value)} /></label>
        </div>
        <div><button className="btn" disabled={ocupado}>Guardar datos</button></div>
      </form>
    </section>
  );
}

const TEMAS: [PreferenciaTema, string, string][] = [["claro", "Claro", "sol"], ["oscuro", "Oscuro", "luna"], ["sistema", "Automático", "ajustes"]];

function Contenido({ usuario }: { usuario: Usuario }) {
  const { preferencia, elegir } = useTema();
  const avisar = useAviso();
  const [aj, setAj] = useState<AjustesApi | null>(null);
  const [reindexando, setReindexando] = useState(false);
  const admin = usuario.role === "administrador";
  useEffect(() => { if (admin) api.ajustes().then(setAj).catch(() => {}); }, [admin]);

  async function reindexar() {
    setReindexando(true);
    try {
      const r = await api.reindexar();
      avisar(r.embeddings_ok ? "Asistente actualizado" : "Actualizado sin embeddings: la IA aún está descargando sus modelos", r.embeddings_ok ? "ok" : "warn");
    } catch (x) { avisar((x as Error).message, "err"); }
    setReindexando(false);
  }

  return (
    <div className="ajustes">
      <section className="cd">
        <div className="aj-h"><span className="ic"><Icono n="sol" size={18} /></span><h3>Apariencia</h3></div>
        <p className="mute">Elige cómo quieres ver la plataforma. Se recuerda en este dispositivo.</p>
        <div className="temas">
          {TEMAS.map(([t, n, i]) => (
            <button key={t} type="button" className={`tema ${preferencia === t ? "on" : ""}`} onClick={() => elegir(t)}>
              <Icono n={i} size={20} />{n}
            </button>
          ))}
        </div>
      </section>
      <section className="cd">
        <div className="aj-h"><span className="ic"><Icono n="candado" size={18} /></span><h3>Cuenta y seguridad</h3></div>
        <p className="mute">Actualiza tu nombre, correo o contraseña.</p>
        <div className="aj-pie"><Link className="btn line sm" href="/cuenta">Ir a Mi cuenta</Link></div>
      </section>
      {admin && <IdentidadBarberia />}
      {admin && aj && (
        <>
          <section className="cd">
            <div className="aj-h"><span className="ic"><Icono n="correo" size={18} /></span><h3>Recordatorios automáticos</h3></div>
            <p className="mute">Se envían solos, sin intervención del administrador ni de los barberos.</p>
            <ul className="lista-aj">
              <li><Icono n="correo" size={16} /><span>Correo de recordatorio <b>{aj.recordatorio_minutos} min</b> antes de la cita</span></li>
              <li><Icono n="check" size={16} /><span>El cliente tiene <b>{aj.confirmar_minutos} min</b> para confirmar con un clic</span></li>
              <li><Icono n="x" size={16} /><span>Si no confirma, la cita se cancela y la hora queda libre</span></li>
            </ul>
          </section>
          {aj.buzon_url && (
            <section className="cd">
              <div className="aj-h"><span className="ic"><Icono n="correo" size={18} /></span><h3>Buzón de pruebas</h3></div>
              <p className="mute">Revisa los correos que envía la plataforma (MailHog).</p>
              <div className="aj-pie"><a className="btn line sm" target="_blank" rel="noopener" href={aj.buzon_url}><Icono n="correo" size={15} /> Abrir buzón de correos</a></div>
            </section>
          )}
          <section className="cd ancho">
            <div className="aj-txt">
              <div className="aj-h"><span className="ic"><Icono n="chispa" size={18} /></span><h3>Asistente con IA</h3></div>
              <p className="mute">Si cambiaste servicios o precios, vuelve a indexar para que el asistente responda con la información nueva.</p>
            </div>
            <button className="btn line sm" disabled={reindexando} onClick={reindexar}><Icono n="chispa" size={15} /> Actualizar asistente</button>
          </section>
        </>
      )}
    </div>
  );
}

export default function Ajustes() {
  return <Panel roles={["cliente", "barbero", "administrador"]} titulo="Ajustes">{(u) => <Contenido usuario={u} />}</Panel>;
}
