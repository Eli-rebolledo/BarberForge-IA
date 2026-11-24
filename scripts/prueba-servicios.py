"""Prueba automatizada de servicios: disponibilidad y latencia de cada servicio, cada uno con su propio umbral.

Llama varias veces a cada servicio de la plataforma ya levantada (Docker Compose o Kubernetes) y guarda:
  - resultados/prueba-servicios-<fecha>.csv          una fila por petición
  - resultados/prueba-servicios-<fecha>-resumen.csv  una fila por servicio: disponibilidad, p50, p95 y si cumple el SLO

Uso (con la plataforma arriba, desde la raíz del repositorio):
    pip install httpx
    python scripts/prueba-servicios.py                       # 20 veces cada servicio rápido, 5 el asistente y la voz
    python scripts/prueba-servicios.py --veces 50 --veces-ia 10
    python scripts/prueba-servicios.py --solo voz            # un servicio: web, api, login, catalogo, disponibilidad, asistente, voz

No crea citas ni PQRS: solo consulta. Las preguntas al asistente son de información (precios y horarios).
"""
import argparse
import csv
import statistics
import time
from pathlib import Path

import httpx

# Umbral de latencia (p95) por servicio: la API normal en milisegundos, el asistente con IA en segundos.
SLO_P95 = {"web": 0.5, "api": 0.5, "login": 0.5, "catalogo": 0.5, "disponibilidad": 0.5, "asistente": 60.0, "voz": 60.0}
SLO_DISPONIBILIDAD = 0.99
PREGUNTAS = ["¿Cuánto cuesta un corte?", "¿A qué hora abren los sábados?", "¿Atienden los festivos?"]


def percentil(valores: list[float], p: float) -> float:
    if not valores:
        return float("nan")
    ordenados = sorted(valores)
    k = (len(ordenados) - 1) * p
    i = int(k)
    return ordenados[i] + (ordenados[min(i + 1, len(ordenados) - 1)] - ordenados[i]) * (k - i)


def medir(cliente: httpx.Client, servicio: str, metodo: str, url: str, **kw) -> dict:
    inicio = time.perf_counter()
    try:
        r = cliente.request(metodo, url, **kw)
        codigo, ok = r.status_code, r.status_code < 500
    except httpx.HTTPError as e:  # caído o sin respuesta: cuenta como no disponible
        codigo, ok = type(e).__name__, False
    return {"servicio": servicio, "url": url, "codigo": codigo, "ok": ok,
            "segundos": round(time.perf_counter() - inicio, 4)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8080", help="dirección de la web (nginx reenvía /api y /voz)")
    ap.add_argument("--correo", default="carlos@demo.co", help="cuenta para probar el login (barbero de ejemplo)")
    ap.add_argument("--clave", default="Demo12345")
    ap.add_argument("--veces", type=int, default=20, help="repeticiones de los servicios rápidos")
    ap.add_argument("--veces-ia", type=int, default=5, help="repeticiones del asistente y de la voz")
    ap.add_argument("--solo", choices=sorted(SLO_P95), help="probar un solo servicio")
    a = ap.parse_args()
    u = a.url.rstrip("/")

    filas: list[dict] = []
    with httpx.Client(timeout=300) as c:
        barbero_id = None
        try:
            barberos = c.get(f"{u}/api/barbers").json()
            barbero_id = barberos[0]["id"] if barberos else None
        except (httpx.HTTPError, ValueError, KeyError, IndexError):
            pass
        pruebas = {
            "web": lambda: medir(c, "web", "GET", f"{u}/"),
            "api": lambda: medir(c, "api", "GET", f"{u}/api/health"),
            "login": lambda: medir(c, "login", "POST", f"{u}/api/login", json={"email": a.correo, "password": a.clave}),
            "catalogo": lambda: medir(c, "catalogo", "GET", f"{u}/api/services"),
            "disponibilidad": lambda: medir(c, "disponibilidad", "GET", f"{u}/api/availability",
                                            params={"barber_id": barbero_id or 1, "minutes": 30}),
        }
        for nombre, prueba in pruebas.items():
            if a.solo in (None, nombre):
                print(f"· {nombre} ({a.veces} veces)…", flush=True)
                filas += [prueba() for _ in range(a.veces)]
        for nombre, metodo, ruta, cuerpo in (("asistente", "POST", "/api/chat", "message"),
                                             ("voz", "POST", "/voz/texto", "texto")):
            if a.solo in (None, nombre):
                print(f"· {nombre} ({a.veces_ia} veces, puede tardar)…", flush=True)
                filas += [medir(c, nombre, metodo, f"{u}{ruta}", json={cuerpo: PREGUNTAS[i % len(PREGUNTAS)]})
                          for i in range(a.veces_ia)]

    resumen = []
    for servicio in dict.fromkeys(f["servicio"] for f in filas):
        de_este = [f for f in filas if f["servicio"] == servicio]
        tiempos = [f["segundos"] for f in de_este if f["ok"]]
        disponibilidad = sum(f["ok"] for f in de_este) / len(de_este)
        p95 = percentil(tiempos, 0.95)
        resumen.append({
            "servicio": servicio, "peticiones": len(de_este), "disponibilidad": round(disponibilidad, 4),
            "p50_s": round(percentil(tiempos, 0.50), 3), "p95_s": round(p95, 3),
            "promedio_s": round(statistics.mean(tiempos), 3) if tiempos else None,
            "slo_p95_s": SLO_P95[servicio],
            "cumple": disponibilidad >= SLO_DISPONIBILIDAD and p95 <= SLO_P95[servicio],
        })

    carpeta = Path("resultados")
    carpeta.mkdir(exist_ok=True)
    marca = time.strftime("%Y%m%d-%H%M")
    for nombre, datos in ((f"prueba-servicios-{marca}.csv", filas), (f"prueba-servicios-{marca}-resumen.csv", resumen)):
        with (carpeta / nombre).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(datos[0]))
            w.writeheader()
            w.writerows(datos)

    print(f"\n{'servicio':<15}{'disp.':>8}{'p50':>9}{'p95':>9}{'SLO p95':>10}  cumple")
    for r in resumen:
        print(f"{r['servicio']:<15}{r['disponibilidad']:>8.1%}{r['p50_s']:>8.2f}s{r['p95_s']:>8.2f}s"
              f"{r['slo_p95_s']:>9.1f}s  {'sí' if r['cumple'] else 'NO'}")
    print(f"\nGuardado en {carpeta.resolve()}")


if __name__ == "__main__":
    main()
