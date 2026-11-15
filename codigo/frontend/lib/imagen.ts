// Prepara la foto del barbero en el navegador: la recorta cuadrada y la reduce antes de subirla,
// así una foto de 5 MB del celular queda en unos 40 KB.
const LADO = 480;

export async function fotoCuadrada(archivo: File): Promise<string> {
  if (!/^image\/(jpeg|png|webp|heic|heif)$/.test(archivo.type) && !archivo.type.startsWith("image/")) {
    throw new Error("Elige una imagen (JPG, PNG o WebP).");
  }
  if (archivo.size > 15 * 1024 * 1024) throw new Error("La imagen es muy pesada (máximo 15 MB).");
  const url = URL.createObjectURL(archivo);
  try {
    const img = await new Promise<HTMLImageElement>((ok, mal) => {
      const i = new Image();
      i.onload = () => ok(i);
      i.onerror = () => mal(new Error("No se pudo abrir la imagen. Prueba con una foto JPG o PNG."));
      i.src = url;
    });
    const lado = Math.min(img.naturalWidth, img.naturalHeight);
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = Math.min(LADO, lado);
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Tu navegador no pudo procesar la imagen.");
    // Recorte centrado (un poco hacia arriba, donde suele estar la cara).
    const sx = (img.naturalWidth - lado) / 2;
    const sy = Math.max(0, (img.naturalHeight - lado) * 0.3);
    ctx.drawImage(img, sx, sy, lado, lado, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.85);
  } finally {
    URL.revokeObjectURL(url);
  }
}

/** Logo de la barbería: conserva la proporción y la transparencia (PNG), máximo 512 px por lado. */
export async function logoAjustado(archivo: File): Promise<string> {
  if (!archivo.type.startsWith("image/") || archivo.type === "image/svg+xml") {
    throw new Error("Elige una imagen PNG, JPG o WebP (no SVG).");
  }
  if (archivo.size > 15 * 1024 * 1024) throw new Error("La imagen es muy pesada (máximo 15 MB).");
  const url = URL.createObjectURL(archivo);
  try {
    const img = await new Promise<HTMLImageElement>((ok, mal) => {
      const i = new Image();
      i.onload = () => ok(i);
      i.onerror = () => mal(new Error("No se pudo abrir la imagen."));
      i.src = url;
    });
    const escala = Math.min(1, 512 / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(img.naturalWidth * escala));
    canvas.height = Math.max(1, Math.round(img.naturalHeight * escala));
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Tu navegador no pudo procesar la imagen.");
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  } finally {
    URL.revokeObjectURL(url);
  }
}
