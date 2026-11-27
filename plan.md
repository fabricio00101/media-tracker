# Estado actual y mejoras posibles — Media Tracker

Este documento refleja el código comprobado en `main`. No es una lista de tareas ya pendientes de implementación: los puntos que antes figuraban como faltantes se contrastaron con el repositorio y se resumen abajo.

## Estado confirmado

- **Backend modularizado:** `app.py` registra blueprints; las rutas están en `routes/` y la lógica de integraciones/procesamiento en `services/`.
- **Frontend separado:** `templates/index.html` carga `static/js/app.js`; `app.spec` incluye los archivos estáticos en el ejecutable.
- **Configuración de ejemplo:** existe `.env.example` y `.env` está excluido por `.gitignore`. `.env` no está versionado y no aparece en el historial disponible de las referencias locales; no se inspeccionaron sus valores.
- **Pruebas automatizadas:** existe una suite bajo `tests/` que cubre rutas, validación, frontend, caché y regresiones de seguridad.
- **Protecciones presentes:** hay rate limiting, cabeceras CSP, escapado HTML y delegación de eventos en el frontend, y validación de descargas/redirecciones para archivos `.torrent`.
- **Caché y paginación:** las duraciones de caché están centralizadas; el token de OpenSubtitles se verifica antes de reutilizarlo. `/api/search` pagina los grupos de resultados y devuelve metadatos de paginación.
- **Documentación reconciliada:** `README.md` y `spec.md` describen ahora la estructura, configuración y comportamiento actuales.
- **Verificación local:** `python -m pytest -q` terminó con 147 pruebas aprobadas. Flask-Limiter avisó que, sin Redis, el almacenamiento de límites es en memoria.

## Mejora candidata, pendiente de decisión

### Evaluar paginación incremental desde Prowlarr

Hoy la aplicación solicita un lote limitado por `PROWLARR_SEARCH_LIMIT` (500 por defecto), procesa ese lote y después pagina los grupos para la API/UI. Por lo tanto, la paginación visible no reduce la cantidad descargada ni procesada por búsqueda.

Antes de implementarlo, confirmar si la API de Prowlarr admite una forma de paginar resultados compatible con este flujo. Si la admite, definir cómo se conservarán filtros, agrupación, orden y conteos entre páginas, y agregar pruebas con respuestas simuladas. Si no la admite, mantener explícito el límite configurable y evitar presentar la paginación actual como paginación upstream.

## Consideraciones operativas

- Redis es opcional; sin él, la caché y los contadores de rate limit son locales al proceso y no sobreviven reinicios.
- La deduplicación de búsquedas simultáneas también es local al proceso; Redis no coordina ese lock entre workers.
- `SECRET_KEY` tiene un valor de desarrollo con advertencia. Configurar una clave propia antes de exponer la aplicación.
- `API_SECRET_TOKEN` es opcional, pero la aplicación advierte si está vacío; configurarlo si el endpoint de Deluge se expondrá más allá del uso local.
