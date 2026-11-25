# Guía de pruebas para la sustentación

Esta guía explica cómo correr las pruebas que en las diapositivas 24 y 29 dicen «Por medir». También trae dos pruebas opcionales que dan más evidencia.

Todo se hace con la plataforma corriendo en Docker Compose, con la voz y la observabilidad encendidas. El `.env` debe tener esta línea:

```
COMPOSE_PROFILES=voz,observabilidad
```

Y el modelo con el que se evaluó el RAG, que es el más rápido en CPU (si su `.env` dice `LLM_MODEL=llama3`, cámbienlo):

```
LLM_MODEL=llama3.2:3b
```

Para que haya métricas y alertas en Grafana, también debe tener:

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-lgtm:4318
```

Antes de empezar, en PowerShell y en la carpeta del proyecto:

```powershell
docker compose up -d
docker compose ps          # todo en Up / healthy
pip install httpx          # una sola vez, para el script de la voz
```

**Regla de oro.** En las diapositivas va lo que salga, aunque no llegue a la meta. Un resultado bajo explicado (por ejemplo, «el WER sube con ruido de fondo») vale más que un número perfecto que nadie puede mostrar. Guarden siempre el CSV y las capturas: son la evidencia.

| # | Prueba | Diapositiva | Tiempo | Quién |
|---|---|---|---|---|
| 1 | Evaluación de la voz con 30 audios | 24 y 29 | ~1 h | Los cuatro graban; uno ejecuta |
| 2 | Ejercicio de incidente (alerta de Ollama) | 27 y 29 | ~15 min | Uno |
| 3 | Ensayo de recuperación cronometrado | 29 | ~20 min (Compose) | Uno, con otro cronometrando |
| 4 | Pipeline en verde en GitHub | 25 y 29 | Al subir el repositorio | Quien suba el repositorio |
| 5 | (Opcional) RAG contra la aplicación | 17 | ~40 min, corre solo | Uno |

---

## 1. Evaluación del asistente de voz (30 audios)

**Qué mide:**
- **WER:** cuántas palabras se transcriben mal.
- **Intención:** si el sistema entendió lo que se pidió.
- **Éxito de punta a punta:** si la respuesta trae la información esperada.
- **Latencia:** el tiempo de cada etapa.

### 1.1 Grabar
1. Abran `codigo/voz/evaluacion/golden_voz.csv`. Cada fila tiene la frase (`texto_esperado`) y el nombre del archivo (`archivo`: `v01.webm` … `v30.webm`).
2. Repártanse las frases: unas 8 por integrante, para que haya varias voces.
3. Graben cada frase como la diría un cliente, con el celular (grabadora de voz) o con la Grabadora de Windows. Ruido normal de fondo está bien; eso también se mide.
4. Copien los audios a `codigo/voz/evaluacion/audios/` con el nombre exacto de la columna `archivo`.
5. **Si los audios quedaron en `.m4a`** (es lo normal en el celular y en Windows), cambien la extensión en el CSV de una vez:
   ```powershell
   cd codigo\voz\evaluacion
   (Get-Content golden_voz.csv) -replace '\.webm', '.m4a' | Set-Content -Encoding utf8 golden_voz.csv
   ```
   Los audios no se suben a Git: la carpeta ya está en `.gitignore`.

### 1.2 Crear un cliente de prueba
Algunas frases son «quiero agendar» o «cancela mi cita». Para que respondan como un cliente con sesión:
1. Registren en http://localhost:8080 un cliente de prueba, por ejemplo `prueba.voz@demo.co`.
2. Saquen su token:
   ```powershell
   $cuerpo = '{"email":"prueba.voz@demo.co","password":"LaClaveQuePusieron"}'
   $env:BF_TOKEN = (Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/login -ContentType 'application/json' -Body $cuerpo).token
   ```

### 1.3 Ejecutar
Desde `codigo\voz`:
```powershell
python evaluacion\evaluar_voz.py --url http://localhost:8080
```
Al final imprime:
- Éxito de punta a punta (meta 70 %).
- Exactitud de la intención.
- WER medio.
- Latencia media.
- El archivo `resultados_voz_<fecha>.csv`.

Tomen captura de esa salida.

Sin audios todavía, pueden medir solo la intención y la respuesta:
```powershell
python evaluacion\evaluar_voz.py --url http://localhost:8080 --solo-texto
```
Sirve para revisar el sistema, pero no reemplaza la prueba con audios: no mide la transcripción.

### 1.4 Qué hacer con el resultado
- Guarden el CSV en `docs/evaluacion-voz/` (créenla) junto con la captura.
- Llenen la diapositiva 24 (columna «Resultado») y la fila «Evaluación de voz» de la diapositiva 29. O mándenme el CSV y yo actualizo las diapositivas y el documento.
- **Si el WER sale alto en alguna frase,** miren en el CSV qué entendió Whisper. Suele ser ruido, una frase muy rápida o un nombre propio. Eso es material para la sustentación: «lo medimos, esto falló y esta es la causa».

---

## 2. Ejercicio de incidente: alerta de Ollama

**Qué demuestra:** que la observabilidad detecta una falla real y avisa sola, que el sistema sigue funcionando sin la IA y cuánto tardan la detección y la recuperación.

1. Abran:
   - **Grafana:** http://localhost:3000 (admin / admin), en **Alerting › Alert rules › BarberForge**. Tomen captura con la alerta en verde (Normal).
   - **MailHog:** http://localhost:8025.
2. Anoten la hora y detengan Ollama:
   ```powershell
   docker compose stop bf-ollama
   ```
3. Hagan 3 o 4 preguntas en el chat de la aplicación. Debe responder con el respaldo sin IA. Tomen captura.
4. En unos minutos la alerta «El modelo de lenguaje (Ollama) está fallando» pasa a **Firing** y llega un correo a MailHog. Anoten la hora y tomen captura de las dos.
5. Recuperen el servicio y anoten la hora:
   ```powershell
   docker compose start bf-ollama
   ```
6. Hagan una pregunta para generar tráfico normal. La alerta vuelve a **Normal** y llega el correo de resolución. Tomen captura.
7. Llenen la tabla de «Registro de incidentes» en `docs/runbook.md`:

   | Fecha | Qué pasó | Detección | Causa | Solución | Tiempo hasta recuperar |
   |---|---|---|---|---|---|
   | 2026-11-2X | Ollama detenido (ejercicio) | Alerta de Grafana + correo, a los N min | Contenedor detenido | `docker compose start bf-ollama` | N min |

Si en 10 minutos no se dispara la alerta, revisen que el `.env` tenga `OTEL_EXPORTER_OTLP_ENDPOINT` y reinicien con `docker compose up -d`.

---

## 3. Ensayo de recuperación cronometrado

**Qué demuestra:** que si se pierde la base de datos, el sistema se recupera desde un respaldo en menos de 30 minutos (objetivo del runbook).

### Opción A: Docker Compose (recomendada, ~20 min)
Uno ejecuta y otro cronometra.
1. Creen datos visibles: una cita, una PQRS y una pregunta enseñada al asistente.
2. **Respaldo:**
   ```powershell
   docker compose exec bf-db pg_dump -U barber -Fc -f /tmp/respaldo.dump barber
   docker compose cp bf-db:/tmp/respaldo.dump .\respaldo.dump
   ```
3. **Desastre.** Pongan el cronómetro en marcha y borren solo la base de datos. No usen `down -v`, que también borraría los modelos de Ollama.
   ```powershell
   docker compose stop bf-api bf-db
   docker compose rm -f bf-db
   docker volume rm barberforge-ia_pgdata
   ```
   Si la carpeta del proyecto tiene otro nombre, el volumen se llama `<carpeta>_pgdata`. Lo ven con `docker volume ls`.
4. **Recuperación:**
   ```powershell
   docker compose up -d
   docker compose cp .\respaldo.dump bf-db:/tmp/respaldo.dump
   docker compose exec bf-db pg_restore -U barber -d barber --clean --if-exists /tmp/respaldo.dump
   docker compose restart bf-api
   ```
5. **Comprobación:** inicien sesión, vean que la cita y la PQRS siguen ahí y pregunten lo que le enseñaron al asistente. Detengan el cronómetro.
6. Anoten el tiempo en el registro de incidentes y tomen captura del antes y el después.

### Opción B: Kubernetes completo (si tienen Minikube funcionando)
Sigan «Ensayo de recuperación» en `docs/runbook.md`, en un equipo distinto: clonar, `setup-minikube.ps1`, `levantar-plataforma.ps1`, esperar a Argo CD en `Synced/Healthy` y restaurar el respaldo. Es la prueba más fuerte, pero necesita el repositorio nuevo con las imágenes ya publicadas en GHCR (prueba 4).

---

## 4. Pipeline en verde en GitHub

Al subir el repositorio nuevo:
1. En **Actions**, abran la ejecución del push a `main`. Tomen captura con todos los jobs en verde: backend, voz, frontend, plataforma, seguridad, imagenes y gitops.
2. Abran el job **seguridad** y uno de **imagenes**. Tomen captura del resumen de Trivy (sin hallazgos críticos).
3. Verifiquen la firma de una imagen (cambien el dueño y el repositorio):
   ```powershell
   cosign verify ghcr.io/<dueño>/barberforge-api:<sha> `
     --certificate-identity-regexp "^https://github.com/<Dueño>/<Repositorio>/.github/workflows/ci.yml@" `
     --certificate-oidc-issuer https://token.actions.githubusercontent.com
   ```
   La salida que dice que la firma es válida es la evidencia de la diapositiva 25.

Si algún job falla, mándenme el log antes de la sustentación.

---

## 5. (Opcional) El RAG contra la propia aplicación

El 82,1 % se midió en OpenWebUI. Esta prueba repite las mismas 56 preguntas contra el asistente de BarberForge (`/api/chat`). Corre sola unos 40 minutos.

```powershell
cd codigo\backend
python evaluacion\evaluar_asistente.py --limite 5                                       # prueba rápida
python evaluacion\evaluar_asistente.py --correo prueba.voz@demo.co --clave LaClaveQuePusieron
```

Imprime el éxito por palabras clave y la latencia. Este resultado no lleva juez, así que compárenlo con la columna «Palabras clave» de la configuración A (71,4 %).

Las preguntas de agendar hacen acciones reales: después cancelen las citas que cree.

---

## Al terminar
Mándenme:
- El CSV de la voz.
- Los tiempos del incidente y de la recuperación.
- Las capturas del pipeline.
- Si hicieron la prueba 5, el CSV del asistente.

Con eso cambio cada «Por medir» por el resultado real en las diapositivas y en el documento.
