"use client";

import { useCallback, useEffect, useState } from "react";
import { useAviso, Vacio } from "@/components/Aviso";
import { Icono } from "@/components/Icono";
import { Panel } from "@/components/Panel";
import { api, type Ausencia, type Barbero, type CitaAfectada, type Festivo } from "@/lib/api";
import { fechaCorta, hora12, hoyISO } from "@/lib/formato";

const plural = (n: number, uno: string, varios: string) => `${n} ${n === 1 ? uno : varios}`;
/** Lista legible de las citas afectadas, para mostrarla antes de confirmar. */
const listaCitas = (citas: CitaAfectada[]) =>
  citas.slice(0, 12).map((c) => `• ${fechaCorta(c.date)} ${hora12(c.time)} · ${c.client} con ${c.barber} (${c.service})`).join("\n")
  + (citas.length > 12 ? `\n… y ${citas.length - 12} más` : "");

/** RF09 (días sin atención) y RF17 (ausencias de barberos). Ninguno recibe horario ni se ofrece en la web, el chat o la voz. */
function Gestion() {
  const avisar = useAviso();
  const [festivos, setFestivos] = useState<Festivo[] | null>(null);
  const [ausencias, setAusencias] = useState<Ausencia[]>([]);
  const [barberos, setBarberos] = useState<Barbero[]>([]);
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [dia, setDia] = useState("");
  const [diaFin, setDiaFin] = useState("");
  const [motivo, setMotivo] = useState("");
  const [aus, setAus] = useState({ barbero: 0, desde: "", hasta: "", motivo: "" });

  const cargar = useCallback(() => {
    Promise.all([api.festivos(), api.ausencias(), api.barberos()]).then(([f, a, b]) => {
      setFestivos(f);
      setAusencias(a);
      const activos = b.filter((x) => x.is_active);
      setBarberos(activos);
      setAus((s) => ({ ...s, barbero: s.barbero || activos[0]?.id || 0 }));
    }).catch((e: Error) => setError(e.message));
  }, []);
  useEffect(cargar, [cargar]);

  async function correr(tarea: () => Promise<string>) {
    setOcupado(true);
    try { avisar(await tarea()); cargar(); } catch (x) { avisar((x as Error).message, "err"); }
    setOcupado(false);
  }

  const agregarFestivo = () => correr(async () => {
    if (!dia) throw new Error("Elige la fecha del festivo");
    if (diaFin && diaFin < dia) throw new Error("La fecha final debe ser igual o posterior a la inicial");
    const afectadas = await api.afectadasPorFestivo(dia, diaFin);
    const aviso = afectadas.length
      ? `Hay ${plural(afectadas.length, "cita activa", "citas activas")} en esas fechas. Se cancelarán y se avisará a cada cliente por correo:\n\n${listaCitas(afectadas)}\n\n¿Confirmas el cierre?`
      : "No hay citas activas en esas fechas. ¿Confirmas el cierre?";
    if (!window.confirm(aviso)) return "Cierre cancelado: no se cambió nada.";
    const r = await api.crearFestivo(dia, motivo || "Festivo", diaFin);
    setDia(""); setDiaFin(""); setMotivo("");
    return `${r.dias > 1 ? `${r.dias} días cerrados` : "Festivo guardado"}${r.canceladas ? ` · ${plural(r.canceladas, "cita cancelada", "citas canceladas")} con aviso al cliente` : ""}.`;
  });

  const cargarColombia = () => correr(async () => {
    const anio = Number(hoyISO().slice(0, 4));
    if (!window.confirm(`Se agregarán los festivos nacionales de Colombia que faltan desde hoy hasta el 31 de diciembre de ${anio}. Si alguna cita cae en uno de ellos, se cancelará con aviso al cliente. ¿Continuar?`)) return "Sin cambios";
    const r = await api.cargarFestivosColombia(anio);
    return r.creados ? `${plural(r.creados, "festivo agregado", "festivos agregados")}${r.canceladas ? ` · ${plural(r.canceladas, "cita cancelada", "citas canceladas")}` : ""}.` : "Los festivos de este año ya estaban cargados.";
  });

  const agregarAusencia = () => correr(async () => {
    if (!aus.barbero || !aus.desde) throw new Error("Elige el barbero y las fechas");
    const hasta = aus.hasta || aus.desde;
    if (hasta < aus.desde) throw new Error("La fecha final debe ser igual o posterior a la inicial");
    const afectadas = await api.afectadasPorAusencia(aus.barbero, aus.desde, hasta);
    if (afectadas.length && !window.confirm(`Este barbero tiene ${plural(afectadas.length, "cita activa", "citas activas")} en esas fechas. Cada una pasará al barbero libre con menos citas ese día que haga el mismo servicio; si no hay nadie, se cancelará. Se avisará a cada cliente por correo:\n\n${listaCitas(afectadas)}\n\n¿Confirmas la ausencia?`)) return "Ausencia no registrada.";
    const r = await api.crearAusencia(aus.barbero, aus.desde, hasta, aus.motivo || "Ausencia");
    setAus((s) => ({ ...s, desde: "", hasta: "", motivo: "" }));
    const partes = [r.reasignadas && `${plural(r.reasignadas, "cita pasó", "citas pasaron")} a otro barbero`,
      r.canceladas && `${plural(r.canceladas, "cita cancelada", "citas canceladas")} (nadie más estaba libre)`].filter(Boolean);
    return `Ausencia guardada${partes.length ? ` · ${partes.join(" · ")}. Se avisó a los clientes por correo` : ""}.`;
  });

  if (error) return <Vacio>{error}</Vacio>;
  if (!festivos) return <Vacio>Cargando…</Vacio>;
  const hoy = hoyISO();

  return (
    <div className="bloqueos">
      <section className="cd">
        <h3>Festivos y días sin atención</h3>
        <p className="mute">La barbería completa cierra ese día (o varios seguidos). No se generan horarios y nadie puede agendar.</p>
        <div className="fgrid">
          <label className="fl">Fecha<input type="date" min={hoy} value={dia} onChange={(e) => setDia(e.target.value)} /></label>
          <label className="fl">Hasta (opcional)<input type="date" min={dia || hoy} value={diaFin} onChange={(e) => setDiaFin(e.target.value)} /></label>
          <label className="fl full">Motivo<input value={motivo} maxLength={80} placeholder="Festivo, inventario, vacaciones colectivas…" onChange={(e) => setMotivo(e.target.value)} /></label>
        </div>
        <div className="act">
          <button className="btn line" disabled={ocupado} onClick={cargarColombia}><Icono n="calendario" size={15} /> Cargar festivos de Colombia</button>
          <button className="btn" disabled={ocupado} onClick={agregarFestivo}><Icono n="mas" size={15} /> Agregar</button>
        </div>
        {festivos.length ? (
          <ul>
            {festivos.map((f) => (
              <li key={f.id}>
                <span><b>{fechaCorta(f.date)}</b><small>{f.motivo}</small></span>
                <button className="btn line sm peligro" disabled={ocupado} aria-label={`Quitar ${f.motivo}`}
                  onClick={() => correr(async () => { await api.borrarFestivo(f.id); return "Festivo quitado: se volvió a abrir la agenda de ese día."; })}>
                  <Icono n="basura" size={14} />
                </button>
              </li>
            ))}
          </ul>
        ) : <p className="mute" style={{ marginTop: 12 }}>No hay festivos próximos.</p>}
      </section>

      <section className="cd">
        <h3>Ausencias de barberos</h3>
        <p className="mute">Vacaciones, incapacidad o permiso. Sus citas de esos días pasan a otro barbero libre que haga el mismo servicio; si no hay nadie, se cancelan. En ambos casos se avisa al cliente.</p>
        {barberos.length ? (
          <>
            <div className="fgrid">
              <label className="fl full">Barbero
                <select value={aus.barbero} onChange={(e) => setAus({ ...aus, barbero: Number(e.target.value) })}>
                  {barberos.map((b) => <option key={b.id} value={b.id}>{b.full_name}</option>)}
                </select>
              </label>
              <label className="fl">Desde<input type="date" min={hoy} value={aus.desde} onChange={(e) => setAus({ ...aus, desde: e.target.value })} /></label>
              <label className="fl">Hasta<input type="date" min={aus.desde || hoy} value={aus.hasta} onChange={(e) => setAus({ ...aus, hasta: e.target.value })} /></label>
              <label className="fl full">Motivo<input value={aus.motivo} maxLength={80} placeholder="Vacaciones, cita médica…" onChange={(e) => setAus({ ...aus, motivo: e.target.value })} /></label>
            </div>
            <div className="act"><button className="btn" disabled={ocupado} onClick={agregarAusencia}><Icono n="mas" size={15} /> Registrar ausencia</button></div>
          </>
        ) : <p className="mute">Primero crea un barbero activo.</p>}
        {ausencias.length ? (
          <ul>
            {ausencias.map((a) => (
              <li key={a.id}>
                <span><b>{a.barber}</b><small>{a.date_from === a.date_to ? fechaCorta(a.date_from) : `${fechaCorta(a.date_from)} – ${fechaCorta(a.date_to)}`} · {a.motivo}</small></span>
                <button className="btn line sm peligro" disabled={ocupado} aria-label={`Quitar ausencia de ${a.barber}`}
                  onClick={() => correr(async () => { await api.borrarAusencia(a.id); return "Ausencia quitada: el barbero vuelve a recibir citas esos días."; })}>
                  <Icono n="basura" size={14} />
                </button>
              </li>
            ))}
          </ul>
        ) : <p className="mute" style={{ marginTop: 12 }}>No hay ausencias registradas.</p>}
      </section>
    </div>
  );
}

export default function PaginaFestivos() {
  return <Panel roles={["administrador"]} titulo="Festivos y ausencias">{() => <Gestion />}</Panel>;
}
