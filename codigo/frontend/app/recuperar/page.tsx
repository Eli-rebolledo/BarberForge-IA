"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Logo } from "@/components/Barberia";
import { Icono } from "@/components/Icono";
import { api } from "@/lib/api";

export default function Recuperar() {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError("");
    try { await api.recuperar(email); setEnviado(true); } catch (x) { setError((x as Error).message); }
    setEnviando(false);
  }

  return (
    <main className="auth">
      <div className="card authcard">
        <div className="authlogo"><Logo size={46} /></div>
        <h2>Recuperar contraseña</h2>
        {enviado ? (
          <div className="note ok"><Icono n="correo" size={18} /> Si ese correo tiene cuenta, te enviamos un enlace para crear una contraseña nueva. Vale 30 minutos.</div>
        ) : (
          <form onSubmit={enviar}>
            <p className="mute">Escribe el correo de tu cuenta (cliente, barbero o administrador) y te enviaremos un enlace.</p>
            <label>Correo<input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
            <div className="err">{error}</div>
            <button className="btn full" disabled={enviando}>Enviar enlace</button>
          </form>
        )}
        <div className="altlink"><Link href="/login">Volver a ingresar</Link></div>
      </div>
    </main>
  );
}
