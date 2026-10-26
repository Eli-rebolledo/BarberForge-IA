"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChatAsistente } from "@/components/ChatAsistente";
import { Icono } from "@/components/Icono";
import { useSesion } from "@/components/Sesion";
import { inicioPanel } from "@/lib/formato";

const FUNCIONES = [
  ["calendario", "Agenda en tiempo real", "Calendario con horarios reales: nunca se cruzan dos citas."],
  ["tijera", "Varios servicios, una cita", "Combina corte, barba y tratamiento y el sistema reserva el tiempo necesario."],
  ["correo", "Recordatorios automáticos", "El cliente recibe un correo antes de la cita. Nadie tiene que enviarlo a mano."],
  ["usuarios", "Citas en el local", "Si llegas y la barbería está ocupada, el barbero crea tu cita en segundos, sin registro."],
];

export default function Inicio() {
  const { usuario, cargando } = useSesion();
  const router = useRouter();
  const personal = !!usuario && usuario.role !== "cliente";
  useEffect(() => { if (usuario && personal) router.replace(inicioPanel(usuario.role)); }, [usuario, personal, router]);
  if (personal || cargando) return <main />; // el personal no ve la página pública
  return (
    <main>
      <section className="hero">
        <div className="hero-in">
          <div>
            <span className="badge"><Icono n="chispa" size={14} /> Barbería con agenda inteligente</span>
            <h1>Tu próximo corte, <span className="gt">sin llamadas ni esperas.</span></h1>
            <p className="lead">Elige tus servicios, tu barbero y la hora que te quede mejor. Si tienes dudas, el asistente responde al instante.</p>
            <div className="row">
              <Link className="btn white" href="/barberia">Ver servicios <Icono n="flecha" size={16} /></Link>
              {!usuario && <Link className="btn glass" href="/registro">Crear mi cuenta</Link>}
            </div>
            <div className="facts">
              <div><b>24/7</b>asistente disponible</div>
              <div><b>Auto</b>recordatorios por correo</div>
              <div><b>0</b>citas cruzadas</div>
            </div>
          </div>
          <ChatAsistente />
        </div>
      </section>

      <section className="sec" id="proceso">
        <div className="st"><h2>¿Cómo funciona?</h2><p>Tres pasos, por formulario o conversando con el asistente.</p></div>
        <div className="steps">
          <div className="step"><i>1</i><h3>Elige</h3><p>Uno o varios servicios y tu barbero favorito.</p></div>
          <div className="step"><i>2</i><h3>Agenda</h3><p>Toca un día del calendario y escoge la hora. La franja se bloquea al instante.</p></div>
          <div className="step"><i>3</i><h3>Confirma</h3><p>Te llega un recordatorio automático con un botón para confirmar.</p></div>
        </div>
      </section>

      <section className="sec alt">
        <div className="st"><h2>Todo en un solo lugar</h2><p>Para clientes, barberos y administradores.</p></div>
        <div className="grid feats">
          {FUNCIONES.map(([i, t, d]) => (
            <div key={t} className="feat"><span className="ic"><Icono n={i} size={22} /></span><h3>{t}</h3><p>{d}</p></div>
          ))}
        </div>
      </section>
    </main>
  );
}
