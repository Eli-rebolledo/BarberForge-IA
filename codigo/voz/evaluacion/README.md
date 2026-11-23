# Evaluación del asistente de voz (feature 012)

Golden Dataset de 30 notas de voz (`golden_voz.csv`) con la misma meta del asistente de texto: **≥ 70 % de éxito
de punta a punta**. Una prueba es exitosa si la API respondió, la intención es la esperada y la respuesta contiene
alguna de las palabras clave (separadas por `|`).

## 1. Los audios
Hay dos juegos de 30 audios, uno por frase de `texto_esperado`, con el nombre de la columna `archivo`
(`v01.webm` … `v30.webm`):

| Carpeta | Qué tiene | ¿Se sube a Git? |
|---|---|---|
| `audios/` | Las frases grabadas por el equipo, con su acento y el ruido normal del lugar | No: son voces de personas (`.gitignore`). Vienen en el zip del proyecto |
| `sinteticos/` | Las mismas frases con voz sintética, para repetir la evaluación sin grabar | Sí |

Si quieren subir también las grabaciones del equipo, borren la línea `audios/` de `evaluacion/.gitignore` y los
patrones de `audios/.gitignore`.

## 2. Ejecutar
```bash
pip install httpx
# con la plataforma arriba: docker compose --profile voz up -d --build
python evaluacion/evaluar_voz.py --url http://localhost:8080                # voces del equipo (audios/)
python evaluacion/evaluar_voz.py --url http://localhost:8080 --audios sinteticos   # voces sintéticas
python evaluacion/evaluar_voz.py --url http://localhost:8080 --solo-texto   # sin audios (solo intención y respuesta)
# Para que las pruebas de agendar y cancelar respondan como un cliente con sesión:
#   BF_TOKEN=<token de un cliente de prueba> python evaluacion/evaluar_voz.py
```
Salida: `resultados_voz_<audios|sinteticos|texto>_<fecha>.csv` con WER, intención, palabras clave y latencias por etapa
(`transcribir`, `entender`, `responder`, `sintetizar`).
