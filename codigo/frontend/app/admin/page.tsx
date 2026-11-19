"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Vacio } from "@/components/Aviso";
import { Icono } from "@/components/Icono";
import { Panel } from "@/components/Panel";
import { Riesgo } from "@/components/Riesgo";
import { api, type EstadoCita, type Estadisticas, type ModeloInasistencia } from "@/lib/api";
import { cop, ESTADOS, fechaCorta, hora12, TONO_ESTADO } from "@/lib/formato";

const COLOR: Record<string, string> = { green: "#3f8a5c", amber: "#d99a2b", blue: "#2e5489", red: "#b3262e", gray: "#98a2b3" };

const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const FRANJAS = ["Antes de las 10 a. m.", "10 a. m. a 12 m.", "12 m. a 5 p. m.", "Desde las 5 p. m."];
const VARIABLES: Record<string, string> = {
  faltas_previas: "Faltas anteriores del cliente", citas_previas: "Citas anteriores del cliente",
  anticipacion_horas: "Anticipación al agendar", es_invitado: "Cliente sin cuenta", tasa_faltas: "Tasa de faltas",
  precio_miles: "Precio de la cita", num_servicios: "Número de servicios", hora: "Hora de la cita",
};
function nombreVariable(v: string) {
  const [k, n] = v.split("=");
  if (k === "dia_semana") return DIAS[Number(n)];
  if (k === "franja") return FRANJAS[Number(n)];
  return VARIABLES[k] ?? k;
}
const pct = (x?: number | null) => (x == null ? "—" : `${Math.round(x * 100)} %`);

/** Feature 011: qué modelo se usa, qué tan bien le va y cuántas citas próximas tienen riesgo alto. */
function PrediccionInasistencias() {
  const [m, setM] = useState<ModeloInasistencia | null>(null);
  useEffect(() => { api.modeloInasistencia().then(setM).catch(() => setM(null)); }, []);
  if (!m) return null;
  return (
    <section className="cd">
      <div className="sh">
        <h3>Predicción de inasistencias</h3>
        {m.activo
          ? <span className={`pill ${m.origen === "real" ? "green" : "amber"}`}><i className="dot" />{m.origen === "real" ? "Entrenado con citas reales" : "Entrenado con datos sintéticos"}</span>
          : <span className="pill gray"><i className="dot" />Sin modelo: solo recordatorio de 40 min</span>}
      </div>
      <div className="mini"><span>Citas próximas con riesgo alto</span><b>{m.citas_riesgo_alto} de {m.citas_proximas}</b></div>
      <small className="mute">Desde {pct(m.umbral)} de riesgo, el cliente recibe un aviso extra 60 minutos antes además del recordatorio de 40 minutos.</small>
      {m.activo && m.metricas && (
        <>
          <div className="mini"><span>Modelo</span><b>{m.algoritmo === "regresion_logistica" ? "Regresión logística" : "Árbol de decisión"}</b></div>
          <div className="mini"><span>AUC (qué tan bien separa a quien falta de quien llega)</span><b>{m.metricas.auc?.toFixed(2) ?? "—"}</b></div>
          <div className="mini"><span>Inasistencias que detecta (recall)</span><b>{pct(m.metricas.recall)}</b></div>
          {m.importancia && (
            <div className="factores">
              <small className="mute">Lo que más pesa en la predicción:</small>
              {Object.entries(m.importancia).map(([v, peso]) => (
                <div key={v} className="mini"><span>{nombreVariable(v)}</span><b className={peso > 0 ? "down" : "up"}>{peso > 0 ? "sube el riesgo" : "baja el riesgo"}</b></div>
              ))}
            </div>
          )}
          {m.origen !== "real" && <small className="mute">Mientras no haya suficientes citas reales cerradas, el modelo se basa en datos sintéticos: sirve para probar el sistema, no garantiza la precisión en tu barbería.</small>}
        </>
      )}
    </section>
  );
}

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
            <span><span className={`pill ${TONO_ESTADO[c.status]}`}><i className="dot" />{ESTADOS[c.status]}</span><Riesgo cita={c} /></span>
          </div>
        )) : <small className="mute">No hay citas próximas.</small>}
      </section>

      <PrediccionInasistencias />
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
