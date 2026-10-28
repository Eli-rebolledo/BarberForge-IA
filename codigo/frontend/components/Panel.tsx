"use client";

import { useEffect, useRef, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { Rol, Usuario } from "@/lib/api";
import { primerNombre, ROLES } from "@/lib/formato";
import { Vacio } from "./Aviso";
import { useNombreBarberia } from "./Barberia";
import { Icono } from "./Icono";
import { useSesion } from "./Sesion";

type Pestana = [href: string, nombre: string, icono: string];

const PESTANAS: Record<Rol, Pestana[]> = {
  cliente: [["/agendar", "Agendar cita", "calendario"], ["/citas", "Mis citas", "reloj"], ["/asistente", "Asistente", "chat"]],
  barbero: [["/citas", "Mi agenda", "calendario"], ["/citas/nueva", "Nueva cita", "mas"], ["/asistente", "Asistente", "chat"]],
  administrador: [
    ["/admin", "Panel", "grafico"], ["/citas", "Citas", "calendario"], ["/admin/barberos", "Barberos", "usuarios"],
    ["/admin/servicios", "Servicios", "tijera"], ["/admin/disponibilidad", "Calendario", "reloj"],
    ["/admin/asistente", "Asistente IA", "chispa"],
  ],
};
const DERECHA: Pestana[] = [["/ajustes", "Ajustes", "ajustes"], ["/cuenta", "Mi cuenta", "usuario"]];

interface Props { roles: Rol[]; titulo?: string; accion?: ReactNode; children: (usuario: Usuario) => ReactNode }

/** Marco de las páginas privadas: exige sesión y rol, y muestra las pestañas del rol. */
export function Panel({ roles, titulo, accion, children }: Props) {
  const { usuario, cargando } = useSesion();
  const router = useRouter();
  const ruta = usePathname();
  const nombreBarberia = useNombreBarberia();

  // Si al entrar no hay sesión, se pide iniciar sesión. Si la sesión se cierra aquí mismo,
  // la barra de navegación ya lleva al inicio y no se redirige al login.
  const tuvoSesion = useRef(false);
  if (usuario) tuvoSesion.current = true;
  useEffect(() => {
    if (!cargando && !usuario && !tuvoSesion.current) router.replace(`/login?next=${encodeURIComponent(ruta)}`);
  }, [cargando, usuario, ruta, router]);

  if (cargando || !usuario) return <main className="panel"><Vacio>Cargando…</Vacio></main>;

  const tab = ([href, nombre, ico]: Pestana) => (
    <Link key={href} href={href} className={ruta === href ? "on" : ""}><Icono n={ico} size={16} />{nombre}</Link>
  );
  return (
    <main className="panel">
      <div className="tbar">
        <nav className="tabs">{PESTANAS[usuario.role].map(tab)}</nav>
        <nav className="tabs">{DERECHA.map(tab)}</nav>
      </div>
      <div className="ph">
        <div>
          <h1>{titulo ?? `Hola, ${primerNombre(usuario.full_name)}`}</h1>
          <p className="mute">{ROLES[usuario.role]} · {nombreBarberia}</p>
        </div>
        {accion}
      </div>
      {roles.includes(usuario.role) ? children(usuario) : <Vacio>Esta sección no está disponible para tu rol.</Vacio>}
    </main>
  );
}
