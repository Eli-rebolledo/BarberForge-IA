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

export interface DiaCalendario { date: string; total: number; ocupadas: number }
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

  // citas
  citas: () => pedir<Cita[]>("/appointments"),
  agendar: (datos: CitaIn) => pedir<{ id: number }>("/appointments", "POST", datos),
  cancelarCita: (id: number) => pedir<Ok>(`/appointments/${id}/cancel`, "POST"),
  cerrarCita: (id: number, status: "completada" | "inasistencia") =>
    pedir<Ok>(`/appointments/${id}/status`, "PATCH", { status }),
  recordarCita: (id: number) => pedir<Ok>(`/appointments/${id}/remind`, "POST"),

  // administración
  estadisticas: () => pedir<Estadisticas>("/admin/stats"),
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
