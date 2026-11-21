"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAviso, Vacio } from "@/components/Aviso";
import { Calendario } from "@/components/Calendario";
import { Icono } from "@/components/Icono";
import { Panel } from "@/components/Panel";
import { api, type Barbero, type DiaCalendario } from "@/lib/api";
import { fechaCorta, hoyISO, hora12 } from "@/lib/formato";

const HORAS = Array.from({ length: 29 }, (_, i) => {
  const m = 6 * 60 + i * 30;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
});
const mesDe = (iso: string) => iso.slice(0, 7);

/** Solo el administrador asigna el calendario de atención de cada barbero. */
function Gestion() {
  const avisar = useAviso();
  const params = useSearchParams();
  const [barberos, setBarberos] = useState<Barbero[] | null>(null);
  const [error, setError] = useState("");
  const [barberoId, setBarberoId] = useState(Number(params.get("barbero")) || 0);
  const [mes, setMes] = useState(mesDe(hoyISO()));
  const [dias, setDias] = useState<DiaCalendario[]>([]);
  const [sel, setSel] = useState<string[]>([]);
  const [inicio, setInicio] = useState("09:00");
  const [fin, setFin] = useState("17:00");
  const minutos = 30; // intervalo base de los horarios; la hora real se ajusta sola a la duración de cada servicio
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    api.barberos().then((b) => {
      const activos = b.filter((x) => x.is_active);
      setBarberos(activos);
      setBarberoId((id) => id || activos[0]?.id || 0);
    }).catch((e: Error) => setError(e.message));
  }, []);

  const cargar = useCallback(() => {
    if (barberoId) api.calendario(barberoId, mes).then(setDias).catch((e: Error) => setError(e.message));
  }, [barberoId, mes]);
  useEffect(cargar, [cargar]);

  const barbero = barberos?.find((b) => b.id === barberoId);
  const marcas = useMemo(() => Object.fromEntries(dias.filter((d) => d.total > 0).map((d) => [d.date, d.total])), [dias]);
  const bloqueos = useMemo(() => Object.fromEntries(dias.filter((d) => d.bloqueo).map((d) => [d.date, d.bloqueo as string])), [dias]);
  const alternar = (iso: string) => setSel((s) => (s.includes(iso) ? s.filter((x) => x !== iso) : [...s, iso].sort()));

  function diasHabituales() {
    if (!barbero) return;
    const [y, m] = mes.split("-").map(Number);
    const hoy = hoyISO();
    const lista: string[] = [];
    for (let d = 1; d <= new Date(y, m, 0).getDate(); d++) {
      const iso = `${mes}-${String(d).padStart(2, "0")}`;
      if (iso >= hoy && barbero.work_days.includes((new Date(y, m - 1, d).getDay() + 6) % 7)) lista.push(iso);
    }
    setSel(lista);
  }

  async function aplicar(accion: "abrir" | "cerrar") {
    if (!barberoId || !sel.length) return;
    if (accion === "abrir" && fin <= inicio) return avisar("La hora final debe ser posterior a la inicial", "warn");
    setOcupado(true);
    try {
      if (accion === "abrir") {
        await api.generarDisponibilidad({ barber_id: barberoId, date_from: sel[0], date_to: sel[sel.length - 1], dates: sel, start: inicio, end: fin, minutes: minutos });
        avisar(`Horario habilitado en ${sel.length} ${sel.length === 1 ? "día" : "días"}: ${hora12(inicio)} a ${hora12(fin)}.`);
      } else {
        await api.cerrarDias(barberoId, sel);
        avisar(`Se cerraron ${sel.length} ${sel.length === 1 ? "día" : "días"}. Las citas ya agendadas se conservan.`, "warn");
      }
      setSel([]);
      cargar();
    } catch (x) { avisar((x as Error).message, "err"); }
    setOcupado(false);
  }

  if (error) return <Vacio>{error}</Vacio>;
  if (!barberos) return <Vacio>Cargando…</Vacio>;
  if (!barberos.length) return <Vacio>Primero crea un barbero activo.</Vacio>;

  return (
    <div className="calpage">
      <section className="cd">
        <label className="fl">Barbero
          <select value={barberoId} onChange={(e) => { setBarberoId(Number(e.target.value)); setSel([]); }}>
            {barberos.map((b) => <option key={b.id} value={b.id}>{b.full_name}</option>)}
          </select>
        </label>
        <Calendario seleccion={sel} marcas={marcas} bloqueos={bloqueos} onToggle={alternar} onMes={(m) => { setMes(m); }} />
        <div className="leyenda"><span><i className="d mk" /> Con horario</span><span><i className="d sel" /> Seleccionado</span><span><i className="d bq" /> Sin atención</span></div>
        <div className="acts"><button className="ab" onClick={diasHabituales}>Seleccionar sus días habituales del mes</button><button className="ab" onClick={() => setSel([])}>Limpiar</button></div>
      </section>

      <section className="cd">
        <h3>Horario de atención</h3>
        <p className="mute">Marca las fechas en las que trabaja (por ejemplo, solo el 11, 12 y 18 de noviembre) y define la jornada.</p>
        {sel.length ? <div className="chipsf">{sel.map((d) => <button key={d} className="fchip on" onClick={() => alternar(d)}>{fechaCorta(d)} <Icono n="x" size={12} /></button>)}</div>
          : <p className="mute">Aún no has seleccionado fechas.</p>}
        <div className="fgrid">
          <label className="fl">Desde<select value={inicio} onChange={(e) => setInicio(e.target.value)}>{HORAS.map((h) => <option key={h} value={h}>{hora12(h)}</option>)}</select></label>
          <label className="fl">Hasta<select value={fin} onChange={(e) => setFin(e.target.value)}>{HORAS.map((h) => <option key={h} value={h}>{hora12(h)}</option>)}</select></label>
        </div>
        <div className="nota-franja"><Icono n="info" size={16} /><span>Solo defines la jornada. Cada cita ocupa lo que dura su servicio: si una barba de 20 min termina antes de la media hora, ese tiempo sobrante queda libre para otro cliente. Y si cierras una cita antes de tiempo desde «Citas», el resto de su horario también se libera.</span></div>
        <div className="act">
          <button className="btn line" disabled={ocupado || !sel.length} onClick={() => aplicar("cerrar")}>Cerrar días</button>
          <button className="btn" disabled={ocupado || !sel.length} onClick={() => aplicar("abrir")}>Habilitar horario</button>
        </div>
        <div className="info-auto"><Icono n="info" size={16} /> En «Barberos» defines los días habituales de la semana; aquí decides las fechas reales de cada mes. Los festivos y las ausencias se marcan en la pestaña «Festivos» y nunca reciben horario.</div>
      </section>
    </div>
  );
}

export default function Disponibilidad() {
  return (
    <Panel roles={["administrador"]} titulo="Calendario de atención">
      {() => <Suspense fallback={<Vacio>Cargando…</Vacio>}><Gestion /></Suspense>}
    </Panel>
  );
}
