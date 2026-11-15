"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAviso, Vacio } from "./Aviso";
import { Calendario } from "./Calendario";
import { Icono } from "./Icono";
import { api, ApiError, type Barbero, type ClienteBasico, type Franja, type Servicio, type Usuario } from "@/lib/api";
import { cop, fechaLarga, hora12, ICONO_TIPO, minutosTexto, textoAlternativas } from "@/lib/formato";
import { Avatar } from "./Avatar";

interface Props {
  usuario: Usuario;
  preServicio?: number;
  preBarbero?: number;
}

/** Agendar paso a paso: servicios (uno o varios) → barbero → día y hora → revisar y confirmar.
 *  El botón de confirmar queda al final, justo después de elegir la hora (y la página baja sola hasta él).
 *  El personal también elige el cliente. */
export function Reserva({ usuario, preServicio, preBarbero }: Props) {
  const router = useRouter();
  const avisar = useAviso();
  const staff = usuario.role !== "cliente";
  const esBarbero = usuario.role === "barbero";
  const [servicios, setServicios] = useState<Servicio[] | null>(null);
  const [barberos, setBarberos] = useState<Barbero[]>([]);
  const [clientes, setClientes] = useState<ClienteBasico[]>([]);
  const [error, setError] = useState("");
  const [ids, setIds] = useState<number[]>(preServicio ? [preServicio] : []);
  const [barberoId, setBarberoId] = useState<number | null>(esBarbero ? usuario.id : preBarbero ?? null);
  const [franjas, setFranjas] = useState<Franja[] | null>(null);
  const [errorFranjas, setErrorFranjas] = useState("");
  const [dia, setDia] = useState("");
  const [hora, setHora] = useState("");
  const [reservando, setReservando] = useState(false);
  const [recarga, setRecarga] = useState(0);
  const confirmar = useRef<HTMLElement>(null);
  // cliente (solo personal)
  const [tipoCliente, setTipoCliente] = useState<"registrado" | "nuevo">("nuevo");
  const [clienteId, setClienteId] = useState(0);
  const [invitado, setInvitado] = useState({ nombre: "", telefono: "", correo: "" });

  useEffect(() => {
    Promise.all([api.servicios(), api.barberos(), staff ? api.clientes() : Promise.resolve([])])
      .then(([s, b, c]) => { setServicios(s); setBarberos(b); setClientes(c); })
      .catch((e: Error) => setError(e.message));
  }, [staff]);

  const elegidos = useMemo(() => (servicios ?? []).filter((s) => ids.includes(s.id)), [servicios, ids]);
  const minutos = elegidos.reduce((t, s) => t + s.duration_minutes, 0);
  const total = elegidos.reduce((t, s) => t + s.price_cop, 0);
  const disponibles = useMemo(
    () => (elegidos.length ? barberos.filter((b) => elegidos.every((s) => b.service_ids.includes(s.id))) : []),
    [elegidos, barberos]);
  const barbero = disponibles.find((b) => b.id === barberoId) ?? null;

  const idBarbero = barbero?.id;
  useEffect(() => {
    setDia(""); setHora(""); setFranjas(null); setErrorFranjas("");
    if (!idBarbero || !minutos) return;
    api.franjas(idBarbero, minutos).then(setFranjas).catch((e: Error) => setErrorFranjas(e.message));
  }, [idBarbero, minutos, recarga]);

  const porDia = useMemo(() => {
    const m: Record<string, string[]> = {};
    for (const f of franjas ?? []) (m[f.date] ??= []).push(f.time);
    return m;
  }, [franjas]);
  const horas = porDia[dia] ?? [];
  const marcas = useMemo(() => Object.fromEntries(Object.entries(porDia).map(([d, h]) => [d, h.length])), [porDia]);
  const primerDia = Object.keys(porDia)[0];

  function elegirHora(h: string) {
    setHora(h);
    // Lleva al cliente al último paso para que vea el botón de confirmar sin tener que buscarlo.
    setTimeout(() => confirmar.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 80);
  }

  const alternar = (id: number) => setIds((a) => (a.includes(id) ? a.filter((x) => x !== id) : [...a, id]));
  const clienteListo = !staff || (tipoCliente === "registrado" ? clienteId > 0 : invitado.nombre.trim().length > 1);
  const faltantes = [
    staff && !clienteListo && "indicar el cliente",
    !elegidos.length && "elegir al menos un servicio",
    !esBarbero && !barbero && "elegir el barbero",
    !dia && "elegir el día",
    !hora && "elegir la hora",
  ].filter(Boolean) as string[];
  const listo = faltantes.length === 0;

  async function reservar() {
    if (!barbero || !dia || !hora || !elegidos.length) return;
    setReservando(true);
    try {
      await api.agendar({
        barber_id: barbero.id, service_ids: ids, date: dia, time: hora,
        ...(staff && tipoCliente === "registrado" ? { client_id: clienteId } : {}),
        ...(staff && tipoCliente === "nuevo" ? { guest_name: invitado.nombre, guest_phone: invitado.telefono, guest_email: invitado.correo } : {}),
      });
      avisar(staff
        ? `Cita confirmada para ${fechaLarga(dia)} a las ${hora12(hora)}.`
        : `¡Cita creada para ${fechaLarga(dia)} a las ${hora12(hora)}! Te llegará un recordatorio automático por correo.`);
      router.push("/citas");
    } catch (e) {
      const alts = e instanceof ApiError && e.alternativas.length ? " Prueba con: " + textoAlternativas(e.alternativas) : "";
      avisar((e as Error).message + alts, "err");
      setReservando(false);
      setRecarga((n) => n + 1);
    }
  }

  if (error) return <Vacio>{error}</Vacio>;
  if (!servicios) return <Vacio>Cargando…</Vacio>;
  let n = 0;
  const paso = (t: string, sub?: string) => (
    <div className="stepn"><i>{++n}</i><div><b>{t}</b>{sub && <small>{sub}</small>}</div></div>
  );

  return (
    <div className="reserva">
      <div className="rcol">
        {staff && (
          <section className="cd">
            {paso("¿Para quién es la cita?", "Si el cliente está en el local, no necesita cuenta.")}
            <div className="seg">
              <button type="button" className={tipoCliente === "nuevo" ? "on" : ""} onClick={() => setTipoCliente("nuevo")}>Cliente en el local</button>
              <button type="button" className={tipoCliente === "registrado" ? "on" : ""} onClick={() => setTipoCliente("registrado")}>Cliente registrado</button>
            </div>
            {tipoCliente === "registrado" ? (
              <label className="fl">Cliente
                <select value={clienteId} onChange={(e) => setClienteId(Number(e.target.value))}>
                  <option value={0}>Selecciona un cliente…</option>
                  {clientes.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}
                </select>
              </label>
            ) : (
              <div className="fgrid">
                <label className="fl">Nombre *<input value={invitado.nombre} onChange={(e) => setInvitado({ ...invitado, nombre: e.target.value })} placeholder="Nombre del cliente" /></label>
                <label className="fl">Celular (opcional)<input inputMode="tel" value={invitado.telefono} onChange={(e) => setInvitado({ ...invitado, telefono: e.target.value })} /></label>
                <label className="fl full">Correo (opcional, para enviarle la cita)<input type="email" value={invitado.correo} onChange={(e) => setInvitado({ ...invitado, correo: e.target.value })} /></label>
              </div>
            )}
          </section>
        )}

        <section className="cd">
          {paso("Elige tus servicios", "Puedes combinar varios en una misma cita.")}
          <div className="opciones">
            {servicios.map((s) => {
              const on = ids.includes(s.id);
              return (
                <button key={s.id} type="button" className={`opt ${on ? "on" : ""}`} aria-pressed={on} onClick={() => alternar(s.id)}>
                  <span className="chk"><Icono n="check" size={14} /></span>
                  <span className="oi"><Icono n={ICONO_TIPO[s.service_type]} size={18} /></span>
                  <span className="ot"><b>{s.name}</b><small>{minutosTexto(s.duration_minutes)}</small></span>
                  <span className="op">{cop(s.price_cop)}</span>
                </button>
              );
            })}
          </div>
        </section>

        {!esBarbero && (
          <section className="cd">
            {paso("Elige el barbero")}
            {!elegidos.length ? <p className="mute">Primero elige al menos un servicio.</p> : (
              <div className="opciones">
                {disponibles.length ? disponibles.map((b, i) => (
                  <button key={b.id} type="button" className={`opt ${b.id === barberoId ? "on" : ""}`} onClick={() => setBarberoId(b.id)}>
                    <Avatar nombre={b.full_name} foto={b.photo_url} indice={i} className="av" />
                    <span className="ot"><b>{b.full_name}</b><small>{b.specialties || "Barbero profesional"}</small></span>
                  </button>
                )) : <Vacio>Ningún barbero ofrece todos esos servicios juntos. Quita alguno o agenda por separado.</Vacio>}
              </div>
            )}
          </section>
        )}

        <section className="cd">
          {paso("Elige el día y la hora", minutos ? `Necesitas ${minutosTexto(minutos)} seguidos.` : undefined)}
          {!barbero ? <p className="mute">Elige servicios{esBarbero ? "" : " y barbero"} para ver la disponibilidad.</p> :
            errorFranjas ? <Vacio>{errorFranjas}</Vacio> : franjas === null ? <Vacio>Buscando horarios…</Vacio> :
            !franjas.length ? <Vacio>Sin horarios libres para esa duración. Prueba con otro barbero.</Vacio> : (
              <div className="pickdia">
                <Calendario seleccion={dia ? [dia] : []} marcas={marcas} habilitados={new Set(Object.keys(porDia))}
                  mesInicial={primerDia} onToggle={(d) => { setDia(d); setHora(""); }} />
                <div className="horas">
                  {!dia ? <p className="mute">Toca un día marcado del calendario.</p> : (
                    <>
                      <h4>{fechaLarga(dia)}</h4>
                      {[["Mañana", horas.filter((h) => +h.slice(0, 2) < 12)], ["Tarde", horas.filter((h) => +h.slice(0, 2) >= 12)]].map(([nombre, lista]) =>
                        (lista as string[]).length > 0 && (
                          <div key={nombre as string}>
                            <span className="gl">{nombre as string}</span>
                            <div className="slots">
                              {(lista as string[]).map((h) => (
                                <button key={h} type="button" className={`slot ${hora === h ? "on" : ""}`} onClick={() => elegirHora(h)}>{hora12(h)}</button>
                              ))}
                            </div>
                          </div>
                        ))}
                    </>
                  )}
                </div>
              </div>
            )}
        </section>

        <section ref={confirmar} className={`cd confirmar ${listo ? "listo" : ""}`}>
          {paso(staff ? "Revisa y crea la cita" : "Revisa y confirma tu cita")}
          <div className="conf-grid">
            <div>
              {elegidos.length ? (
                <ul className="resumen">
                  {elegidos.map((s) => <li key={s.id}><span>{s.name}</span><b>{cop(s.price_cop)}</b></li>)}
                </ul>
              ) : <p className="mute">Aún no has elegido servicios.</p>}
              <dl className="det">
                {barbero && <><dt>Barbero</dt><dd className="dd-foto">{barbero.photo_url && <Avatar nombre={barbero.full_name} foto={barbero.photo_url} className="av mini" />}{barbero.full_name}</dd></>}
                {dia && <><dt>Fecha</dt><dd>{fechaLarga(dia)}</dd></>}
                {hora && <><dt>Hora</dt><dd>{hora12(hora)}</dd></>}
                {minutos > 0 && <><dt>Duración</dt><dd>{minutosTexto(minutos)}</dd></>}
              </dl>
            </div>
            <div className="conf-acc">
              <div className="tot"><span>Total</span><b>{cop(total)}</b></div>
              <button className="btn full grande" disabled={reservando || !listo} onClick={reservar}>
                <Icono n="check" size={18} /> {reservando ? "Agendando…" : staff ? "Crear cita" : "Confirmar cita"}
              </button>
              {!listo && <small className="falta">Te falta: {faltantes.join(", ")}.</small>}
            </div>
          </div>
        </section>
      </div>

    </div>
  );
}
