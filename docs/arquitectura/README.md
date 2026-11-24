# Diagramas de arquitectura (C4)

Son las mismas imágenes del documento final y de la presentación de la sustentación.

| Archivo | Vista |
|---|---|
| `c4_l1` | Contexto (C4 nivel 1): personas, BarberForge AI y el servidor de correo |
| `c4_l2` | Contenedores (C4 nivel 2): sitio, web, API, voz, worker, migraciones, base de datos, reentrenamiento y Ollama |
| `c4_l3` | Componentes de la API (C4 nivel 3), un servicio de la arquitectura de microservicios: routers, servicios (citas, asistente, RAG, PQRS, predicción…) y repositorios |
| `despliegue` | Despliegue: GitHub, Minikube, namespaces y Ollama fuera del clúster |
| `voz_flujo` | Vista dinámica del asistente de voz con RAG y ML |
| `modelo_er` | Modelo entidad-relación (sin atributos): 13 entidades y la cardinalidad de cada relación |
| `agendamiento` | Flujo de agendamiento con carriles cliente / sistema: de la solicitud a la cita pendiente |
| `rag_flujo` | Recorrido de un mensaje en el asistente: guardas, embedding, recuperación en pgvector, aumentación del prompt y generación (`.dot` de Graphviz y `.png`) |

Cada vista está en `.svg` (se puede ampliar sin perder calidad) y en `.png`.
Si cambia la arquitectura, hay que actualizar a la vez la imagen, el documento y la diapositiva.
