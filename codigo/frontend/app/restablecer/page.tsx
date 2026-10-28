"use client";

import { Suspense, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAviso } from "@/components/Aviso";
import { Logo } from "@/components/Barberia";
import { api } from "@/lib/api";

function Formulario() {
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();
  const avisar = useAviso();
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError("");
    try {
      await api.restablecer(token, clave);
      avisar("Contraseña actualizada. Ya puedes ingresar.");
      router.replace("/login");
    } catch (x) { setError((x as Error).message); setEnviando(false); }
  }

  return (
    <main className="auth">
      <div className="card authcard">
        <div className="authlogo"><Logo size={46} /></div>
        <h2>Nueva contraseña</h2>
        {!token ? <div className="note">El enlace no es válido. <Link href="/recuperar">Pide uno nuevo</Link>.</div> : (
          <form onSubmit={enviar}>
            <label>Nueva contraseña (mínimo 8)
              <input type="password" minLength={8} required autoComplete="new-password" value={clave} onChange={(e) => setClave(e.target.value)} />
            </label>
            <div className="err">{error}</div>
            <button className="btn full" disabled={enviando}>Guardar contraseña</button>
          </form>
        )}
      </div>
    </main>
  );
}

export default function Restablecer() {
  return <Suspense><Formulario /></Suspense>;
}
