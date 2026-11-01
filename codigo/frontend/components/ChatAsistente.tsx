"use client";

import { useCallback, useEffect, useId, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, type MensajeGuardado, type OpcionChat, type ReservaChat, type Usuario } from "@/lib/api";
import { primerNombre } from "@/lib/formato";
import { useAviso } from "./Aviso";
import { Logo, useNombreBarberia } from "./Barberia";
import { Icono } from "./Icono";
import { useSesion } from "./Sesion";

interface Mensaje {
  id: number;
  servidorId?: number; // id en el historial guardado (usuarios registrados)
  texto: string;
  quien: "bot" | "me";
  fuentes?: string[];
  opciones?: OpcionChat[];
  escribiendo?: boolean;
  calificable?: boolean;
  opinion?: number | null;
  pregunta?: string; // para que un visitante pueda calificar (no tiene historial)
}

/** Avisa a los demás chats abiertos (flotante y página) que la conversación cambió. */
const EVENTO_ACTUALIZADO = "bf:chat-actualizado";
const ESPERA_SONDEO = 3000;

const SUGERENCIAS: Record<string, string[]> = {
  visitante: ["¿Qué servicios ofrecen?", "¿Cuánto cuesta un corte?", "¿Cuál es el horario?", "Quiero agendar"],
  cliente: ["Quiero agendar", "Mis citas", "Cancelar una cita", "¿Qué corte me recomiendas?", "¿Cuál es el horario?"],
  barbero: ["¿Cómo limpio y desinfecto las máquinas?", "Mi agenda de hoy", "Mis próximas citas", "¿Cómo cierro mi puesto?", "Cancelar una cita"],
  administrador: ["¿Cuál es el horario?", "¿Cómo limpio las máquinas?", "Citas de hoy"],
};

let siguienteId = 0;

function saludo(usuario: Usuario | null): Mensaje {
  const nombre = usuario ? ` ${primerNombre(usuario.full_name)}` : "";
  const texto = !usuario
    ? "¡Hola! Soy el asistente de la barbería. Pregúntame por servicios, precios, horarios o estilos. Para agendar o cancelar citas, inicia sesión."
    : usuario.role === "barbero"
      ? `¡Hola${nombre}! Soy tu asistente interno. Pregúntame por procedimientos de limpieza y desinfección de las máquinas, tu agenda de hoy o tus próximas citas. Si no sé algo, se lo pregunto al administrador y lo aprendo.`
      : usuario.role === "administrador"
        ? `¡Hola${nombre}! Aquí puedes probarme. Lo que no sepa responder aparece en «Asistente IA → Por aprender» para que me lo enseñes.`
        : `¡Hola${nombre}! Soy el asistente de la barbería. Pregúntame por servicios, precios, horarios o estilos. También puedo agendar («agendar») y cancelar tus citas («cancelar cita»).`;
  return { id: ++siguienteId, texto, quien: "bot" };
}

const desdeServidor = (m: MensajeGuardado): Mensaje => ({
  id: ++siguienteId, servidorId: m.id, texto: m.text, quien: m.sender === "me" ? "me" : "bot",
  fuentes: m.sources, opciones: m.options, calificable: m.can_rate, opinion: m.feedback ?? null,
});

const pensando = (): Mensaje => ({ id: ++siguienteId, texto: "Pensando", quien: "bot", escribiendo: true });

interface Props { className?: string; onCerrar?: () => void; subtitulo?: string }

export function ChatAsistente({ className = "", onCerrar, subtitulo }: Props) {
  const { usuario, cargando } = useSesion();
  const avisar = useAviso();
  const router = useRouter();
  const yo = useId(); // identifica esta ventana de chat entre las abiertas
  const [mensajes, setMensajes] = useState<Mensaje[]>(() => [saludo(null)]);
  const [texto, setTexto] = useState("");
  const [esperando, setEsperando] = useState(false);
  const lista = useRef<HTMLDivElement>(null);
  const sondeo = useRef<ReturnType<typeof setTimeout> | null>(null);
  const uid = usuario?.id;
  const nombreBarberia = useNombreBarberia();

  // Carga la conversación guardada. Si la última pregunta aún se está respondiendo (por ejemplo, la persona
  // cambió de página mientras el asistente pensaba), muestra «Pensando» y vuelve a consultar hasta que llegue.
  const cargarHistorial = useCallback(async (intento = 0) => {
    if (sondeo.current) clearTimeout(sondeo.current);
    if (!usuario) return;
    try {
      const h = await api.historialChat();
      const guardados = h.messages.map(desdeServidor);
      setMensajes([saludo(usuario), ...guardados, ...(h.pending ? [pensando()] : [])]);
      setEsperando(h.pending);
      if (h.pending && intento < 80) sondeo.current = setTimeout(() => cargarHistorial(intento + 1), ESPERA_SONDEO);
    } catch {
      /* sin conexión: se queda con lo que hay en pantalla */
    }
  }, [uid]);

  // Al iniciar o cerrar sesión la conversación cambia: el usuario ve su historial; el visitante empieza de cero.
  useEffect(() => {
    if (cargando) return;
    if (usuario) cargarHistorial();
    else { setMensajes([saludo(null)]); setEsperando(false); }
    return () => { if (sondeo.current) clearTimeout(sondeo.current); };
  }, [uid, cargando]);

  // Si se escribe en otra ventana del asistente (la flotante o la página), esta se pone al día.
  useEffect(() => {
    const alActualizar = (e: Event) => { if ((e as CustomEvent).detail !== yo) cargarHistorial(); };
    window.addEventListener(EVENTO_ACTUALIZADO, alActualizar);
    return () => window.removeEventListener(EVENTO_ACTUALIZADO, alActualizar);
  }, [yo, cargarHistorial]);

  useEffect(() => {
    lista.current?.scrollTo({ top: lista.current.scrollHeight });
  }, [mensajes]);

  async function preguntar(pregunta: string, reserva?: ReservaChat) {
    if (esperando) return;
    setEsperando(true);
    const temporal = pensando();
    setMensajes((ms) => [...ms, { id: ++siguienteId, texto: pregunta, quien: "me" }, temporal]);
    let respuesta: Mensaje;
    try {
      const r = await api.chat(pregunta, reserva);
      respuesta = { id: ++siguienteId, servidorId: r.id, texto: r.reply, quien: "bot", fuentes: r.sources,
        opciones: r.options, calificable: r.can_rate, opinion: null, pregunta };
    } catch (e) {
      respuesta = { id: ++siguienteId, texto: "No pude responder: " + (e as Error).message, quien: "bot" };
    }
    setMensajes((ms) => [...ms.filter((m) => m.id !== temporal.id), respuesta]);
    setEsperando(false);
    if (usuario) window.dispatchEvent(new CustomEvent(EVENTO_ACTUALIZADO, { detail: yo }));
  }

  function elegir(opcion: OpcionChat) {
    if (opcion.action) return router.push(`/${opcion.action}`);
    if (opcion.book) return preguntar(`Quiero el horario ${opcion.label}`, opcion.book);
    if (opcion.send) return preguntar(opcion.send);
  }

  async function opinar(m: Mensaje, util: boolean) {
    setMensajes((ms) => ms.map((x) => (x.id === m.id ? { ...x, opinion: util ? 1 : -1 } : x)));
    try {
      const r = await api.opinarChat(m.servidorId && usuario
        ? { useful: util, message_id: m.servidorId }
        : { useful: util, question: m.pregunta, answer: m.texto });
      if (!util) avisar(r.message);
    } catch (e) { avisar((e as Error).message, "err"); }
  }

  async function nuevaConversacion() {
    if (!usuario || !window.confirm("¿Borrar esta conversación? El asistente no olvidará lo que ya aprendió.")) return;
    try {
      await api.borrarHistorialChat();
      setMensajes([saludo(usuario)]);
      window.dispatchEvent(new CustomEvent(EVENTO_ACTUALIZADO, { detail: yo }));
    } catch (e) { avisar((e as Error).message, "err"); }
  }

  function enviar(e: FormEvent) {
    e.preventDefault();
    const t = texto.trim();
    if (!t || esperando) return;
    setTexto("");
    preguntar(t);
  }

  const rol = usuario?.role ?? "visitante";
  const sinPreguntas = !mensajes.some((m) => m.quien === "me");
  const ultimoBot = [...mensajes].reverse().find((m) => m.quien === "bot" && !m.escribiendo)?.id;
  const sub = subtitulo ?? (rol === "barbero" ? "Asistente interno · procedimientos y agenda" : "En línea · responde al instante");

  return (
    <div className={`chat ${className}`} id="asistente">
      <div className="ch">
        <Logo size={40} />
        <div><b>Asistente de {nombreBarberia}</b><small><i className="dot" /> {sub}</small></div>
        <div className="ch-acts">
          {usuario && mensajes.length > 1 && (
            <button type="button" className="ico-btn glass" onClick={nuevaConversacion} title="Nueva conversación" aria-label="Nueva conversación"><Icono n="recargar" size={16} /></button>
          )}
          {onCerrar && <button type="button" className="ico-btn glass" onClick={onCerrar} aria-label="Cerrar asistente"><Icono n="x" /></button>}
        </div>
      </div>
      <div className="msgs" ref={lista}>
        {mensajes.map((m) => (
          <div key={m.id} className={`m ${m.quien} ${m.escribiendo ? "typing" : ""}`}>
            {m.texto}
            {m.fuentes && m.fuentes.length > 0 && <small>Fuentes: {m.fuentes.join(", ")}</small>}
            {m.id === ultimoBot && m.opciones && m.opciones.length > 0 && (
              <div className="opts">
                {m.opciones.map((o, i) => (
                  <button key={i} type="button" className={o.image ? "con-foto" : ""} disabled={esperando} onClick={() => elegir(o)}>
                    {o.image && <img src={o.image} alt="" loading="lazy" />}{o.label}
                  </button>
                ))}
              </div>
            )}
            {m.quien === "bot" && m.calificable && (
              <div className="opina">
                {m.opinion == null ? (
                  <>
                    <span>¿Te sirvió?</span>
                    <button type="button" onClick={() => opinar(m, true)} aria-label="Sí me sirvió" title="Sí me sirvió"><Icono n="arriba" size={14} /></button>
                    <button type="button" onClick={() => opinar(m, false)} aria-label="No me sirvió" title="No me sirvió"><Icono n="abajo" size={14} /></button>
                  </>
                ) : <span>{m.opinion > 0 ? "¡Gracias por tu opinión!" : "Gracias: el equipo me enseñará una mejor respuesta."}</span>}
              </div>
            )}
          </div>
        ))}
      </div>
      {sinPreguntas && !esperando && (
        <div className="chips-chat">
          {(SUGERENCIAS[rol] ?? SUGERENCIAS.visitante).map((s) => <button key={s} type="button" onClick={() => preguntar(s)}>{s}</button>)}
        </div>
      )}
      <form className="cf" onSubmit={enviar}>
        <input value={texto} onChange={(e) => setTexto(e.target.value)}
          placeholder={rol === "barbero" ? "Pregunta por un procedimiento o tu agenda…" : "Pregunta o escribe «agendar»…"}
          autoComplete="off" maxLength={500} aria-label="Mensaje para el asistente" />
        <button className="send" aria-label="Enviar" disabled={esperando}><Icono n="enviar" size={18} /></button>
      </form>
    </div>
  );
}
