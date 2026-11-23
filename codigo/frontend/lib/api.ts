// Tipos de la API y funciones fetch. Todas las llamadas al backend pasan por aquí.
import { leerToken } from "./auth";

// ---------- tipos ----------

export type Rol = "cliente" | "barbero" | "administrador";
export type TipoServicio = "corte" | "barba" | "combo" | "tratamiento";
export type EstadoCita =
  | "pendiente" | "confirmada" | "completada" | "inasistencia"
  | "cancelada_cliente" | "cancelada_admin" | "cancelada_sin_confirmar";

export interface Usuario {
  id: number;
  email: string;
  full_name: string;
  role: Rol;
  style_pref: string;
  photo_url?: string | null;
}

export interface Sesion {
  token: string;
  user: Usuario;
}

export interface Servicio {
  id: number;
  name: string;
  description: string | null;
  price_cop: number;
  duration_minutes: number;
  service_type: TipoServicio;
  is_active: boolean;
}

export interface ServicioIn {
  name: string;
  description: string;
  price_cop: number;
  duration_minutes: number;
  service_type: TipoServicio;
}

export interface Barbero {
  id: number;
  full_name: string;
  is_active: boolean;
  specialties: string;
  service_ids: number[];
  work_days: number[];
  photo_url?: string | null;
}

export interface BarberoDetalle extends Barbero {
  email: string;
}

export interface BarberoEditarIn {
  email: string;
  full_name: string;
  password: string;
  specialties: string;
  service_ids: number[];
}

export interface BarberoIn {
  email: string;
  full_name: string;
  password: string;
  specialties: string;
  service_ids: number[];
  work_days: number[];
}

interface BarberiaBase {
  id: number;
  nombre: string;
  direccion: string;
  horario: string;
  descripcion: string;
  buzon_url: string;
  logo_url?: string | null;
}

/** Identidad pública de la barbería (nombre, datos y logo), editable por el administrador en «Ajustes». */
export interface Marca {
  nombre: string;
  direccion: string;
  horario: string;
  descripcion: string;
  logo_url?: string | null;
}

export interface BarberiaResumen extends BarberiaBase {
  servicios: number;
  barberos: number;
}

export interface BarberiaDetalle extends BarberiaBase {
  servicios: Servicio[];
  barberos: Barbero[];
}

export interface Franja {
  date: string; // AAAA-MM-DD
  time: string; // HH:MM
}

export interface Cita {
  id: number;
  date: string;
  time: string;
  status: EstadoCita;
  service: string;
  services: string[];
  barber: string;
  barber_id: number;
  client: string;
  client_phone: string | null;
  walk_in: boolean;
  price: number;
  duration: number;
  // Feature 011: probabilidad de inasistencia (0 a 1). Solo llega para barberos y administradores.
  riesgo?: number | null;
  riesgo_alto?: boolean;
}

/** Feature 011: modelo de predicción de inasistencias en uso. */
export interface ModeloInasistencia {
  activo: boolean;
  umbral: number;
  citas_proximas: number;
  citas_riesgo_alto: number;
  version?: string | null;
  origen?: "sintetico" | "real" | null;
  algoritmo?: string | null;
  entrenado?: string | null;
  metricas?: { auc: number | null; recall: number; precision: number; alertas_pct: number; n: number } | null;
  importancia?: Record<string, number> | null;
}

export interface CitaIn {
  barber_id?: number;
  service_ids?: number[];
  service_id?: number;
  date: string;
  time: string;
  // solo personal: cita creada en el local
  client_id?: number;
  guest_name?: string;
  guest_phone?: string;
  guest_email?: string;
}

export interface DiaCalendario { date: string; total: number; ocupadas: number; bloqueo?: string | null }
export interface Festivo { id: number; date: string; motivo: string }
export interface CitaAfectada { id: number; date: string; time: string; client: string; barber: string; service: string }
export interface Ausencia { id: number; barber_id: number; barber: string; date_from: string; date_to: string; motivo: string }
export interface ClienteBasico { id: number; full_name: string }
export interface Estadisticas {
  ingresos_mes: number; ingresos_mes_anterior: number; ingresos_hoy: number; por_cobrar: number;
  citas_mes: number; citas_hoy: number; pendientes: number; ticket_promedio: number; tasa_cancelacion: number;
  ingresos_6_meses: { mes: string; etiqueta: string; total: number; citas: number }[];
  estados: Record<string, number>;
  top_servicios: { nombre: string; cantidad: number; ingresos: number }[];
  barberos: { nombre: string; citas: number; completadas: number; ingresos: number }[];
  proximas: Cita[];
}
export interface Ajustes {
  barberia: string; direccion: string; horario: string;
  recordatorio_minutos: number; confirmar_minutos: number; buzon_url: string;
}

export interface RegistroIn {
  email: string;
  full_name: string;
  password: string;
  accept_policy: boolean;
}

export interface CuentaIn {
  full_name?: string;
  email?: string;
  style_pref?: string;
  current_password?: string;
  new_password?: string;
}

export interface GenerarDisponibilidadIn {
  barber_id: number;
  date_from: string;
  date_to: string;
  start: string;
  end: string;
  minutes: number;
  days?: number[]; // sin indicar, el servidor usa los días de trabajo del barbero
  dates?: string[]; // fechas concretas elegidas en el calendario
}

export interface ReservaChat { barber_id: number; service_id: number; date: string; time: string }

export interface OpcionChat {
  label: string;
  send?: string;
  action?: "registro" | "login";
  book?: ReservaChat;
  image?: string; // foto del barbero
}

export interface RespuestaChat {
  reply: string;
  sources?: string[];
  options?: OpcionChat[];
  id?: number; // mensaje guardado en el historial (solo usuarios registrados)
  can_rate?: boolean;
}

export interface MensajeGuardado {
  id: number;
  sender: "me" | "bot";
  text: string;
  sources?: string[];
  options?: OpcionChat[];
  can_rate?: boolean;
  feedback?: number | null;
}

export interface HistorialChat { messages: MensajeGuardado[]; pending: boolean }

/** Feature 012: respuesta del asistente de voz (servicio bf-voz, detrás de /voz/). */
export interface RespuestaVoz {
  transcripcion: string;
  intencion: { intencion: "pregunta" | "agendar" | "cancelar" | "mis_citas" | "pqrs" | "saludo"; tipo_pqrs?: string };
  metodo_intencion: "llm" | "reglas";
  mensaje?: string | null; // frase que se le envió al chat
  respuesta: RespuestaChat;
  audio?: string | null; // WAV en base64 (Piper); si no llega, el navegador lee la respuesta
  tiempos_ms: Record<string, number>;
}

/** Feature 012: PQRS que llegan por el asistente de voz (vista del administrador). */
export type EstadoPqrs = "abierta" | "en_tramite" | "cerrada";
export interface Pqrs {
  id: number; radicado: string; tipo: "peticion" | "queja" | "reclamo" | "sugerencia";
  descripcion: string; resumen: string | null; canal: string; estado: EstadoPqrs; quien: string;
  correo: string | null; respuesta: string | null; respondida_at: string | null; created_at: string | null;
}

export type Visibilidad = "public" | "internal";

export interface DocumentoConocimiento {
  id: number;
  title: string;
  content: string;
  access_level: Visibilidad;
  kind: "documento" | "aprendido";
  question: string | null;
  is_active: boolean;
  updated_at?: string;
}

export interface DocumentoIn {
  title: string;
  content: string;
  access_level: Visibilidad;
  question?: string | null;
  is_active?: boolean;
}

export interface PreguntaPendiente {
  id: number;
  question: string;
  access_level: Visibilidad;
  asked_by_role: string;
  reason: "sin_respuesta" | "no_util";
  bot_answer: string | null;
  times_asked: number;
  status: string;
  created_at?: string;
  updated_at?: string;
}

// ---------- cliente HTTP ----------

export class ApiError extends Error {
  constructor(mensaje: string, public status: number, public alternativas: Franja[] = []) {
    super(mensaje);
  }
}

type Metodo = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

async function pedir<T>(ruta: string, metodo: Metodo = "GET", cuerpo?: unknown): Promise<T> {
  const token = leerToken();
  let r: Response;
  try {
    r = await fetch("/api" + ruta, {
      method: metodo,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    });
  } catch {
    throw new ApiError("No se pudo conectar con el servidor. Revisa tu conexión.", 0);
  }
  let datos: unknown = {};
  try {
    const texto = await r.text();
    datos = texto ? JSON.parse(texto) : {};
  } catch {
    /* respuesta sin JSON */
  }
  if (!r.ok) {
    const detalle = (datos as { detail?: unknown }).detail;
    let mensaje: string | undefined;
    let alternativas: Franja[] = [];
    if (typeof detalle === "string") mensaje = detalle;
    else if (Array.isArray(detalle)) mensaje = "Revisa los datos del formulario.";
    else if (detalle && typeof detalle === "object") {
      const d = detalle as { message?: string; alternatives?: Franja[] };
      mensaje = d.message;
      alternativas = d.alternatives ?? [];
    }
    mensaje ??= r.status >= 500
      ? `El servidor no respondió bien (código ${r.status}). Abre /api/health para ver el estado.`
      : `Error ${r.status}`;
    throw new ApiError(mensaje, r.status, alternativas);
  }
  return datos as T;
}

/** Envía una nota de voz al servicio de voz. Va aparte de pedir() porque es multipart y no JSON. */
async function enviarVoz(audio: Blob, conVoz: boolean): Promise<RespuestaVoz> {
  const token = leerToken();
  const datos = new FormData();
  const extension = audio.type.includes("ogg") ? "ogg" : audio.type.includes("mp4") ? "m4a" : "webm";
  datos.append("audio", audio, `nota.${extension}`);
  datos.append("responder_con_voz", String(conVoz));
  let r: Response;
  try {
    r = await fetch("/voz/", { method: "POST", body: datos, headers: token ? { Authorization: `Bearer ${token}` } : {} });
  } catch {
    throw new ApiError("No se pudo conectar con el asistente de voz.", 0);
  }
  let cuerpo: { detail?: unknown } = {};
  try { cuerpo = await r.json(); } catch { /* sin JSON */ }
  if (!r.ok) {
    const detalle = typeof cuerpo.detail === "string" ? cuerpo.detail : undefined;
    throw new ApiError(detalle ?? (r.status === 502 || r.status === 503 || r.status === 504
      ? "El asistente de voz no está disponible en este momento. Escribe tu pregunta."
      : `Error ${r.status}`), r.status);
  }
  return cuerpo as RespuestaVoz;
}

type Ok = { ok: boolean };

export const api = {
  // sesión y cuenta
  setup: () => pedir<{ hay_admin: boolean }>("/setup"),
  registrar: (datos: RegistroIn) => pedir<Sesion>("/register", "POST", datos),
  login: (email: string, password: string) => pedir<Sesion>("/login", "POST", { email, password }),
  yo: () => pedir<Usuario>("/me"),
  actualizarCuenta: (datos: CuentaIn) => pedir<{ user: Usuario }>("/me", "PATCH", datos),

  // identidad de la barbería
  marca: () => pedir<Marca>("/brand"),
  actualizarMarca: (datos: Omit<Marca, "logo_url">) => pedir<Marca>("/brand", "PUT", datos),
  subirLogo: (image: string) => pedir<Marca>("/brand/logo", "PUT", { image }),
  quitarLogo: () => pedir<Ok>("/brand/logo", "DELETE"),

  // barberías
  barberias: () => pedir<BarberiaResumen[]>("/barberias"),
  barberia: (id: number) => pedir<BarberiaDetalle>(`/barberias/${id}`),

  // servicios
  servicios: () => pedir<Servicio[]>("/services"),
  crearServicio: (datos: ServicioIn) => pedir<Ok>("/services", "POST", datos),
  editarServicio: (id: number, datos: ServicioIn) => pedir<Ok>(`/services/${id}`, "PUT", datos),
  alternarServicio: (id: number) => pedir<Ok>(`/services/${id}/toggle`, "POST"),

  // barberos
  barberos: () => pedir<Barbero[]>("/barbers"),
  crearBarbero: (datos: BarberoIn) => pedir<{ ok: boolean; id: number }>("/barbers", "POST", datos),
  subirFoto: (id: number, image: string) => pedir<{ ok: boolean; photo_url: string }>(`/barbers/${id}/photo`, "PUT", { image }),
  quitarFoto: (id: number) => pedir<Ok>(`/barbers/${id}/photo`, "DELETE"),
  barbero: (id: number) => pedir<BarberoDetalle>(`/barbers/${id}`),
  editarBarbero: (id: number, datos: BarberoEditarIn) => pedir<Ok>(`/barbers/${id}`, "PUT", datos),
  eliminarBarbero: (id: number) => pedir<Ok>(`/barbers/${id}`, "DELETE"),
  alternarBarbero: (id: number) => pedir<{ ok: boolean; reasignadas: number; canceladas: number }>(`/barbers/${id}/toggle`, "POST"),
  actualizarDias: (id: number, work_days: number[]) => pedir<Ok>(`/barbers/${id}/days`, "PUT", { work_days }),

  // disponibilidad
  franjas: (barberoId: number, minutos = 30) => pedir<Franja[]>(`/availability?barber_id=${barberoId}&minutes=${minutos}`),
  calendario: (barberoId: number, mes: string) =>
    pedir<DiaCalendario[]>(`/availability/calendar?barber_id=${barberoId}&month=${mes}`),
  cerrarDias: (barber_id: number, dates: string[]) => pedir<Ok>("/availability/close", "POST", { barber_id, dates }),
  generarDisponibilidad: (datos: GenerarDisponibilidadIn) => pedir<Ok>("/availability", "POST", datos),

  // festivos (RF09) y ausencias de barberos (RF17)
  festivos: () => pedir<Festivo[]>("/closed-days"),
  crearFestivo: (date: string, motivo: string, date_to?: string) =>
    pedir<{ id: number; dias: number; canceladas: number }>("/closed-days", "POST", { date, date_to: date_to || null, motivo }),
  cargarFestivosColombia: (year: number) => pedir<{ creados: number; canceladas: number }>("/closed-days/colombia", "POST", { year }),
  borrarFestivo: (id: number) => pedir<Ok>(`/closed-days/${id}`, "DELETE"),
  afectadasPorFestivo: (date: string, date_to?: string) =>
    pedir<CitaAfectada[]>(`/closed-days/preview?date=${date}${date_to ? `&date_to=${date_to}` : ""}`),
  afectadasPorAusencia: (barberoId: number, date_from: string, date_to: string) =>
    pedir<CitaAfectada[]>(`/barbers/${barberoId}/absences/preview?date_from=${date_from}&date_to=${date_to}`),
  ausencias: () => pedir<Ausencia[]>("/absences"),
  crearAusencia: (barberoId: number, date_from: string, date_to: string, motivo: string) =>
    pedir<{ id: number; reasignadas: number; canceladas: number }>(`/barbers/${barberoId}/absences`, "POST", { date_from, date_to, motivo }),
  borrarAusencia: (id: number) => pedir<Ok>(`/absences/${id}`, "DELETE"),

  // citas
  citas: () => pedir<Cita[]>("/appointments"),
  agendar: (datos: CitaIn) => pedir<{ id: number }>("/appointments", "POST", datos),
  cancelarCita: (id: number) => pedir<Ok>(`/appointments/${id}/cancel`, "POST"),
  cerrarCita: (id: number, status: "completada" | "inasistencia") =>
    pedir<Ok>(`/appointments/${id}/status`, "PATCH", { status }),
  recordarCita: (id: number) => pedir<Ok>(`/appointments/${id}/remind`, "POST"),

  // administración
  estadisticas: () => pedir<Estadisticas>("/admin/stats"),
  modeloInasistencia: () => pedir<ModeloInasistencia>("/admin/ml"),
  ajustes: () => pedir<Ajustes>("/admin/settings"),
  clientes: () => pedir<ClienteBasico[]>("/clients"),
  recuperar: (email: string) => pedir<Ok>("/password/forgot", "POST", { email }),
  restablecer: (token: string, password: string) => pedir<Ok>("/password/reset", "POST", { token, password }),

  // asistente
  chat: (message: string, book?: ReservaChat) => pedir<RespuestaChat>("/chat", "POST", { message, book }),
  historialChat: () => pedir<HistorialChat>("/chat/history"),
  borrarHistorialChat: () => pedir<Ok>("/chat/history", "DELETE"),
  opinarChat: (datos: { useful: boolean; message_id?: number; question?: string; answer?: string }) =>
    pedir<{ ok: boolean; message: string }>("/chat/feedback", "POST", datos),
  reindexar: () => pedir<{ embeddings_ok: boolean }>("/admin/reindex", "POST"),
  voz: (audio: Blob, conVoz = true) => enviarVoz(audio, conVoz),
  pqrs: () => pedir<Pqrs[]>("/admin/pqrs"),
  gestionarPqrs: (id: number, estado: EstadoPqrs, respuesta?: string) =>
    pedir<Ok>(`/admin/pqrs/${id}`, "PATCH", { estado, respuesta: respuesta || null }),

  // aprendizaje del asistente (administrador)
  preguntasPendientes: (estado = "pendiente") => pedir<PreguntaPendiente[]>(`/assistant/questions?status=${estado}`),
  ensenar: (id: number, datos: { answer: string; access_level: Visibilidad; question?: string }) =>
    pedir<DocumentoConocimiento>(`/assistant/questions/${id}/answer`, "POST", datos),
  descartarPregunta: (id: number) => pedir<Ok>(`/assistant/questions/${id}/discard`, "POST"),
  documentos: () => pedir<DocumentoConocimiento[]>("/assistant/knowledge"),
  crearDocumento: (datos: DocumentoIn) => pedir<DocumentoConocimiento>("/assistant/knowledge", "POST", datos),
  editarDocumento: (id: number, datos: DocumentoIn) => pedir<DocumentoConocimiento>(`/assistant/knowledge/${id}`, "PUT", datos),
  eliminarDocumento: (id: number) => pedir<Ok>(`/assistant/knowledge/${id}`, "DELETE"),
};
