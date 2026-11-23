import type { NextConfig } from "next";

// En producción se exporta como sitio estático (carpeta out/) que sirve nginx, el cual
// también reenvía /api al backend. En desarrollo, Next reenvía /api a la API local.
const desarrollo = process.env.NODE_ENV !== "production";
const API_URL = process.env.API_URL ?? "http://localhost:8000";
const VOZ_URL = process.env.VOZ_URL ?? "http://localhost:8001"; // feature 012: servicio de voz

const config: NextConfig = desarrollo
  ? {
      async rewrites() {
        return [
          { source: "/api/:ruta*", destination: `${API_URL}/api/:ruta*` },
          { source: "/voz/:ruta*", destination: `${VOZ_URL}/voz/:ruta*` },
        ];
      },
    }
  : { output: "export", images: { unoptimized: true } };

export default config;
