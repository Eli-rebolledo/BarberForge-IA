import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AvisoProvider } from "@/components/Aviso";
import { BarberiaProvider } from "@/components/Barberia";
import { ChatFlotante } from "@/components/ChatFlotante";
import { Footer } from "@/components/Footer";
import { Navbar } from "@/components/Navbar";
import { SesionProvider } from "@/components/Sesion";
import { SCRIPT_TEMA, TemaProvider } from "@/components/Tema";
import "./globals.css";

export const metadata: Metadata = {
  title: "BarberForge AI | Agenda tu cita en la barbería",
  description: "Agenda tu cita en línea, elige tus servicios y pregúntale al asistente por precios y horarios.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Alfa+Slab+One&display=swap" />
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
      </head>
      <body>
        <TemaProvider>
          <SesionProvider>
            <BarberiaProvider>
            <AvisoProvider>
              <Navbar />
              <div className="page">{children}</div>
              <Footer />
              <ChatFlotante />
            </AvisoProvider>
            </BarberiaProvider>
          </SesionProvider>
        </TemaProvider>
      </body>
    </html>
  );
}
