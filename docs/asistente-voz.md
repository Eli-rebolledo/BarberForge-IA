# Asistente de voz (feature 012): cómo probarlo en tu PC

Spec: `spec/features/012-asistente-voz/` · Evaluación: `codigo/voz/evaluacion/`

## 1. Levantar todo con el perfil «voz»
```bash
cp .env.example .env            # si aún no lo tienes; en equipos con poca RAM: LLM_MODEL=llama3.2:3b
docker compose --profile voz up -d --build
docker compose logs -f bf-voz   # espera «Application startup complete»
```
La primera construcción tarda (descarga Whisper `base` ≈ 150 MB y la voz de Piper ≈ 60 MB). Revisa:
- http://localhost:8001/voz/health → `whisper_cargado: true` y `tts: true` (si es `false`, leerá el navegador).
- http://localhost:8001/docs → puedes probar `POST /voz/texto` sin micrófono.

> En Windows, Docker Desktop necesita unos 8 GB asignados para Ollama (llama3.2:3b) + voz. Con menos memoria usa
> `LLM_MODEL=llama3.2:3b` o `INTENCION_CON_LLM=false` en el `.env`.

## 2. Probar desde la web
1. Abre http://localhost:8080 (el micrófono solo funciona en `localhost` o con https).
2. Inicia sesión como cliente (o crea una cuenta) y abre el asistente.
3. Toca el **micrófono**, acepta el aviso y el permiso del navegador, habla y toca **■** para enviar.
4. Prueba estas frases:
   | Dices | Qué debe pasar |
   |---|---|
   | «¿Cuánto cuesta el corte clásico?» | Respuesta del RAG con fuentes, leída en voz alta |
   | «Quiero sacar un turno para la barba con Carlos» | Botones con los horarios; al tocar uno se agenda y la cita guarda su **riesgo ML** |
   | «¿Qué citas tengo?» | Lista de tus citas |
   | «Quiero cancelar mi cita» | Te pregunta cuál cancelar |
   | «Tengo una queja» | El asistente pregunta qué pasó (todavía no radica nada) |
   | «El barbero llegó media hora tarde y no me avisaron» | Radicado `PQRS-000NN` con canal `voz`; correo en MailHog (http://localhost:8025) |
5. Como administrador: pestaña **PQRS** del panel y la insignia **Riesgo N %** en **Citas**.

## 3. Probar sin micrófono (consola)
```bash
curl -s -X POST http://localhost:8001/voz/texto -H "Content-Type: application/json" \
     -d '{"texto":"Quiero poner una queja porque me atendieron tarde"}'
# Con un archivo de audio:
curl -s -X POST http://localhost:8001/voz/ -F "audio=@nota.webm" -F "responder_con_voz=false"
```
En PowerShell usa `curl.exe` en lugar de `curl`.

## 4. Evaluación (Golden Dataset de voz)
Ver `codigo/voz/evaluacion/README.md`: graben los 30 audios y ejecuten `python evaluacion/evaluar_voz.py`.
Para una primera medición sin audios: `python evaluacion/evaluar_voz.py --solo-texto`.

## 5. Kubernetes
El pipeline construye la imagen `barberforge-voz`, la escanea con Trivy y, en `main`, la publica en GHCR con SBOM y
firma de Cosign. `values-dev.yaml` trae `voz.enabled: true` y el job «gitops» actualiza su tag junto con la API y la
web, así que Argo CD la despliega sola. Necesita unos 1,5 GB de RAM libres en Minikube; si no alcanzan, pon
`voz.enabled: false` en `values-dev.yaml` y la web sigue funcionando (el micrófono avisa que la voz no está disponible).

## 6. Responder las PQRS
En el panel, pestaña **PQRS** → **Responder**: cambia el estado (abierta, en trámite, cerrada) y escribe la respuesta.
Si la PQRS la radicó un usuario registrado, le llega por correo (revísalo en MailHog); si fue un visitante, queda
guardada en el panel.

## Problemas comunes
| Síntoma | Causa y solución |
|---|---|
| «El asistente de voz no está disponible» | `bf-voz` no está arriba: `docker compose --profile voz up -d` |
| El botón del micrófono no aparece | El navegador no permite el micrófono fuera de `localhost`/https |
| Responde con reglas (`metodo_intencion: reglas`) | Ollama no respondió a tiempo o el modelo aún se descarga |
| No habla | No se descargó la voz de Piper: el navegador debería leerla; revisa el volumen del equipo |
| Agendar dice «inicia sesión» | La voz usa tu sesión: entra con una cuenta de cliente |
