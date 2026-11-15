"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Modal, useAviso, Vacio } from "@/components/Aviso";
import { ChatAsistente } from "@/components/ChatAsistente";
import { Icono } from "@/components/Icono";
import { Panel } from "@/components/Panel";
import { api, type DocumentoConocimiento, type DocumentoIn, type PreguntaPendiente, type Visibilidad } from "@/lib/api";
import { ROLES } from "@/lib/formato";

type Pestana = "aprender" | "conocimiento" | "probar";
type Estado = "pendiente" | "respondida" | "descartada";

const VISIBILIDAD: Record<Visibilidad, string> = { public: "Todos (clientes y visitantes)", internal: "Solo personal (barberos)" };
const QUIEN: Record<string, string> = { ...ROLES, visitante: "Visitante" };
const DOC_VACIO: DocumentoIn = { title: "", content: "", access_level: "public", question: null, is_active: true };

function fecha(iso?: string) {
  return iso ? new Date(iso).toLocaleDateString("es-CO", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) : "";
}

function PorAprender({ onCambio }: { onCambio: () => void }) {
  const avisar = useAviso();
  const [estado, setEstado] = useState<Estado>("pendiente");
  const [lista, setLista] = useState<PreguntaPendiente[] | null>(null);
  const [error, setError] = useState("");
  const [ensenando, setEnsenando] = useState<PreguntaPendiente | null>(null);
  const [form, setForm] = useState({ question: "", answer: "", access_level: "public" as Visibilidad });
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(() => {
    setLista(null);
    api.preguntasPendientes(estado).then(setLista).catch((e: Error) => setError(e.message));
  }, [estado]);
  useEffect(cargar, [cargar]);

  function abrir(p: PreguntaPendiente) {
    setEnsenando(p);
    setForm({ question: p.question, answer: "", access_level: p.access_level });
  }

  async function ensenar(e: FormEvent) {
    e.preventDefault();
    if (!ensenando) return;
    setGuardando(true);
    try {
      await api.ensenar(ensenando.id, form);
      avisar("¡Aprendido! El asistente ya responde esta pregunta y se lo avisó a quien la hizo.");
      setEnsenando(null);
      cargar();
      onCambio();
    } catch (x) { avisar((x as Error).message, "err"); }
    setGuardando(false);
  }

  async function descartar(p: PreguntaPendiente) {
    try { await api.descartarPregunta(p.id); avisar("Pregunta descartada", "warn"); cargar(); onCambio(); }
    catch (x) { avisar((x as Error).message, "err"); }
  }

  return (
    <>
      <div className="toolrow">
        <p className="mute">Preguntas que el asistente no supo responder o cuya respuesta no le sirvió a alguien. Escribe la respuesta una vez: queda como respuesta oficial y llama3 la usa para responder con sus propias palabras.</p>
        <div className="seg">
          {(["pendiente", "respondida", "descartada"] as Estado[]).map((e) => (
            <button key={e} type="button" className={estado === e ? "on" : ""} onClick={() => setEstado(e)}>
              {e === "pendiente" ? "Por aprender" : e === "respondida" ? "Aprendidas" : "Descartadas"}
            </button>
          ))}
        </div>
      </div>
      {error ? <Vacio>{error}</Vacio> : !lista ? <Vacio>Cargando…</Vacio> : !lista.length ? (
        <Vacio>{estado === "pendiente" ? "No hay preguntas por aprender. ¡El asistente está al día!" : "Nada por aquí todavía."}</Vacio>
      ) : (
        <div className="aprender">
          {lista.map((p) => (
            <article key={p.id} className="cd preg">
              <div className="preg-h">
                <b>«{p.question}»</b>
                {p.times_asked > 1 && <span className="pill amber"><i className="dot" />{p.times_asked} veces</span>}
              </div>
              <div className="tags izq">
                <span className="tag">{QUIEN[p.asked_by_role] ?? p.asked_by_role}</span>
                <span className="tag">{p.reason === "no_util" ? "La respuesta no sirvió" : "No supo responder"}</span>
                <span className="tag">{p.access_level === "internal" ? "Interna" : "Pública"}</span>
                <small>{fecha(p.updated_at)}</small>
              </div>
              {p.bot_answer && <p className="bot-ans"><small>Había respondido:</small> {p.bot_answer}</p>}
              {estado === "pendiente" && (
                <div className="bacts">
                  <button type="button" className="btn sm" onClick={() => abrir(p)}><Icono n="chispa" size={15} /> Enseñar respuesta</button>
                  <button type="button" className="btn line sm" onClick={() => descartar(p)}>Descartar</button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}

      {ensenando && (
        <Modal titulo="Enseñar al asistente" onCerrar={() => setEnsenando(null)}>
          <form className="form" onSubmit={ensenar}>
            <label className="fl">Pregunta (puedes dejarla más clara)
              <input required value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })} />
            </label>
            <label className="fl">Respuesta
              <textarea required rows={6} value={form.answer} placeholder="Escribe la respuesta tal como quieres que la dé el asistente."
                onChange={(e) => setForm({ ...form, answer: e.target.value })} />
            </label>
            <label className="fl">¿Quién puede ver esta respuesta?
              <select value={form.access_level} onChange={(e) => setForm({ ...form, access_level: e.target.value as Visibilidad })}>
                {(Object.keys(VISIBILIDAD) as Visibilidad[]).map((v) => <option key={v} value={v}>{VISIBILIDAD[v]}</option>)}
              </select>
            </label>
            <div className="act"><button type="button" className="btn line" onClick={() => setEnsenando(null)}>Cancelar</button>
              <button className="btn" disabled={guardando}>Guardar y aprender</button></div>
          </form>
        </Modal>
      )}
    </>
  );
}

function Conocimiento() {
  const avisar = useAviso();
  const [docs, setDocs] = useState<DocumentoConocimiento[] | null>(null);
  const [error, setError] = useState("");
  const [editando, setEditando] = useState<DocumentoConocimiento | "nuevo" | null>(null);
  const [form, setForm] = useState<DocumentoIn>(DOC_VACIO);
  const [porEliminar, setPorEliminar] = useState<DocumentoConocimiento | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const cargar = useCallback(() => { api.documentos().then(setDocs).catch((e: Error) => setError(e.message)); }, []);
  useEffect(cargar, [cargar]);

  function abrir(d: DocumentoConocimiento | "nuevo") {
    setEditando(d);
    setForm(d === "nuevo" ? DOC_VACIO : { title: d.title, content: d.content, access_level: d.access_level, question: d.question, is_active: d.is_active });
  }

  async function guardar(e: FormEvent) {
    e.preventDefault();
    setOcupado(true);
    try {
      if (editando === "nuevo") await api.crearDocumento(form);
      else if (editando) await api.editarDocumento(editando.id, form);
      avisar("Guardado. El asistente ya usa esta información.");
      setEditando(null);
      cargar();
    } catch (x) { avisar((x as Error).message, "err"); }
    setOcupado(false);
  }

  async function eliminar() {
    if (!porEliminar) return;
    setOcupado(true);
    try { await api.eliminarDocumento(porEliminar.id); avisar("Eliminado del conocimiento del asistente", "warn"); setPorEliminar(null); cargar(); }
    catch (x) { avisar((x as Error).message, "err"); }
    setOcupado(false);
  }

  async function reindexar() {
    setOcupado(true);
    try {
      const r = await api.reindexar();
      avisar(r.embeddings_ok ? "Índice reconstruido con búsqueda semántica." : "Índice reconstruido. La IA aún no responde, así que por ahora busca por palabras clave.", r.embeddings_ok ? "ok" : "warn");
    } catch (x) { avisar((x as Error).message, "err"); }
    setOcupado(false);
  }

  if (error) return <Vacio>{error}</Vacio>;
  if (!docs) return <Vacio>Cargando…</Vacio>;
  const grupos: [string, DocumentoConocimiento[]][] = [
    ["Documentos y procedimientos", docs.filter((d) => d.kind === "documento")],
    ["Respuestas aprendidas", docs.filter((d) => d.kind === "aprendido")],
  ];

  return (
    <>
      <div className="toolrow">
        <p className="mute">Lo que sabe el asistente. Lo marcado como <b>solo personal</b> (por ejemplo, la limpieza de las máquinas) solo lo ven los barberos y el administrador. Los servicios y precios se toman solos del catálogo.</p>
        <div className="row">
          <button className="btn line" disabled={ocupado} onClick={reindexar}><Icono n="recargar" size={16} /> Reindexar</button>
          <button className="btn" onClick={() => abrir("nuevo")}><Icono n="mas" size={16} /> Nuevo documento</button>
        </div>
      </div>
      {grupos.map(([titulo, lista]) => (
        <section key={titulo} className="kgrupo">
          <h3>{titulo} <small>({lista.length})</small></h3>
          {!lista.length ? <Vacio>{titulo === "Respuestas aprendidas" ? "Cuando enseñes una pregunta pendiente aparecerá aquí." : "Sin documentos."}</Vacio> : (
            <div className="kdocs">
              {lista.map((d) => (
                <article key={d.id} className={`cd kdoc ${d.is_active ? "" : "off"}`}>
                  <div className="kdoc-h">
                    <Icono n={d.kind === "aprendido" ? "chispa" : "libro"} size={16} />
                    <b>{d.title}</b>
                    <span className={`pill ${d.access_level === "internal" ? "blue" : "green"}`}>{d.access_level === "internal" ? "Solo personal" : "Público"}</span>
                    {!d.is_active && <span className="pill gray">Inactivo</span>}
                  </div>
                  {d.question && <small>Pregunta: «{d.question}»</small>}
                  <p className="kdoc-t">{d.content}</p>
                  <div className="bacts">
                    <button type="button" className="btn line sm" onClick={() => abrir(d)}><Icono n="editar" size={15} /> Editar</button>
                    <button type="button" className="btn line sm peligro" onClick={() => setPorEliminar(d)}><Icono n="basura" size={15} /> Eliminar</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      ))}

      {editando && (
        <Modal titulo={editando === "nuevo" ? "Nuevo documento" : `Editar «${editando.title}»`} onCerrar={() => setEditando(null)}>
          <form className="form" onSubmit={guardar}>
            <label className="fl">Título<input required value={form.title} placeholder="Ej.: Limpieza de la silla y el lavacabezas" onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
            {editando !== "nuevo" && editando.kind === "aprendido" && (
              <label className="fl">Pregunta<input value={form.question ?? ""} onChange={(e) => setForm({ ...form, question: e.target.value })} /></label>
            )}
            <label className="fl">Contenido
              <textarea required rows={9} value={form.content} placeholder="Escribe el procedimiento o la información. Puedes separar en párrafos."
                onChange={(e) => setForm({ ...form, content: e.target.value })} />
            </label>
            <div className="fgrid">
              <label className="fl">¿Quién lo puede ver?
                <select value={form.access_level} onChange={(e) => setForm({ ...form, access_level: e.target.value as Visibilidad })}>
                  {(Object.keys(VISIBILIDAD) as Visibilidad[]).map((v) => <option key={v} value={v}>{VISIBILIDAD[v]}</option>)}
                </select>
              </label>
              <label className="fl chk-l"><input type="checkbox" checked={form.is_active !== false} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Activo (el asistente lo usa)</label>
            </div>
            <div className="act"><button type="button" className="btn line" onClick={() => setEditando(null)}>Cancelar</button>
              <button className="btn" disabled={ocupado}>Guardar</button></div>
          </form>
        </Modal>
      )}

      {porEliminar && (
        <Modal titulo="Eliminar del conocimiento" onCerrar={() => setPorEliminar(null)}>
          <div className="confirma">
            <p>¿Eliminar <b>{porEliminar.title}</b>? El asistente dejará de usar esta información.</p>
            <div className="act"><button type="button" className="btn line" onClick={() => setPorEliminar(null)}>Cancelar</button>
              <button type="button" className="btn danger" disabled={ocupado} onClick={eliminar}>Sí, eliminar</button></div>
          </div>
        </Modal>
      )}
    </>
  );
}

function AsistenteIA() {
  const [pestana, setPestana] = useState<Pestana>("aprender");
  const [pendientes, setPendientes] = useState<number | null>(null);
  const contar = useCallback(() => { api.preguntasPendientes().then((l) => setPendientes(l.length)).catch(() => {}); }, []);
  useEffect(contar, [contar]);

  return (
    <>
      <div className="seg grande">
        <button type="button" className={pestana === "aprender" ? "on" : ""} onClick={() => setPestana("aprender")}>
          Por aprender{pendientes ? <span className="cnt">{pendientes}</span> : null}
        </button>
        <button type="button" className={pestana === "conocimiento" ? "on" : ""} onClick={() => setPestana("conocimiento")}>Conocimiento</button>
        <button type="button" className={pestana === "probar" ? "on" : ""} onClick={() => setPestana("probar")}>Probar asistente</button>
      </div>
      {pestana === "aprender" && <PorAprender onCambio={contar} />}
      {pestana === "conocimiento" && <Conocimiento />}
      {pestana === "probar" && (
        <div className="asis">
          <ChatAsistente className="grande" subtitulo="Modo prueba · ves también lo interno" />
          <aside className="cd asis-ayuda">
            <h3>Cómo aprende</h3>
            <div className="ayuda-i"><span className="ic"><Icono n="alerta" size={18} /></span><p>Si no sabe algo, o alguien marca que la respuesta no le sirvió, la pregunta llega a «Por aprender».</p></div>
            <div className="ayuda-i"><span className="ic"><Icono n="chispa" size={18} /></span><p>Escribes la respuesta una vez: queda guardada como respuesta oficial y llama3 la redacta cuando alguien vuelve a preguntar (si la IA no responde, se usa el texto guardado).</p></div>
            <div className="ayuda-i"><span className="ic"><Icono n="libro" size={18} /></span><p>Agendar, cancelar y consultar citas se hacen directo en la base de datos, para que la IA nunca invente horarios.</p></div>
          </aside>
        </div>
      )}
    </>
  );
}

export default function AsistenteAdmin() {
  return <Panel roles={["administrador"]} titulo="Asistente IA">{() => <AsistenteIA />}</Panel>;
}
