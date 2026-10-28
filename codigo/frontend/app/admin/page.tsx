"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Vacio } from "@/components/Aviso";
import { Icono } from "@/components/Icono";
import { Panel } from "@/components/Panel";
import { api, type EstadoCita, type Estadisticas } from "@/lib/api";
import { cop, ESTADOS, fechaCorta, hora12, TONO_ESTADO } from "@/lib/formato";

const COLOR: Record<string, string> = { green: "#3f8a5c", amber: "#d99a2b", blue: "#2e5489", red: "#b3262e", gray: "#98a2b3" };

function Dashboard() {
  const [s, setS] = useState<Estadisticas | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api.estadisticas().then(setS).catch((e: Error) => setError(e.message)); }, []);
  if (error) return <Vacio>{error}</Vacio>;
  if (!s) return <Vacio>Cargando…</Vacio>;

  const delta = s.ingresos_mes_anterior ? Math.round(((s.ingresos_mes - s.ingresos_mes_anterior) / s.ingresos_mes_anterior) * 100) : null;
  const maxMes = Math.max(1, ...s.ingresos_6_meses.map((m) => m.total));
  const totalEstados = Object.values(s.estados).reduce((a, b) => a + b, 0);
  let acum = 0;
  const gradiente = totalEstados ? Object.entries(s.estados).map(([k, n]) => {
    const ini = acum; acum += (n / totalEstados) * 100;
    return `${COLOR[TONO_ESTADO[k as EstadoCita]]} ${ini}% ${acum}%`;
  }).join(",") : "var(--sf) 0 100%";
  const maxTop = Math.max(1, ...s.top_servicios.map((t) => t.cantidad));

  return (
    <>
      <div className="kp">
        <div className="cd kc"><span className="kl"><Icono n="dinero" size={16} /> Recaudado este mes</span><b className="k">{cop(s.ingresos_mes)}</b>
          <small className={delta === null ? "mute" : delta >= 0 ? "up" : "down"}>{delta === null ? "Sin mes anterior para comparar" : `${delta >= 0 ? "+" : ""}${delta}% vs. mes anterior`}</small></div>
        <div className="cd kc ka"><span className="kl"><Icono n="reloj" size={16} /> Por cobrar</span><b className="k">{cop(s.por_cobrar)}</b><small className="mute">Citas activas próximas</small></div>
        <div className="cd kc kg"><span className="kl"><Icono n="calendario" size={16} /> Citas hoy</span><b className="k">{s.citas_hoy}</b><small className="mute">{s.citas_mes} en lo que va del mes</small></div>
        <div className="cd kc kr"><span className="kl"><Icono n="alerta" size={16} /> Por confirmar</span><b className="k">{s.pendientes}</b><small className="mute">Cancelaciones del mes: {s.tasa_cancelacion}%</small></div>
      </div>

      <div className="g2">
        <section className="cd">
          <div className="sh"><h3>Recaudo de los últimos 6 meses</h3><small className="mute">Solo citas completadas</small></div>
          <div className="bars">
            {s.ingresos_6_meses.map((m, i) => (
              <div key={m.mes} title={`${cop(m.total)} · ${m.citas} citas`}>
                <em>{m.total ? cop(m.total) : ""}</em>
                <span className={i === 5 ? "now" : ""} style={{ height: `${Math.max(3, (m.total / maxMes) * 100)}%` }} />
                {m.etiqueta}
              </div>
            ))}
          </div>
        </section>
        <section className="cd">
          <div className="sh"><h3>Estado de las citas</h3><small className="mute">Este mes</small></div>
          <div className="donutw">
            <div className="donut" style={{ background: `conic-gradient(${gradiente})` }}><div><b>{totalEstados}</b><small>citas</small></div></div>
            <div>
              {Object.entries(s.estados).map(([k, n]) => (
                <div key={k} className="lgd"><i style={{ background: COLOR[TONO_ESTADO[k as EstadoCita]] }} />{ESTADOS[k as EstadoCita]} · {n}</div>
              ))}
              {!totalEstados && <small className="mute">Aún no hay citas este mes.</small>}
            </div>
          </div>
        </section>
      </div>

      <div className="g3">
        <section className="cd">
          <div className="sh"><h3>Servicios más pedidos</h3></div>
          {s.top_servicios.length ? s.top_servicios.map((t) => (
            <div key={t.nombre} className="hb"><span>{t.nombre}</span><div><i style={{ width: `${(t.cantidad / maxTop) * 100}%` }} /></div><b>{t.cantidad}</b></div>
          )) : <small className="mute">Sin datos todavía.</small>}
          <div className="mini"><span>Ticket promedio</span><b>{cop(s.ticket_promedio)}</b></div>
          <div className="mini"><span>Recaudado hoy</span><b>{cop(s.ingresos_hoy)}</b></div>
        </section>
        <section className="cd">
          <div className="sh"><h3>Rendimiento por barbero</h3></div>
          <div className="tw">
            <table className="rt">
              <thead><tr><th>Barbero</th><th>Citas</th><th>Completadas</th><th>Recaudado</th></tr></thead>
              <tbody>
                {s.barberos.map((b) => <tr key={b.nombre}><td data-l="Barbero"><b>{b.nombre}</b></td><td data-l="Citas">{b.citas}</td><td data-l="Completadas">{b.completadas}</td><td data-l="Recaudado">{cop(b.ingresos)}</td></tr>)}
                {!s.barberos.length && <tr><td colSpan={4}><small className="mute">Sin citas este mes.</small></td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <section className="cd">
        <div className="sh"><h3>Próximas citas</h3><Link className="btn line sm" href="/citas">Ver todas</Link></div>
        {s.proximas.length ? s.proximas.map((c) => (
          <div key={c.id} className="prox">
            <span className="pf"><b>{fechaCorta(c.date)}</b>{hora12(c.time)}</span>
            <span className="pc"><b>{c.client}</b><small>{c.services.join(" + ")} · {c.barber}</small></span>
            <span className={`pill ${TONO_ESTADO[c.status]}`}><i className="dot" />{ESTADOS[c.status]}</span>
          </div>
        )) : <small className="mute">No hay citas próximas.</small>}
      </section>
    </>
  );
}

export default function Admin() {
  return (
    <Panel roles={["administrador"]} titulo="Panel de la barbería"
      accion={<Link className="btn" href="/citas/nueva"><Icono n="mas" size={16} /> Nueva cita</Link>}>
      {() => <Dashboard />}
    </Panel>
  );
}
