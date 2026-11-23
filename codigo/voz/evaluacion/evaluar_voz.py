"""Evaluación del asistente de voz con un Golden Dataset de audios (feature 012).

Uso (con la plataforma levantada y el perfil «voz»):
    python evaluacion/evaluar_voz.py --url http://localhost:8080 --csv evaluacion/golden_voz.csv
    python evaluacion/evaluar_voz.py --solo-texto      # sin audios: prueba la intención con el texto esperado
    python evaluacion/evaluar_voz.py --audios sinteticos   # con las 30 voces sintéticas

Mide por cada audio: WER (error por palabra de la transcripción), si acertó la intención, si la respuesta contiene
las palabras clave y la latencia de cada etapa. Escribe resultados_voz_<fecha>.csv y un resumen en pantalla.
Solo usa la biblioteca estándar y httpx."""
import argparse
import csv
import json
import os
import statistics
import sys
import time
import unicodedata
from datetime import datetime

import httpx


def normalizar(t: str) -> list[str]:
    t = "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")
    return "".join(c if c.isalnum() or c.isspace() else " " for c in t).split()


def wer(referencia: str, hipotesis: str) -> float:
    r, h = normalizar(referencia), normalizar(hipotesis)
    if not r:
        return 0.0 if not h else 1.0
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        previo, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            actual = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, previo + (r[i - 1] != h[j - 1]))
            previo = actual
    return d[len(h)] / len(r)


def contiene(respuesta: str, claves: str) -> bool:
    palabras = [k.strip() for k in claves.split("|") if k.strip()]
    texto = " ".join(normalizar(respuesta))
    return not palabras or any(" ".join(normalizar(p)) in texto for p in palabras)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8080", help="dirección de la web (nginx reenvía /voz)")
    ap.add_argument("--csv", default=os.path.join(os.path.dirname(__file__), "golden_voz.csv"))
    ap.add_argument("--token", default=os.getenv("BF_TOKEN"), help="JWT de un cliente de prueba (para agendar)")
    ap.add_argument("--solo-texto", action="store_true")
    ap.add_argument("--audios", default="audios",
                    help="carpeta de los audios, relativa al CSV: audios (voces del equipo) o sinteticos")
    a = ap.parse_args()
    cab = {"Authorization": f"Bearer {a.token}"} if a.token else {}
    base = os.path.dirname(a.csv)
    filas = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    salida = []
    for f in filas:
        t0 = time.perf_counter()
        try:
            if a.solo_texto or not f.get("archivo"):
                r = httpx.post(f"{a.url}/voz/texto", json={"texto": f["texto_esperado"]}, headers=cab, timeout=300)
            else:
                with open(os.path.join(base, a.audios, f["archivo"]), "rb") as audio:
                    r = httpx.post(f"{a.url}/voz/", files={"audio": (f["archivo"], audio)},
                                   data={"responder_con_voz": "false"}, headers=cab, timeout=300)
            d = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            ok_http = r.status_code == 200
        except httpx.HTTPError as e:
            d, ok_http = {"detail": str(e)}, False
        trans = d.get("transcripcion", "")
        intencion = (d.get("intencion") or {}).get("intencion", "")
        respuesta = (d.get("respuesta") or {}).get("reply", d.get("detail", ""))
        w = wer(f["texto_esperado"], trans) if ok_http else 1.0
        acierto = intencion == f["intencion_esperada"]
        claves = contiene(respuesta, f.get("palabras_clave", ""))
        exito = ok_http and acierto and claves
        tiempos = d.get("tiempos_ms", {})
        salida.append({"id": f["id"], "categoria": f.get("categoria", ""), "texto_esperado": f["texto_esperado"],
                       "transcripcion": trans, "wer": round(w, 3), "intencion_esperada": f["intencion_esperada"],
                       "intencion": intencion, "acierta_intencion": acierto, "palabras_clave": claves,
                       "exito": exito, "metodo_intencion": d.get("metodo_intencion", ""),
                       "total_ms": tiempos.get("total", int((time.perf_counter() - t0) * 1000)),
                       "tiempos_ms": json.dumps(tiempos), "respuesta": respuesta[:300]})
        print(f"[{f['id']}] {'✔' if exito else '✘'} intención {intencion or '—'} · WER {w:.2f} · "
              f"{salida[-1]['total_ms'] / 1000:.1f} s")
    if not salida:
        print("El CSV no tiene filas.")
        return 1
    origen = "texto" if a.solo_texto else os.path.basename(os.path.normpath(a.audios))
    nombre = os.path.join(base, f"resultados_voz_{origen}_{datetime.now():%Y%m%d_%H%M}.csv")
    with open(nombre, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(salida[0]))
        w.writeheader()
        w.writerows(salida)
    n = len(salida)
    exito = sum(s["exito"] for s in salida) / n
    print("\n" + "=" * 60)
    print(f"Éxito de punta a punta: {exito:.1%} (meta 70 %: {'CUMPLE' if exito >= 0.7 else 'NO CUMPLE'})")
    print(f"Exactitud de la intención: {sum(s['acierta_intencion'] for s in salida) / n:.1%}")
    if not a.solo_texto:
        print(f"WER medio: {statistics.mean(s['wer'] for s in salida):.3f}")
    print(f"Latencia media: {statistics.mean(s['total_ms'] for s in salida) / 1000:.1f} s")
    print(f"Archivo: {nombre}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
