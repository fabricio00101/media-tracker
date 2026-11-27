# Especificación técnica vigente: Media Tracker

Este documento describe la implementación actual del repositorio. La guía de instalación para usuarios está en [README.md](README.md); las variables de entorno completas y sus valores iniciales están en [.env.example](.env.example).

## 1. Propósito y arquitectura

Media Tracker es una aplicación Flask que consulta Prowlarr, agrupa releases y enriquece los resultados con metadatos de TMDB. La interfaz se sirve como una página y usa JavaScript vanilla.

| Componente | Responsabilidad |
| --- | --- |
| `app.py` | Crear la app Flask, configurar extensiones, errores, cabeceras y registrar blueprints. |
| `routes/search.py` | Validar y atender búsquedas, gestionar caché/concurrencia y paginar grupos. |
| `routes/subtitles.py` | Exponer la búsqueda y descarga de subtítulos. |
| `routes/deluge.py` | Validar y enviar magnets o archivos `.torrent` a Deluge. |
| `services/` | Consultar Prowlarr, TMDB y OpenSubtitles; procesar y agrupar resultados. |
| `utils/` | Validadores, detección de idioma, deduplicación, metadatos y utilidades de seguridad. |
| `templates/index.html` | Plantilla HTML de la aplicación. |
| `static/js/app.js` | Búsqueda, renderizado, filtros, subtítulos, favoritos e historial en el navegador. |

No hay base de datos relacional. Favoritos e historial se guardan en `localStorage`; la caché del servidor y los límites de solicitudes funcionan en memoria si Redis no está disponible, o pueden usar Redis con `REDIS_URL`.

## 2. Stack y ejecución

- Python 3.10 o superior.
- Flask 3.1.3, Flask-Caching 2.3.1, Flask-Limiter 3.8.0, Requests 2.33.0, python-dotenv 1.2.2, parse-torrent-title 2.8.2 y Waitress 3.0.2.
- Redis es opcional; Pytest, pytest-mock y pytest-cov se usan para pruebas.
- `python app.py` inicia Waitress en modo de producción. `HOST` y `PORT` permiten cambiar la dirección y el puerto; los valores predeterminados son `127.0.0.1` y `5000`.
- En modo de desarrollo se usa el servidor de Flask con el depurador desactivado.

## 3. Integraciones y flujos

### Búsqueda

`GET /api/search` consulta `services/prowlarr_service.py`, filtra y agrupa releases, intenta resolver metadatos en TMDB y devuelve grupos con sus torrents.

Parámetros admitidos: `query`, `category`, `min_size_gb`, `quality_tag`, `hdr`, `hevc`, `sdr_only`, `lang_filter`, `min_bpp`, `sort`, `page` y `per_page`. Los valores y límites aceptados se validan en `utils/validators.py`.

La respuesta incluye `results`, `page`, `per_page`, `total_groups`, `total_torrents` y `has_more`. El valor predeterminado de `per_page` es 16 y el máximo es 50. Esta paginación divide los grupos ya procesados: Prowlarr se consulta antes de paginar y su respuesta se limita con `PROWLARR_SEARCH_LIMIT` (predeterminado 500; `0` significa sin límite). No se implementa paginación incremental de la consulta upstream.

El orden predeterminado prioriza seeders. También hay orden por puntuación técnica, año y título. Las claves de búsqueda se almacenan en caché durante cinco minutos. La resolución de metadatos TMDB usa caché de 24 horas y limita las resoluciones por búsqueda.

### Subtítulos

- `GET /api/subtitles/search?tmdb_id=...&media_type=movie|tv&season=...&episode=...` consulta OpenSubtitles en español (`es`). Solo las respuestas exitosas se cachean.
- `GET /api/subtitles/download?file_id=...` obtiene el enlace de descarga. El token se conserva en caché y se vuelve a autenticar si OpenSubtitles lo rechaza.

### Deluge

`POST /api/deluge/add` recibe JSON con `magnet`. Acepta un URI magnet o una URL HTTP(S) que redirija a un magnet o a un archivo `.torrent` válido; después envía el contenido a Deluge mediante JSON-RPC. El acceso desde la interfaz usa un token aleatorio por sesión. `API_SECRET_TOKEN` permite configurar protección adicional para el endpoint.

## 4. Configuración

Los valores predeterminados y las variables disponibles están en `.env.example`. Consideraciones principales:

| Variable | Comportamiento |
| --- | --- |
| `PROWLARR_URL` | URL base de Prowlarr; predeterminada `http://localhost:9696`. |
| `PROWLARR_API_KEY` | Necesaria para búsquedas. Si falta, la aplicación registra un error y las búsquedas fallan; no impide que el servidor arranque. |
| `PROWLARR_SEARCH_LIMIT` | Máximo de resultados solicitados a Prowlarr; predeterminado 500, rango aceptado 0–2000. |
| `PROWLARR_TIMEOUT` | Timeout de la consulta; predeterminado 300 segundos, rango aceptado 10–600. |
| `TMDB_API_KEY`, `TMDB_MAX_RESOLUTIONS` | Metadatos opcionales; se permiten hasta 40 resoluciones por búsqueda de forma predeterminada. |
| `OPENSUBTITLES_API_KEY`, `OPENSUBTITLES_USER`, `OPENSUBTITLES_PASSWORD` | Búsqueda y descarga de subtítulos. |
| `DELUGE_URL`, `DELUGE_PASSWORD` | Conexión con Deluge Web UI. |
| `REDIS_URL` | Redis opcional para caché y rate limiting compartidos/persistentes; si no está disponible se usa almacenamiento en memoria. |
| `SECRET_KEY` | Clave de firma de sesiones. El valor de desarrollo predeterminado genera una advertencia; configurar una clave propia antes de exponer la app. |
| `API_SECRET_TOKEN` | Protección adicional opcional para Deluge. La aplicación advierte si está vacío. |
| `SSRF_ALLOW_PRIVATE_TARGETS` | Permite destinos privados/loopback por defecto para servicios locales; puede desactivarse. |

## 5. Límites, caché y seguridad de transporte

- Rate limits por IP: búsqueda, 60 solicitudes por minuto; búsqueda/descarga de subtítulos y envío a Deluge, 10 por minuto cada ruta.
- Si Redis no se configura o no responde, los rate limits y la caché no se comparten entre procesos y se pierden al reiniciar.
- La deduplicación de búsquedas idénticas en curso usa eventos en memoria del proceso; Redis no coordina ese lock, por lo que varios workers pueden repetir una consulta simultánea.
- La aplicación establece Content Security Policy y otras cabeceras HTTP de seguridad.
- Las descargas de `.torrent` validan destinos y redirecciones, limitan el tamaño del archivo y comprueban que el contenido tenga formato bencode de torrent.

## 6. Distribución y pruebas

- `app.spec` incluye `templates/`, `assets/` y `static/`, además de los imports dinámicos requeridos por PyInstaller.
- Ejecutar pruebas: `python -m pytest`.
- Crear el ejecutable: `python -m PyInstaller app.spec --noconfirm`.
