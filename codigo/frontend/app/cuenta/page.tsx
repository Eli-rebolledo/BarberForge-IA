"use client";

import { useState, type FormEvent } from "react";
import { useAviso } from "@/components/Aviso";
import { FotoEditor } from "@/components/FotoEditor";
import { Panel } from "@/components/Panel";
import { useSesion } from "@/components/Sesion";
import { api, type CuentaIn, type Usuario } from "@/lib/api";

function FormularioCuenta({ usuario }: { usuario: Usuario }) {
  const { actualizar } = useSesion();
  const avisar = useAviso();
  const [datos, setDatos] = useState({
    full_name: usuario.full_name, email: usuario.email, style_pref: usuario.style_pref ?? "",
    current_password: "", new_password: "",
  });
  const [guardando, setGuardando] = useState(false);
  const campo = (k: keyof typeof datos, v: string) => setDatos((d) => ({ ...d, [k]: v }));

  async function guardar(e: FormEvent) {
    e.preventDefault();
    const cuerpo: CuentaIn = { full_name: datos.full_name, email: datos.email };
    if (usuario.role === "cliente") cuerpo.style_pref = datos.style_pref;
    if (datos.new_password) {
      cuerpo.current_password = datos.current_password;
      cuerpo.new_password = datos.new_password;
    }
    setGuardando(true);
    try {
      const r = await api.actualizarCuenta(cuerpo);
      actualizar(r.user);
      setDatos((d) => ({ ...d, current_password: "", new_password: "" }));
      avisar("Cuenta actualizada");
    } catch (x) {
      avisar((x as Error).message, "err");
    }
    setGuardando(false);
  }

  return (
    <form className="cuenta" onSubmit={guardar}>
      <section className="cd">
        <h3>Perfil</h3>
        {usuario.role === "barbero" && (
          <FotoEditor barberoId={usuario.id} nombre={usuario.full_name} foto={usuario.photo_url}
            onCambio={(url) => actualizar({ ...usuario, photo_url: url })} />
        )}
        <div className="fgrid">
          <label className="fl">Nombre<input required value={datos.full_name} onChange={(e) => campo("full_name", e.target.value)} /></label>
          <label className="fl">Correo<input type="email" required value={datos.email} onChange={(e) => campo("email", e.target.value)} /></label>
          {usuario.role === "cliente" && (
            <label className="fl full">Preferencias de estilo
              <input value={datos.style_pref} placeholder="Ej.: fade bajo, barba perfilada" onChange={(e) => campo("style_pref", e.target.value)} />
            </label>
          )}
        </div>
      </section>
      <section className="cd">
        <h3>Seguridad</h3>
        <p className="mute">Para cambiar la contraseña escribe la actual y la nueva (mínimo 8 caracteres).</p>
        <div className="fgrid">
          <label className="fl">Contraseña actual
            <input type="password" autoComplete="current-password" value={datos.current_password} onChange={(e) => campo("current_password", e.target.value)} />
          </label>
          <label className="fl">Nueva contraseña
            <input type="password" minLength={8} autoComplete="new-password" value={datos.new_password} onChange={(e) => campo("new_password", e.target.value)} />
          </label>
        </div>
      </section>
      <div><button className="btn" disabled={guardando}>Guardar cambios</button></div>
    </form>
  );
}

export default function Cuenta() {
  return (
    <Panel roles={["cliente", "barbero", "administrador"]} titulo="Mi cuenta">
      {(usuario) => <FormularioCuenta usuario={usuario} />}
    </Panel>
  );
}
