import { COLORES_AVATAR, iniciales } from "@/lib/formato";

interface Props {
  nombre: string;
  foto?: string | null;
  indice?: number;
  className?: string;
  apagado?: boolean;
}

/** Foto del barbero o, si no tiene, sus iniciales sobre un color. */
export function Avatar({ nombre, foto, indice = 0, className = "av", apagado }: Props) {
  if (foto) {
    return <img className={`${className} foto`} src={foto} alt={`Foto de ${nombre}`} loading="lazy" />;
  }
  return (
    <span className={className} style={apagado ? undefined : { background: COLORES_AVATAR[indice % COLORES_AVATAR.length], color: "#fff" }}>
      {iniciales(nombre)}
    </span>
  );
}
