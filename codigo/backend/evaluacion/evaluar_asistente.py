"""Evalúa el asistente de BarberForge (POST /api/chat) con el Golden Dataset de 56 preguntas.

Es el mismo dataset y el mismo criterio de palabras clave que se usó con OpenWebUI (docs/evaluacion-rag/), pero
contra el asistente propio de la aplicación: así se comprueba que el RAG integrado responde igual de bien.

    python evaluacion/evaluar_asistente.py                          # API en http://localhost:8080
    python evaluacion/evaluar_asistente.py --limite 5               # prueba rápida
    python evaluacion/evaluar_asistente.py --correo ana@correo.co --clave ...   # como cliente registrado

Solo usa la biblioteca estándar. Escribe resultados_asistente_<fecha>.csv y un resumen en pantalla.
Las preguntas de agendar, cancelar o PQRS hacen acciones reales: córrelo contra un entorno de prueba.
"""
import argparse
import csv
import json
import re
import statistics
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
DATASET = RAIZ / "docs" / "evaluacion-rag" / "golden_dataset.csv"
UMBRAL_PALABRAS = 0.5   # pruebas «responder»: pasa si aparece al menos la mitad de las palabras clave
META = 0.70             # eficiencia mínima pedida por la actividad


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y sin separador de miles: «$25.000» → «$25000»."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"(?<=\d)[.,](?=\d{3}\b)", "", texto)


def contiene(texto_norm: str, palabra: str) -> bool:
    p = re.escape(normalizar(palabra.strip()))
    if len(palabra.strip()) <= 3:
        return re.search(rf"(?<![a-z0-9]){p}(?![a-z0-9])", texto_norm) is not None
    return re.search(rf"(?<![a-z0-9]){p}", texto_norm) is not None


def evaluar(respuesta: str, palabras: list[str], tipo: str) -> tuple[float, bool, list[str]]:
    texto = normalizar(respuesta)
    encontradas = [p for p in palabras if contiene(texto, p)]
    proporcion = len(encontradas) / len(palabras) if palabras else 0.0
    paso = bool(encontradas) if tipo == "negarse" else proporcion >= UMBRAL_PALABRAS
    return round(proporcion, 2), paso, encontradas


def post(url: str, cuerpo: dict, token: str | None, timeout: int) -> dict:
    cabeceras = {"Content-Type": "application/json"} | ({"Authorization": f"Bearer {token}"} if token else {})
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode(), headers=cabeceras)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://localhost:8080")
    p.add_argument("--dataset", default=str(DATASET))
    p.add_argument("--limite", type=int, default=0)
    p.add_argument("--correo", default="")
    p.add_argument("--clave", default="")
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args()
    base = args.url.rstrip("/")

    token = None
    if args.correo:
        token = post(f"{base}/api/login", {"email": args.correo, "password": args.clave}, None, 30)["token"]

    with open(args.dataset, encoding="utf-8") as f:
        pruebas = list(csv.DictReader(f))
    if args.limite:
        pruebas = pruebas[: args.limite]

    filas, latencias = [], []
    for i, prueba in enumerate(pruebas, 1):
        inicio = time.perf_counter()
        try:
            respuesta, error = post(f"{base}/api/chat", {"message": prueba["pregunta"]}, token, args.timeout)["reply"], ""
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
            respuesta, error = "", f"{type(e).__name__}: {e}"
        segundos = round(time.perf_counter() - inicio, 2)
        latencias.append(segundos)
        proporcion, paso, encontradas = evaluar(respuesta, prueba["palabras_clave"].split("|"), prueba["tipo"])
        filas.append({"id": prueba["id"], "categoria": prueba["categoria"], "tipo": prueba["tipo"],
                      "pregunta": prueba["pregunta"], "respuesta": respuesta, "palabras_encontradas": "|".join(encontradas),
                      "proporcion": proporcion, "exito": paso, "latencia_s": segundos, "error": error})
        print(f"[{i:>2}/{len(pruebas)}] {prueba['id']} {'OK ' if paso else 'NO '} {segundos:>6.1f} s  {prueba['pregunta'][:60]}")

    salida = Path(f"resultados_asistente_{datetime.now():%Y%m%d_%H%M}.csv")
    with salida.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    exitos = sum(f["exito"] for f in filas)
    tasa = exitos / len(filas)
    print(f"\nÉxito por palabras clave: {tasa:.1%} ({exitos} de {len(filas)}) · meta {META:.0%}: "
          f"{'cumple' if tasa >= META else 'no cumple'}")
    print(f"Latencia: media {statistics.mean(latencias):.1f} s · p50 {statistics.median(latencias):.1f} s · "
          f"p95 {sorted(latencias)[max(0, int(len(latencias) * 0.95) - 1)]:.1f} s · "
          f"errores de API: {sum(bool(f['error']) for f in filas)}")
    print(f"Detalle: {salida}")


if __name__ == "__main__":
    main()
