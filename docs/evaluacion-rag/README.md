# Evaluación del asistente (RAG) con el Golden Dataset

El asistente se evaluó con **56 preguntas en 10 categorías** (46 que debe responder y 10 en las que debe negarse o
redirigir). La evaluación se hizo en OpenWebUI con el modelo `barberforge-soporte` (llama3 + la base de conocimiento de
la barbería) y un segundo modelo como juez (`llama3.2:3b`) que califica fidelidad y completitud de 1 a 5.

Una prueba **pasa** si contiene al menos la mitad de sus palabras clave (o una señal de negación en las de «negarse»)
**o** si el juez le da un promedio ≥ 4. La meta de la actividad es **≥ 70 % de éxito**.

## Resultados

| Configuración | Fragmentos | Éxito | Solo palabras clave | Fidelidad | Completitud | Latencia p50 | p95 |
|---|---|---|---|---|---|---|---|
| **configA** (elegida) | 500 tokens, solape 100, top K 4 | **82,1 %** (46/56) | 71,4 % | **4,41** | 4,27 | 28,2 s | 47,2 s |
| configB | 250 tokens, solape 50, top K 4 | 75,0 % (42/56) | 62,5 % | 4,11 | 4,04 | 26,9 s | 58,6 s |
| sin RAG | — (solo el modelo) | 80,4 % (45/56) | 44,6 % | 3,82 | 3,96 | 18,2 s | 36,0 s |

**Lectura.** Sin RAG el modelo «suena bien» (el juez le aprueba muchas respuestas), pero acierta mucho menos los datos
concretos de la barbería: las palabras clave bajan de 71,4 % a 44,6 % y la fidelidad de 4,41 a 3,82. Con fragmentos
pequeños (configB) se parte el contexto y se pierden precios y plazos. Por eso se eligió la **configA**, y el RAG
propio de la aplicación (`app/services/rag.py`) sigue la misma idea: trocea cada documento por párrafos en fragmentos
de hasta 700 caracteres, para que una sección completa (un precio con su duración, un plazo con su condición) no se parta.

**Lo que falló y cómo se corrigió en BarberForge.** Las categorías más débiles fueron PQRS (50 %) y recordatorios
(60 %). En la aplicación, agendar, cancelar y radicar PQRS no las redacta el modelo: van directo a la base de datos
(decisión «llama3 para hablar, base de datos para actuar»), y las PQRS por voz quedan con número de radicado.

## Archivos
- `golden_dataset.csv`: las 56 preguntas con su respuesta esperada y sus palabras clave.
- `resultados/`: detalle por pregunta (CSV y JSON), resumen (MD) y gráficas por categoría y de latencia de cada
  configuración.
- El script original y la base de conocimiento están en el repositorio de la actividad de RAG (OpenWebUI).

## Repetir la evaluación contra la aplicación
`codigo/backend/evaluacion/evaluar_asistente.py` usa el mismo dataset y el mismo criterio de palabras clave contra el
asistente propio (`POST /api/chat`), con la aplicación corriendo en Docker:

```powershell
cd codigo\backend
python evaluacion\evaluar_asistente.py --limite 5     # prueba rápida
python evaluacion\evaluar_asistente.py                # las 56 preguntas
```

Las preguntas de agendar y PQRS hacen acciones reales: úsalo con los datos de demostración, no en producción.
