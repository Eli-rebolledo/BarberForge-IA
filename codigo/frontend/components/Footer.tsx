"use client";

import Link from "next/link";
import { useSesion } from "./Sesion";
import { Logo, useBarberia, useNombreBarberia } from "./Barberia";
import { Icono } from "./Icono";

export function Footer() {
  const { usuario } = useSesion();
  const nombre = useNombreBarberia();
  const { marca } = useBarberia();
  if (usuario && usuario.role !== "cliente") {
    return (
      <footer className="foot foot-min">
        <div className="foot-bar"><span>© 2026 {nombre}. Todos los derechos reservados.</span></div>
      </footer>
    );
  }
  return (
    <footer className="foot">
      <div className="foot-in">
        <div className="fcol brand">
          <Link href="/" className="logo"><Logo /><span className="bn"><b>{nombre}</b></span></Link>
          <p>Agenda en línea, recordatorios automáticos y un asistente que responde a cualquier hora. Pensado para barberías que quieren verse y trabajar mejor.</p>
        </div>
        <div className="fcol">
          <h4>Plataforma</h4>
          <Link href="/">Inicio</Link>
          <Link href="/barberia">Servicios y barberos</Link>
          <Link href="/#proceso">Cómo funciona</Link>
          <Link href="/agendar">Agendar cita</Link>
        </div>
        <div className="fcol">
          <h4>Mi cuenta</h4>
          <Link href="/login">Ingresar</Link>
          <Link href="/registro">Crear cuenta</Link>
          <Link href="/recuperar">Recuperar contraseña</Link>
          <Link href="/ajustes">Ajustes</Link>
        </div>
        <div className="fcol">
          <h4>Contacto</h4>
          <span><Icono n="pin" size={15} /> {marca?.direccion ?? "Popayán, Cauca"}</span>
          <span><Icono n="reloj" size={15} /> {marca?.horario ?? "Lun a sáb · 9:00 a. m. – 5:00 p. m."}</span>
          <span><Icono n="escudo" size={15} /> Tus datos se tratan según la Ley 1581 de 2012. Solo pedimos nombre y correo.</span>
        </div>
      </div>
      <div className="foot-bar">
        <span>© 2026 {nombre}. Todos los derechos reservados.</span>
      </div>
    </footer>
  );
}
