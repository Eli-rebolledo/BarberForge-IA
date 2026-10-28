"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAviso } from "./Aviso";
import { abrirChat } from "./ChatFlotante";
import { Logo, useNombreBarberia } from "./Barberia";
import { Icono } from "./Icono";
import { useSesion } from "./Sesion";
import { useTema } from "./Tema";
import { inicioPanel, ROLES } from "@/lib/formato";
import { Avatar } from "./Avatar";

export function Navbar() {
  const { usuario, salir } = useSesion();
  const { oscuro, alternar } = useTema();
  const avisar = useAviso();
  const router = useRouter();
  const ruta = usePathname();
  const [abierto, setAbierto] = useState(false);
  const nombre = useNombreBarberia();
  const personal = !!usuario && usuario.role !== "cliente"; // administrador y barberos solo trabajan en su panel
  useEffect(() => setAbierto(false), [ruta]);

  function cerrarSesion() {
    salir();
    router.push("/");
    avisar("Sesión cerrada");
  }

  return (
    <div className="topwrap">
      <header className="top">
        <Link href={usuario ? inicioPanel(usuario.role) : "/"} className="logo"><Logo /><span className="bn"><b className="gt" title={nombre}>{nombre}</b><small>Agenda en línea</small></span></Link>
        <nav className={`main ${abierto ? "open" : ""}`}>
          {!personal && (
            <>
              <Link href="/" className={ruta === "/" ? "on" : ""}>Inicio</Link>
              <Link href="/barberia" className={ruta === "/barberia" ? "on" : ""}>Barbería</Link>
              <Link href="/#proceso">Cómo funciona</Link>
              <button type="button" onClick={abrirChat}>Asistente</button>
            </>
          )}
          <div className="navuser">
            {usuario ? (
              <>
                <Link className="btn glass sm" href={inicioPanel(usuario.role)}>Mi panel</Link>
                <button className="btn glass sm" onClick={cerrarSesion}>Salir</button>
              </>
            ) : (
              <>
                <Link className="btn glass sm" href="/login">Ingresar</Link>
                <Link className="btn white sm" href="/registro">Registrarse</Link>
              </>
            )}
          </div>
        </nav>
        <div className="hd">
          <button type="button" className="ico-btn glass" onClick={alternar} aria-label={oscuro ? "Modo claro" : "Modo oscuro"} title={oscuro ? "Modo claro" : "Modo oscuro"}>
            <Icono n={oscuro ? "sol" : "luna"} />
          </button>
          {usuario && (
            <Link href="/cuenta" className="who" title="Mi cuenta">
              <Avatar nombre={usuario.full_name} foto={usuario.photo_url} className="av" apagado />
              <span className="wn"><b>{usuario.full_name}</b><small>{ROLES[usuario.role]}</small></span>
            </Link>
          )}
          <button type="button" className="ico-btn glass burger" aria-label="Menú" aria-expanded={abierto} onClick={() => setAbierto((a) => !a)}>
            <Icono n={abierto ? "x" : "menu"} />
          </button>
        </div>
      </header>
    </div>
  );
}
