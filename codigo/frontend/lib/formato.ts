// Formatos y etiquetas en español para la interfaz.
import type { EstadoCita, Franja, Rol, TipoServicio } from "./api";

export const cop = (n: number) => "$" + Number(n).toLocaleString("es-CO");

export const fechaLarga = (d: string) =>
  new Date(d + "T12:00:00").toLocaleDateString("es-CO", { weekday: "long", day: "numeric", month: "long" });

export const fechaCorta = (d: string) =>
  new Date(d + "T12:00:00").toLocaleDateString("es-CO", { weekday: "short", day: "numeric", month: "short" }).replace(/\./g, "");

/** "14:30" -> "2:30 p. m." */
export const hora12 = (t: string) => {
  const [h, m] = t.split(":").map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2, "0")} ${h < 12 ? "a. m." : "p. m."}`;
};

export const iniciales = (nombre: string) =>
  nombre.split(" ").filter(Boolean).slice(0, 2).map((x) => x[0]).join("").toUpperCase();

export const primerNombre = (nombre: string) => nombre.split(" ")[0];

const dos = (n: number) => String(n).padStart(2, "0");
export const isoFecha = (y: number, m: number, d: number) => `${y}-${dos(m + 1)}-${dos(d)}`;

// Fecha local AAAA-MM-DD (toISOString usaría UTC y en la noche de Colombia daría el día siguiente).
export const hoyISO = () => {
  const d = new Date();
  return isoFecha(d.getFullYear(), d.getMonth(), d.getDate());
};

export const textoAlternativas = (alts: Franja[]) =>
  alts.map((a) => `${a.date.slice(5)} ${hora12(a.time)}`).join(", ");

export const minutosTexto = (m: number) => (m >= 60 ? `${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60} min` : ""}` : `${m} min`);

export const ESTADOS: Record<EstadoCita, string> = {
  pendiente: "Pendiente",
  confirmada: "Confirmada",
  completada: "Completada",
  inasistencia: "No asistió",
  cancelada_cliente: "Cancelada por el cliente",
  cancelada_sin_confirmar: "Cancelada: sin confirmar",
  cancelada_admin: "Cancelada por la barbería",
};

/** Color de cada estado (clases .pill.t-…). */
export const TONO_ESTADO: Record<EstadoCita, string> = {
  pendiente: "amber", confirmada: "green", completada: "blue", inasistencia: "gray",
  cancelada_cliente: "red", cancelada_sin_confirmar: "red", cancelada_admin: "red",
};

export const TIPOS: TipoServicio[] = ["corte", "barba", "combo", "tratamiento"];
export const NOMBRE_TIPO: Record<TipoServicio, string> = {
  corte: "Corte", barba: "Barba", combo: "Combo", tratamiento: "Tratamiento",
};
export const ICONO_TIPO: Record<TipoServicio, string> = {
  corte: "tijera", barba: "navaja", combo: "poste", tratamiento: "gota",
};

export const ROLES: Record<Rol, string> = {
  cliente: "Cliente", barbero: "Barbero", administrador: "Administrador",
};

export const COLORES_AVATAR = [
  "linear-gradient(135deg,#1c1f29,#3b4256)",
  "linear-gradient(135deg,#9f1f27,#cf4249)",
  "linear-gradient(135deg,#2e5489,#5b82bd)",
  "linear-gradient(135deg,#2f6b4a,#4f9a73)",
];

// Página de inicio del panel según el rol.
export const inicioPanel = (rol: Rol) => (rol === "cliente" ? "/agendar" : rol === "administrador" ? "/admin" : "/citas");

/** Días de la semana en el orden del servidor: 0 = lunes … 6 = domingo. */
export const DIAS_SEMANA = [
  { n: 0, letra: "L", nombre: "Lunes" }, { n: 1, letra: "M", nombre: "Martes" },
  { n: 2, letra: "X", nombre: "Miércoles" }, { n: 3, letra: "J", nombre: "Jueves" },
  { n: 4, letra: "V", nombre: "Viernes" }, { n: 5, letra: "S", nombre: "Sábado" },
  { n: 6, letra: "D", nombre: "Domingo" },
];

export const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
