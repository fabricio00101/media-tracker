# Registro de Sesión (session_log.md)

## Qué se completó
- **Fase 1: Seguridad**:
  - Creado `.env.example`.
  - Confirmado que `.env` no tiene historial público expuesto.
  - Integrado `flask-limiter` en la app para prevenir abusos (30 req/min para búsquedas y 10 req/min para subtítulos) e implementado un handler de error para respuestas 429 en formato JSON.
  - Corregida vulnerabilidad XSS en carga de magnets usando `data-` attributes en lugar de `onclick` inline y delegación de eventos en JS vanilla.
- **Fase 2: Limpieza Inicial**:
  - Corregido typo `containter` -> `container` en el footer.
  - Extraído todo el JavaScript inline de `templates/index.html` a su propio archivo estático en `static/js/app.js`.
  - Unificadas duraciones de caché en constantes en `config.py` y agregada validación de expiración manual de token de OpenSubtitles.
  - Agregado logging para errores atrapados al consultar TMDB.
  - Reubicados imports redundantes al inicio de cada archivo.
- **Fase 3 y 4: Tests y Refactor**:
  - Separado el backend monolítico de `app.py` en Flask Blueprints (`routes/search.py`, `routes/subtitles.py`, `routes/deluge.py`) y servicios separados (`services/tmdb.py`, `services/subtitles.py`).
  - Creada suite de pruebas en `tests/` (`conftest.py`, `test_search.py`, `test_subtitles.py`, `test_deluge.py`, `test_tmdb.py`) utilizando `pytest` y `pytest-mock`.
- **Fase 5: Funcionalidad y UX**:
  - Añadido filtro de idiomas server-side en `/api/search` compatible con selección múltiple separada por comas, optimizando el ancho de banda del backend.
  - Implementados timeouts de 15 segundos con `AbortController` al buscar y descargar subtítulos en el frontend para evitar esperas infinitas del usuario.

## Qué quedó pendiente
- Ningún elemento pendiente del `plan.md` aprobado. El plan de mejoras se ha completado en su totalidad.

## Decisiones tomadas
- Se optó por usar `flask-limiter` como la librería estándar para la rate-limitation.
- Se implementó soporte de filtrado server-side de múltiples idiomas por medio de listas separadas por comas para preservar la capacidad del frontend de tener múltiples checkboxes seleccionados.
- Se deshabilitó dinámicamente el backend del caché en entornos de pruebas usando `NullCache` en `conftest.py` y agregando un fixture `clear_cache` para prevenir colisión de estados entre tests paralelos.

---

## Sesión 2026-11-18 — Optimización y mejoras de UX

### Qué se completó
- **Limpieza de `requirements.txt`**: se eliminaron dependencias no usadas (Django, FastAPI, pandas, numpy, mysql-connector, psycopg2, etc.) dejando solo las necesarias.
- **Entorno verificado**: dependencias instaladas y suite de tests ejecutada (7/7 passing).
- **Timeout de Prowlarr** reducido de 160s a 30s en `routes/search.py`.
- **Mejoras de bajo esfuerzo**:
  - Barra de progreso global durante las búsquedas.
  - Búsqueda en tiempo real con debounce (1200 ms, mínimo 4 caracteres) y cancelación de búsquedas previas vía `AbortController` + número de secuencia.
  - Página de error dedicada (`templates/error.html`) con handlers 404/500 (respuestas JSON en rutas `/api/*`).
- **Mejoras de medio esfuerzo**:
  - Soporte opcional de **Redis** para caché (`RedisCache`) y rate-limiting, con fallback automático a memoria si no está disponible.
  - **Exportación de resultados** a JSON y CSV desde el frontend (CSV con BOM UTF-8 para Excel).

### Qué quedó pendiente
- Verificación manual en navegador con Prowlarr activo (el entorno actual no tiene `.env` configurado).
- Mejoras de alto esfuerzo: paginación server-side, soporte multilingüe completo y escalado con Redis + múltiples workers.

### Decisiones tomadas
- Redis es **opcional** mediante `REDIS_URL`; si falta o falla el ping, la app usa `SimpleCache` y memoria para no romper el arranque.
- La exportación se resuelve en el cliente a partir de los datos crudos de la última búsqueda, sin agregar una nueva ruta backend.
- Las búsquedas concurrentes se cancelan con `AbortController` para evitar condiciones de carrera entre resultados viejos y nuevos.

---

## Sesión 2026-11-18 (cont.) — Mejoras de alto esfuerzo

### Qué se completó
- **Paginación server-side de grupos** en `/api/search`:
  - Nuevos parámetros `page` y `per_page` (máximo 50, default 16).
  - El conjunto completo de resultados se procesa una vez y se guarda en caché con una clave estable; la paginación se aplica sobre los grupos ya procesados.
  - La respuesta incluye `page`, `per_page`, `total_groups`, `total_torrents` y `has_more`.
  - El frontend ahora pide la página siguiente al servidor en "Cargar Más", en lugar de paginar datos ya descargados.
  - Se extrajo `buildValidGroups()` en `app.js` para reutilizar el filtrado/renderizado entre la búsqueda inicial y la carga de páginas.
  - La exportación acumula los resultados de todas las páginas cargadas.
- **Despliegue escalable**:
  - `Dockerfile` con Waitress multi-hilo (`--threads=8`).
  - `docker-compose.yml` con la app + Redis 7 (AOF persistente y healthcheck) y `REDIS_URL` configurado.
  - `.dockerignore` para no incluir `.env`, tests ni artefactos.
  - README actualizado con instrucciones de despliegue.
- **Tests**: nuevo `test_search_api_pagination` que valida totales, cortes de página, `has_more` y el tope de `per_page`.

### Qué quedó pendiente
- Validar el `docker-compose.yml` en un equipo con Docker (no está instalado en el entorno actual).
- Soporte multilingüe de la interfaz (ES/EN): no se abordó en esta sesión.

### Decisiones tomadas
- La paginación se hace sobre **grupos de obras** (no sobre torrents), porque es la unidad que se muestra al usuario.
- Se mantiene el filtrado de idioma en el cliente como salvaguarda, aunque el backend ya filtra; `has_more` lo controla el servidor.
- La caché manual (`cache.get`/`cache.set`) reemplaza a `@cache.cached` para que el parámetro `page` no invalide la clave ni fuerce a repetir la consulta a Prowlarr.

---

## Sesión 2026-11-19 — Actualización del ejecutable (`app.exe`)

### Qué se completó
- `app.spec` corregido y ampliado:
  - Se agregó `static/` a `datas` (antes el EXE no incluía el JavaScript).
  - Hidden imports nuevos: `waitress`, `redis`, `dotenv`, `flask_limiter`, `flask_caching.backends.rediscache` y `cachelib.redis`.
- Ejecutable regenerado con PyInstaller 6.22.3 en `dist/app.exe` (~16 MB).
- Prueba de humo del EXE: `GET /` 200 (con botones de exportación), `GET /static/js/app.js` 200 (con `buildValidGroups` y `exportResults`) y 404 renderizando `error.html`.
- README: sección de compilación/uso del ejecutable; se aclaró que el `.env` debe estar en el directorio de trabajo.

### Qué quedó pendiente
- El `.env` real con claves de Prowlarr/TMDB sigue sin configurarse en este entorno.

### Decisiones tomadas
- PyInstaller se usa como **herramienta de build**, no como dependencia de runtime, por lo que no se agregó a `requirements.txt`.
- El ejecutable es onefile: incluye plantillas y frontend; solo requiere el `.env` externo.

---

## Sesión 2026-11-19 (cont.) — Instalación de FlareSolverr

### Qué se completó
- Se instaló **FlareSolverr 3.5.2** para Windows x64 en `F:\Proyectos\flaresolverr` (release oficial, incluye Chromium 153).
- Verificación: `GET http://127.0.0.1:8191/` responde `{"msg":"FlareSolverr is ready!","version":"3.5.2"}`.
- Se agregó `iniciar-flaresolverr.bat` para arrancarlo con doble clic.
- Se detectó Prowlarr 3.0.2 corriendo en `http://localhost:9696` (sin indexer proxies configurados).
- Se registró FlareSolverr como **Indexer Proxy** en Prowlarr (`id=1`, host `http://localhost:8191/`, timeout 60 s) con el tag `flaresolverr` (`id=1`). El test de conexión desde Prowlarr devolvió OK.
- Prowlarr no tiene indexers configurados todavía; cuando se agreguen, hay que asignarles el tag `flaresolverr` para que usen el proxy.

### Qué quedó pendiente
- Asignar el tag `flaresolverr` a los indexers que requieran pasar por Cloudflare (no hay indexers cargados aún).
- Definir si FlareSolverr debe arrancar automáticamente con Windows (hoy es manual con el `.bat`).

### Decisiones tomadas
- Se usó el binario oficial en lugar de clonar el repositorio: el código fuente está pensado para ejecutarse con Docker y en este equipo Docker no está disponible.
- FlareSolverr queda fuera de `requirements.txt` porque es un servicio externo, no una dependencia de Python.

---

## Sesión 2026-11-19 (cont.) — Endurecimiento de seguridad

### Qué se completó
1. **XSS en el frontend** (`static/js/app.js`):
   - Nuevo helper `escapeHtml()` aplicado a todos los datos externos (título, sinopsis, tracker, calidad, codec, magnet, poster, idioma, nombre de archivo de subtítulo).
   - Se eliminaron **todos los `onclick` inline** (10 → 0): ahora las acciones usan atributos `data-*` resueltos por delegación de eventos en el listener global (`fav-btn`, `data-fav-remove`, `data-fav-search`, `data-sub-id`, `data-sub-file`).
   - `toggleFavorite()` recibe el objeto `info` directamente en lugar de un string interpocado en HTML.
   - `querySelector` sobre claves de favoritos ahora usa `CSS.escape()` (evita inyección de selectores).
   - `localStorage` de favoritos se lee y se escribe con `try/catch` (un valor corrupto ya no rompe el arranque de la página).
2. **Fuerza bruta en Deluge** (`routes/deluge.py`): `POST /api/deluge/add` —que recibe la contraseña en JSON-RPC— ahora tiene `@limiter.limit("10 per minute")`. Era el único endpoint sin límite.
3. **SSRF en Deluge** (`routes/deluge.py`): nueva función `_is_safe_remote_url()` que rechaza esquemas no web (`file://`, etc.) y destinos link-local (169.254.0.0/16 incluye 169.254.169.254, metadatos de AWS/GCP; fe80::/10; 0.0.0.0/8). Se aplica tanto a la URL original como a la redirección `Location`, y las redirecciones relativas se normalizan con `urljoin()`.
4. **API key de Prowlarr** (`routes/search.py`): dejó de viajar en query string y ahora se envía en el header `X-Api-Key`.

### Qué quedó pendiente
- Tests de regresión para el rate limit de Deluge y para `_is_safe_remote_url()` (hoy solo hay `tests/test_search.py`).
- Verificación visual en navegador de que favoritos, subtítulos y "Enviar a Deluge" siguen funcionando tras el paso a delegación de eventos.
- Performance (TMDB paralelo, lock contra cache stampede, `limit` en la query a Prowlarr), tests/subtitles/health y CI.

### Decisiones tomadas
- Se optó por **delegación de eventos con `data-*`** en vez de escapar dentro de `onclick`: escapar con entidades HTML no basta ahí, porque el parser decodifica los entidades antes de que JavaScript vea el código.
- En el SSRF se **siguen permitiendo hosts privados** (192.168/10.x), porque ahí suele estar Prowlarr; se bloquean solo los destinos link-local y no-web.
- `escapeHtml()` se aplica también a valores numéricos (`size_gb`, `seeders`) por uniformidad, ya que el costo es despreciable.

---

## Sesión 2026-11-19 (cont.) — Optimización de performance

### Qué se completó
1. **TMDB en paralelo** (`routes/search.py`): el procesamiento se reestructuró en **dos pasadas**:
   - 1ª pasada: filtros baratos (tamaño, calidad, HDR, HEVC, idioma) + `PTN.parse` + recolección de títulos únicos. No se hace ninguna llamada de red.
   - Resolución de metadatos con `ThreadPoolExecutor` (6 workers) para todos los títulos únicos de una vez.
   - 2ª pasada: agrupación con la información ya resuelta.
   - Cada worker crea su propio `app_context()` (Flask no comparte context entre hilos y `flask_caching` lo necesita para resolver el backend).
   - `TMDB_MAX_WORKERS = 6` a propósito: TMDB limita ~40 req / 10 s por IP.
   - Nueva función `_resolve_titles()` más `_detect_spanish()`, `_detect_audio()` y `_matches_language()` extraídas (funciones más pequeñas).
2. **Anti cache-stampede**: locks por clave de caché con doble chequeo (`_get_inflight_lock` + re-lectura dentro del lock). Varias peticiones iguales producen **una sola** consulta a Prowlarr. La primera lectura de caché sigue siendo lock-free. El diccionario de locks se poda por encima de 512 entradas.
3. **Tope de resultados hacia Prowlarr**: nuevo `PROWLARR_SEARCH_LIMIT` (default 500, `0` = sin límite) en `config.py` y `.env.example`, enviado como parámetro `limit`.
4. `routes/search.py` se dividió en funciones pequeñas: `_fetch_prowlarr()`, `_process_results()`, `_resolve_titles()`, con una excepción `ProwlarrError` para centralizar los códigos HTTP de error (503 sin conexión, 502 error, 500 JSON inválido).

### Medidas (script de verificación)
- **TMDB con 48 títulos**: 4,82s secuencial → **0,90s paralelo (5,4x)**. Con el peor caso del timeout de 5s pasaría de ~240s a ~40s.
- **Cache stampede con 8 hilos simultáneos**: **1 sola** llamada a Prowlarr (antes 8), 8 respuestas `200`, 0,55s totales.
- **Params a Prowlarr**: `{'query', 'type', 'limit': 500}` y `apikey` ya no aparece en el query string.

### Qué quedó pendiente
- Tests de regresión para el lock anti-stampede y para `_resolve_titles()`.
- Verificar en producción el valor de `PROWLARR_SEARCH_LIMIT`: 500 puede ser poco para búsquedas muy genéricas (se agrupa por obra, pero el recorte pasa antes de agrupar).
- Tests de `deluge`/`subtitles`, endpoint `/health` y CI.

### Decisiones tomadas
- Se eligió `ThreadPoolExecutor` en lugar de async: `requests` y `PTN` son síncronos y el cambio de arquitectura no se justifica.
- 6 workers como punto medio entre velocidad y el rate limit de TMDB.
- El tope `limit` se aplica **antes** de agrupar; se acepta perder algo de cobertura a cambio de no procesar miles de duplicados. Por eso es configurable y admite `0`.

---

## Sesión 2026-11-19 (cont.) — Tests de regresión

### Corrección a lo reportado antes
- **Sí existían** tests de `deluge`, `subtitles` y `tmdb` (`tests/test_deluge.py`, `test_subtitles.py`, `test_tmdb.py`), pero solo cubrían el camino feliz. Lo que faltaban eran los tests de los cambios nuevos y los casos negativos.

### Qué se completó
- **`tests/conftest.py`**:
  - Fixture autouse `reset_rate_limits()` que limpia los contadores de Flask-Limiter antes y después de cada test. Sin esto, un test que agota una cuota hacía fallar a los siguientes (el rate limit de Deluge necesita11 peticiones contra una cuota de 10).
  - Fixture `simple_cache_app`: reemplaza `NullCache` por `SimpleCache` para los tests que dependen de que la caché guarde algo, y lo restaura al terminar.
- **`tests/test_security.py`** (nuevo, 17 tests):
  - `_is_safe_remote_url` parametrizado (12 casos): esquemas no web, link-local/metadata, `0.0.0.0`, host no resoluble, y hosts válidos (privados y públicos). Usa un `getaddrinfo` falso para no depender de DNS.
  - SSRF en el endpoint: `169.254.169.254` → 400 y `requests.get` nunca se invoca.
  - Validaciones de Deluge: sin magnet → 400, sin credenciales → 500.
  - Rate limit de Deluge: 10 × 503 y la 11.ª → 429.
  - API key de Prowlarr por header `X-Api-Key` y **no** presente en `params`.
- **`tests/test_search_cache.py`** (nuevo, 8 tests):
  - Cache stampede: 8 hilos simultáneos → **1 sola** llamada a Prowlarr, 8 respuestas 200.
  - Cache hit: la segunda búsqueda idéntica no vuelve a consultar.
  - `limit=500` enviado a Prowlarr.
  - `_resolve_titles`: sin entradas, resolución completa de 12 títulos, y fallback local cuando TMDB devuelve `None`.
  - Mapeo de errores: sin conexión → 503, JSON inválido → 500.
- **`tests/test_frontend.py`** + **`tests/frontend_escape_check.js`** (nuevo, 5 tests):
  - `app.js` no debe contener `onclick=`, `onerror=`, `onload=` ni `onmouseover=` (regresión del fix de XSS).
  - Presencia de `escapeHtml` y de sus entidades.
  - Uso de delegación de eventos (`data-fav-info`, `data-sub-id`, `closest()`).
  - `node --check` y ejecución real de `escapeHtml()` contra payloads XSS (extrae la función desde `app.js` y la evalúa).
  - Los tests de Node se saltan automáticamente si `node` no está instalado.
- **`tests/test_subtitles.py`**: se agregaron los4 casos negativos que faltaban (sin `tmdb_id`, sin API key, sin `file_id`, sin token).

### Resultado
- **42 tests** (antes 8), ejecutados **3 veces seguidas sin fallos** ni flakiness, en ~0,75 s.

### Qué quedó pendiente
- CI (GitHub Actions) que corra `pytest` en cada push.
- Cobertura con `pytest-cov` y un umbral mínimo.
- Tests del frontend con un navegador real (Playwright) para validar el renderizado.

### Decisiones tomadas
- `getaddrinfo` se mockea en los tests SSRF: garantiza determinismo y evita timeouts por resolución DNS en CI.
- El test de rate limit aísla el contador por fixture en lugar de desactivar Flask-Limiter, para que la limitación siga estando real durante la suite.
- El test de stampede usa un reloj real con `sleep(0.3)` en vez de un truco de sincronización: falla igual tanto si se rompe la caché como si se rompe el lock.

---

## Sesión 2026-11-19 (cont.) — CI y cobertura

### Qué se completó
- **Cobertura con `pytest-cov`**:
  - `pytest-cov==7.1.0` agregado a `requirements.txt`.
  - Nuevo `.coveragerc`: mide solo código de producción (`omit` de `tests/`, `build/`, `dist/`), excluye el bloque `if __name__ == "__main__":` y muestra líneas faltantes.
  - Gate de cobertura en CI: `--cov-fail-under=70` (actual: **76,83 %**).
- **`tests/test_app.py`** (nuevo, 6 tests) — cubría 54 % y era el archivo más descuidado:
  - Página principal responde 200 con el formulario.
  - 404 en rutas web → `error.html`; 404 en `/api/*` → **JSON** (no HTML).
  - `_redis_available("")` y contra un puerto cerrado → `False`.
  - `USE_REDIS` es booleano y es `False` cuando no hay `REDIS_URL` (el aserto se condiciona al entorno para no romper si alguien corre los tests con Redis configurado).
- **`.github/workflows/ci.yml`** (nuevo):
  - Se ejecuta en `push` a `main` y en `pull_request`.
  - Matriz de **Python 3.10 y 3.12** (rango que declara `AGENTS.md`), `fail-fast: false`.
  - Instala Node 20 (los tests de frontend lo necesitan), valida `node --check static/js/app.js` y corre la suite con cobertura.
  - Sube `coverage.xml` como artefacto.
  - `cache: pip` para acelerar las corridas.
- **`.gitignore`**: ahora ignora `.coverage` y `coverage.xml`.

### Resultado
- **49 tests**, cobertura **76,83 %** sobre código de producción (los tests quedan fuera del cálculo).
- El comando exacto que corre CI se ejecutó localmente: `python -m pytest --cov=. --cov-report=term-missing --cov-report=xml --cov-fail-under=70` → **exit 0**.

### Qué quedó pendiente
- **Ejecutar el workflow real**: no se pudo validar en este equipo (no hay acceso a ejecutar Actions). La validación del YAML fue estructural (sin tabs, indentación par, claves y pasos correctos), no con un parser YAML, porque no hay librería instalada y no se agregan dependencias sin confirmación.
- Commit y push de los cambios: hay ~25 archivos modificados/nuevos sin commitear.
- Cobertura de `services/subtitles.py` (22 %) y de las ramas de error de `routes/deluge.py` (68 %).
- Regenerar `dist/app.exe`.

### Decisiones tomadas
- El umbral se puso en **70 %** con una holgura de ~7 puntos sobre el valor actual: lo suficiente para que una regresión seria lo rompa, sin que diferencias menores entre versiones de Python lo hagan flaky.
- Se eligió matriz de dos versiones en lugar de una sola: el proyecto declara soporte desde 3.10 y probar solo la última ocultaría incompatibilidades.
- No se agregó ningún job de Windows ni de build del `.exe` en CI: encarecería la corrida y el empaquetado ya está verificado manualmente.

---

## Sesión 2026-11-19 (cont.) — Página de error dinámica + ejecutable regenerado

### Qué se completó
- **`templates/error.html` ya no es estática**: antes un 404 mostraba literalmente *"500 - Error Interno del Servidor"* y *"Algo salió mal en nuestros servidores"*.
  - Nueva función `error_page_context(code, description)` en `app.py` que traduce el estado a títulos en español (404, 500 y un fallback genérico para cualquier otro código).
  - `handle_errors()` ahora pasa `code`, `title`, `subtitle` y `description` al template.
  - `error.html` usa `{{ code }}`, `{{ title }}`, `{{ subtitle }}` y `{{ description }}`.
- **Tests**: `tests/test_app.py` pasó de 6 a **10 tests**:
  - El 404 en HTML **no** debe contener "Error del Servidor" y sí debe mostrar "Página no encontrada" / "404 - No encontramos lo que buscas".
  - Contexto para 404 y 500.
  - Código no previsto (503) muestra su propio número y usa la `description` recibida.
  - Código sin `description` no revienta.
- **`dist/app.exe` regenerado** con PyInstaller (15,56 MB) e incluye el `app.js` sin `onclick`, el `error.html` dinámico y los cambios de performance.

### Prueba de humo del ejecutable
| Endpoint | Resultado |
|---|---|
| `GET /` | 200, formulario presente |
| `GET /static/js/app.js` | 200, `escapeHtml` presente, **0 `onclick=`** |
| `GET /no-existe` | 404 → h1 *"Página no encontrada"*, h2 *"404 - No encontramos lo que buscas"*, sin "500" |
| `GET /api/no-existe` | 404 → JSON `{"error": ...}` |
| Procesos restantes | 0 (limpiados con `taskkill /T`) |

> Nota: la primera verificación devolvió `False` por la codificación ANSI de la consola de PowerShell al leer el HTML; leyendo el archivo como UTF-8 el contenido es correcto.

### Resultado final
- **53 tests**, cobertura **77,07 %** (`--cov-fail-under=70` OK), `node --check` OK.

### Qué quedó pendiente
- ~~Commit y push~~ → **hecho**: 5 commits (`e57634d`, `87309f7`, `19ad91c`, `1355b16`, `96f8ee4`).
- Cobertura de `services/subtitles.py` (22 %) y de las ramas de error de `routes/deluge.py` (68 %).
- Soporte multilingüe ES/EN de la interfaz.
- FlareSolverr: decidir autostart con Windows; asignar tag `flaresolverr` al agregar indexers en Prowlarr.

---

## Sesión 2026-11-19 (cont.) — Commits, push y primer CI verde

### Qué se completó
- **Commits en 4 partes lógicas** (26 archivos), validando que el primero quedara en pie en solitario (suite con stash: 48 passed):
  1. `e57634d` feat: Búsqueda robusta, seguridad y tests de regresión (13 archivos)
  2. `87309f7` feat(frontend): XSS, exportación de resultados y UX de búsqueda (4)
  3. `19ad91c` chore: Docker, CI con cobertura y empaquetado (7)
  4. `1355b16` docs: Actualizar README y registro de sesiones (2)
- **Push a `origin/main`** y **primer workflow de CI ejecutado con éxito** en la matriz 3.10 + 3.12 (53 tests, cobertura 77 %, artefactos `coverage-py3.10/12` subidos).
- **Actions actualizadas a runtime Node 24** (`96f8ee4`): `checkout@v5`, `setup-python@v6`, `setup-node@v5`, `upload-artifact@v6` y `node-version: 24`. Motivo: Node 20 llegó a EOL en abril 2026 y GitHub lo removió de los runners en septiembre 2026; cada corrida mostraba la anotación *"Node.js 20 is deprecated"*. Tras el cambio, segunda corrida **verde y sin anotaciones**.

### Decisiones
- Commits separados por área (backend+tests / frontend / infra / docs) en vez de uno solo, para que cada uno sea utilizable y verificable.
- Versiones de actions elegidas entre las confirmadas con `runs.using: node24` (evité tags no verificados).
- No se agregó `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24`: ya no es necesario con las actions actualizadas.

### Resultado final de la sesión
- 53 tests, cobertura 77,07 %, `node --check` OK, CI verde ×2, árbol limpio, `dist/app.exe` regenerado (15,56 MB).

---

## Sesión 2026-11-19 (cont.) — Cobertura de subtítulos y ramas de error de Deluge

### Qué se completó
- **`tests/test_subtitles_service.py` (nuevo, 5 tests)**: primera cobertura directa de `services.get_opensubtitles_token()`.
  - Cache hit (token vigente → no toca red).
  - Sin credenciales → `None` sin intentar login.
  - Login exitoso → guarda en caché con clave `opensubtitles_token_data` y devuelve el token.
  - Login sin `token` en la respuesta → `None` sin escribir caché.
  - Excepción de red en el login → `None` sin escribir caché.
  - Se usó `monkeypatch` para las credenciales en vez de `@patch(..., new=...)`: evita el orden ambiguo de inyección de mocks y el bug de que `new=` no aporta parámetro.
- **`tests/test_deluge.py` (nuevo, 13 tests)**: ramas que `test_security.py` no tocaba.
  - Magnet feliz, error en JSON de respuesta, `raise_for_status` del add, login con `result` falso (401), `ConnectionError` (503), excepción genérica (500).
  - Descarga `.torrent` vía `core.add_torrent_file`, fallo de `raise_for_status`.
  - Redirección 302 a magnet, 302 sin `Location` (502), 302 a URL no permitida (400, con `side_effect=[True, False]` porque `_is_safe_remote_url` se evalúa dos veces), segunda GET de la redirección fallando.
  - `urlparse` lanzando excepción → URL insegura (cierra las 2 líneas restantes del helper SSRF).

### Resultado
| Archivo | Antes | Ahora |
|---|---|---|
| `services/subtitles.py` | 22 % | **100 %** |
| `routes/deluge.py` | 68 % | **100 %** |
| Total proyecto | 77,07 % | **86,78 %** |
| Tests | 53 | **70** |

- Suite corrida dos veces seguidas: 70 passed, sin flakes (~2 s). `node --check` OK.

### Decisiones
- Los tests nuevos van en archivos propios (`test_subtitles_service.py`, `test_deluge.py`) en lugar de mezclarse con los de rutas.
- Helper `_mock_response()` para imitar `requests.Response` (incluye `content` para el `.torrent` en base64).
- No se tocó `routes/subtitles.py` (71 %): su cobertura quedó fuera del alcance de esta ronda.

---

## Sesión 2026-11-19 (cont.) — Arreglo de búsqueda de subtítulos

### Bug reportado
Al hacer clic en "Buscar Subtítulos" la búsqueda "mandaba a cualquier lado". El usuario sospechaba del TMDB ID y acertó.

### Causa raíz (varias, encadenadas)
1. **No existe `.env` en el proyecto** (ni variables de entorno de usuario): `TMDB_API_KEY` está vacía, así que `group_info` no tiene `id`. El frontend generaba `data-sub-id="undefined"` y el backend buscaba literalmente `tmdb_id=undefined` → OpenSubtitles devolvía resultados aleatorios.
2. **Series buscadas mal**: se usaba `tmdb_id` para todo. La API v1 de OpenSubtitles exige `parent_tmdb_id` + `season_number` + `episode_number` para episodios.
3. **Idioma inválido**: se enviaba `languages=es,es-mx`; `es-mx` no es un código válido para la API (solo `es`).
4. **Enlace de respaldo roto**: usaba el TMDB ID en el parámetro `imdbid-` de opensubtitles.org, que espera un IMDb ID.

### Cambios
- `services/tmdb.py`: `get_tmdb_info()` devuelve `media_type` (`movie`/`tv`).
- `routes/search.py`: el fallback local incluye `id: None` y `media_type`; las entradas memoizadas viejas reciben `media_type` vía `setdefault` (compatibilidad con caché de 24 h).
- `routes/subtitles.py`:
  - `_build_subtitles_params()`: películas por `tmdb_id`; series por `parent_tmdb_id` + temporada/episodio (`type=episode`).
  - `tmdb_id` y `file_id` deben ser numéricos (400 si no).
  - Series sin temporada/episodio → 400 explicativo.
  - `languages=es`; mensajes de error con la variable de `.env` que falta.
- Frontend (`app.js` + `index.html`):
  - Botón deshabilitado con tooltip si falta TMDB ID o si la serie solo tiene packs de temporada completa.
  - Selector de episodio en el modal cuando el grupo trae varios.
  - Re-búsqueda al cambiar de episodio; se cancela la petición anterior.
  - Título del modal con `Temporada X · Episodio Y`.
  - Enlace de respaldo por nombre de obra, no por TMDB ID.

### Tests
- `tests/test_subtitles.py`: +14 (parámetros movie/tv, `tmdb_id=undefined`, serie sin episodio, 401/429/500 de OpenSubtitles, 406 y otros errores de descarga).
- `tests/test_tmdb.py`: `media_type` en película y serie.
- `tests/test_search_cache.py`: fallback con `id: None`, serie y `media_type` agregado a caché vieja.

### Resultado
| Archivo | Antes | Ahora |
|---|---|---|
| `routes/subtitles.py` | 71 % | **100 %** |
| Total proyecto | 86,78 % | **90,84 %** |
| Tests | 70 | **88** |

- Suite completa: 88 passed (~2 s), `node --check` OK, plantilla renderiza el selector de episodios.
- `dist/app.exe` regenerado (16,32 MB) y humo-testeado: `GET /` → 200 con el selector de episodios y `tmdb_id=undefined` → 400.
- Commit `70bf1ec` pusheado a `main`; CI verde en Python 3.10 y 3.12 (run 44559556492).

### Pendiente / aviso importante
- Para que la búsqueda funcione de verdad hace falta crear un `.env` (copiar `.env.example`) con `TMDB_API_KEY`, `OPENSUBTITLES_API_KEY`, `OPENSUBTITLES_USER` y `OPENSUBTITLES_PASSWORD`. Sin esas claves el botón queda deshabilitado y el modal muestra el error de configuración (ya no consulta con datos basura).
- En el `.exe` empaquetado, `load_dotenv()` busca el `.env` desde el directorio de ejecución (comportamiento `sys.frozen` de python-dotenv): debe estar junto a `app.exe` o en una carpeta superior.

---

## Sesión 2026-11-19 (cont.) — Configuración real del .env

### Qué se completó
- **`.env` creado** en la raíz (ignorado por git; verificado con `git check-ignore`). Sin secretos en el repositorio ni en el log.
  - `PROWLARR_URL` + `PROWLARR_API_KEY` reales: la key se leyó de `C:\ProgramData\Prowlarr\config.xml` (32 chars).
  - `PROWLARR_SEARCH_LIMIT=500`.
  - `DELUGE_URL=http://localhost:8112` y `DELUGE_PASSWORD=deluge` (default de Deluge; ajustar si se cambió).
  - `REDIS_URL` vacío: caché y rate-limit en memoria.
  - `TMDB_API_KEY`, `OPENSUBTITLES_API_KEY`, `OPENSUBTITLES_USER` y `OPENSUBTITLES_PASSWORD` cargadas por el usuario.
- **Validaciones reales contra las APIs**:
  - TMDB: HTTP 200; `Inception` → id 27205 (`movie`), `The Last of Us` → id 100088 (`tv`).
  - OpenSubtitles búsqueda película: **41** subtítulos en español para *Inception*.
  - OpenSubtitles búsqueda serie: **10** subtítulos para *The Last of Us* S01E01, con el episodio correcto (confirma `parent_tmdb_id` + temporada/episodio).
  - Login: HTTP 200 con `OPENSUBTITLES_USER=fabrigol`; `get_opensubtitles_token()` devuelve token.
  - Descarga: `/api/subtitles/download?file_id=...` → 200 con link de `www.opensubtitles.com` (consumió 1 descarga de la cuota diaria).
- El `.exe` en `dist/` encuentra el `.env` de la raíz al ejecutarse desde `dist` (python-dotenv camina hacia arriba desde el cwd).

### Decisiones
- El usuario de OpenSubtitles es `fabrigol` (la API rechaza el email como usuario).
- Se evitó seguir probando candidatos de usuario para no gatillar el rate limit de login (HTTP 429).
- No se versiona el `.env`; el `.env.example` queda como plantilla sin secretos.

### Pendiente
- Prowlarr está detenido (binario en `C:\ProgramData\Prowlarr\bin\Prowlarr.exe`, sin servicio registrado) y tenía 0 indexers.
- Deluge no está corriendo (puerto 8112 libre); confirmar la contraseña real de la Web UI.
- Si las claves se compartieron por un canal no privado, conviene rotarlas.

---

## Sesión 2026-11-19 (cont.) — Corrección de tests de caché ante presencia de TMDB_API_KEY

### Qué se completó
- Se aislaron `test_cache_stampede_una_sola_llamada` y `test_cache_hit_no_vuelve_a_consultar` en `tests/test_search_cache.py` mockeando `routes.search.get_tmdb_info`.
- Al estar configurado el `.env` con una `TMDB_API_KEY` válida, los hilos de prueba realizaban llamadas HTTP a TMDB interceptadas por el mock genérico de `requests.get` de Prowlarr, distorsionando el contador de llamadas esperado.
- Se ejecutó la suite completa de tests de pytest resultando en **88/88 tests pasando**.

### Qué quedó pendiente
- Mismo estado pendiente: iniciar Prowlarr con indexers y Deluge si se van a efectuar búsquedas y descargas reales en la app.

### Decisiones tomadas
- Se aplicó `@patch("routes.search.get_tmdb_info", return_value=None)` en los tests de concurrencia y caché de Prowlarr para desacoplar completamente la resolución de metadatos de TMDB del chequeo del stampede lock y el almacenamiento en caché de los resultados de búsqueda.

---

## Sesión 2026-11-19 (cont.) — Implementación de la Etapa 1 de la Hoja de Ruta (Estabilización)

### Qué se completó
- **Ciclo de vida de locks de búsqueda (`routes/search.py`)**: Implementado contextmanager `_inflight_lock(key)` con conteo de referencias (`refcount`). Ya no se eliminan locks arbitrariamente con `locked() == False`, previniendo colisiones de hilos en espera y garantizando que múltiples llamadas concurrentes con caché fría consulten Prowlarr una única vez.
- **Validación estricta de parámetros HTTP en `/api/search`**:
  - `query`: requerido, longitud máxima de 150 caracteres.
  - `category`: validada contra lista permitida (`all`, `movies`, `tv`, `docs`), devolviendo 400 en caso contrario.
  - `lang_filter`: validado contra lista permitida (`all`, `latino`, `castellano`, `sub`, `otros`).
  - `min_size_gb`: validación con `math.isfinite()`, rango estricto entre 0.0 y 2000.0 GB, rechazando `NaN`, `Inf` y negativos con 400.
  - `quality_tag`: longitud acotada a máximo 30 caracteres.
- **Tolerancia a respuestas de Prowlarr (`_fetch_prowlarr`)**:
  - Verificación de tipos para listas o diccionarios con clave `Results` tipo lista. Error 502 controlado ante estructuras anómalas.
  - Filtrado defensivo de items individuales (descarte de valores nulos o sin título).
- **Desambiguación de grupos (Películas vs Series)**: Clave de agrupación `tmdb_{media_type}_{title}_{year}` y `local_{media_type}_{title}_{year}` para evitar que obras homónimas compartan tarjeta.
- **Pruebas añadidas**:
  - `test_search_param_validations`: cubre todas las combinaciones inválidas (query larga, category, lang_filter, min_size_gb bounds/NaN/Inf, quality_tag).
  - `test_prowlarr_responses_robustness`: cubre respuestas dict con Results, items nulos y respuestas de tipo inesperado (502).
  - `test_grouping_separates_movie_and_tv`: verifica que película y serie homónimas formen grupos independientes.
  - Suite completa: **91 tests pasando (100% verde)**.
- **Hoja de ruta actualizada**: Marcados como completados los 5 ítems de la *Etapa 1 — Estabilización* en `media-tracker-hoja-de-ruta.md`.

### Qué quedó pendiente
- Avanzar con la *Etapa 2 — Calidad de metadatos y servicios externos* (scoring en selección de TMDB, semáforo global para TMDB, regex en detección de idiomas).

### Decisiones tomadas
- Se utilizó un context manager estándar de Python (`@contextmanager`) para el manejo del lock y refcount dentro de `_inflight_guard` para asegurar liberación simétrica en bloque `finally`.

---

## Sesión 2026-11-19 (cont.) — Implementación de la Etapa 2 de la Hoja de Ruta (Calidad de Metadatos y Servicios Externos)

### Qué se completó
- **Scoring y Selección de Candidatos en TMDB (`services/tmdb.py`)**:
  - Implementada función `_normalize_title()` quitando acentos y signos para comparaciones semánticas.
  - Implementado sistema de puntuación en `_score_tmdb_candidate()` evaluando:
    - Coincidencia exacta de título o título original (+60 / +55 pts).
    - Coincidencia de año con tolerancia (+30 pts si coincide, penalizaciones proporcionales ante diferencias mayores).
    - Desempate por volumen de votos (+10 / +5 pts).
  - Filtro por umbral mínimo (`score >= 30`): si los resultados devueltos por TMDB no guardan relación con la búsqueda, se descartan en vez de forzar el primer resultado arbitrario.
- **Límite Global de Concurrencia y Resiliencia en TMDB (`services/tmdb.py`)**:
  - `tmdb_semaphore = threading.Semaphore(6)` limita las consultas concurrentes salientes a TMDB a nivel de toda la aplicación.
  - Manejo de respuestas `HTTP 429` (Too Many Requests) con reintento automático y backoff exponencial breve (`time.sleep(0.5 * attempt)`).
- **Detección Robusta de Idiomas y Audio (`routes/search.py`)**:
  - Se sustituyeron las búsquedas de subcadenas simples por expresiones regulares con límites de palabra (`\b`).
  - Previene falsos positivos en títulos con palabras comunes en inglés como `blade.runner.final.cut` o `plateau` (que antes disparaban `lat` -> Latino).
  - Normalización de variantes en audio (`atmos`, `truehd`, `dts-hd`, `eac3`, `dd5.1`, `aac`).
- **Pruebas y Suite de Tests**:
  - `tests/test_tmdb.py`: pruebas para desempate de remakes por año (`Dune 1984` vs `2021`), descarte de candidatos irrelevantes y reintento exitoso ante 429.
  - `tests/test_search.py`: pruebas unitarias para `_detect_spanish` con word boundaries (ausencia de falsos positivos) y `_detect_audio`.
  - Suite completa: **96 tests pasando (100% verde)**.
- **Hoja de ruta actualizada**: Marcados como completados los 5 ítems de la *Etapa 2 — Calidad de metadatos y servicios externos* en `media-tracker-hoja-de-ruta.md`.

### Qué quedó pendiente
- Avanzar con la *Etapa 3 — Mantenibilidad* (extracción de lógica de búsqueda a `search_service.py` y `prowlarr_service.py`, centralización de validaciones).

### Decisiones tomadas
- Se mantuvo `TMDB_CONCURRENCY_LIMIT = 6` para respetar el límite de 40 requests cada 10 segundos de la API pública de TMDB por IP.
- Si ningún candidato de TMDB alcanza el score mínimo de 30, `get_tmdb_info` retorna `None` para que el backend use fallback a información local en lugar de asociar un póster o sinopsis equivocada.

---

## Sesión 2026-11-19 (cont.) — Implementación de la Etapa 3 de la Hoja de Ruta (Mantenibilidad y Modularización)

### Qué se completó
- **Modularización de Servicios y Utilidades**:
  - Creado `utils/validators.py`: centraliza la validación estricta de parámetros (`validate_search_params`) y definición de excepciones (`ValidationError`).
  - Creado `utils/language_detector.py`: centraliza `detect_spanish`, `detect_audio` y `matches_language`.
  - Creado `services/prowlarr_service.py`: aísla la comunicación HTTP con Prowlarr (`fetch_prowlarr`) y los errores controlados (`ProwlarrError`).
  - Creado `services/search_service.py`: aísla el pipeline de procesamiento, parseo de PTN, agrupación por obra y llamadas paralelas a TMDB (`process_results`, `resolve_titles`, `build_cache_key`).
  - Refactorizado `routes/search.py`: ahora actúa como un controlador HTTP delgado (Thin Controller) que orquesta validación, caché, llamada al servicio y paginación.
- **Contratos de Respuesta y Errores Consistentes**:
  - Implementado formato uniforme de errores: `{"error": message, "error_detail": {"code": code, "message": message}}`. Compatible tanto con clientes que esperan `data.error` como con clientes que requieren código de error tipificado.
- **Documentación Ampliada en README.md**:
  - Tabla de variables de entorno actualizada (`PROWLARR_SEARCH_LIMIT`, `OPENSUBTITLES_*`, `DELUGE_*`).
  - Nueva sección con tabla de endpoints de la API REST y formato de respuestas de error.
- **Pruebas y Cobertura**:
  - Creado `tests/test_validators.py` para verificar validaciones de parámetros de búsqueda y valores por defecto.
  - Retrocompatibilidad asegurada con alias de funciones en `routes/search.py` para tests existentes.
  - Suite completa: **98 tests pasando (100% verde)**.
- **Hoja de ruta actualizada**: Marcados como completados los 6 ítems de la *Etapa 3 — Mantenibilidad* en `media-tracker-hoja-de-ruta.md`.

### Qué quedó pendiente
- Avanzar con la *Etapa 4 — Seguridad y producción* (revisión de endpoints sensibles, auditoría SSRF/redirecciones y hardening).

### Decisiones tomadas
- Se mantuvieron alias de funciones históricas en `routes/search.py` (`_detect_spanish`, `_process_results`, `_resolve_titles`, etc.) apuntando a los nuevos módulos para garantizar retrocompatibilidad total sin romper tests existentes ni mocks.

---

## Sesión 2026-11-19 (cont.) — Implementación de la Etapa 4 de la Hoja de Ruta (Seguridad y Producción)

### Qué se completó
- **Autorización de Endpoints de Control (`routes/deluge.py`)**:
  - Incorporada capa de autorización opcional mediante `API_SECRET_TOKEN` (`X-Api-Token` o `Authorization: Bearer <token>`).
  - Previene que terceros o scripts ajenos disparen descargas en Deluge si la aplicación se expone más allá de la red de confianza.
- **Cabeceras de Seguridad HTTP y Límites de Carga (`app.py`)**:
  - Implementado hook `set_security_headers`:
    - `X-Content-Type-Options: nosniff`
    - `X-Frame-Options: SAMEORIGIN` (prevención de Clickjacking)
    - `X-XSS-Protection: 1; mode=block`
    - `Referrer-Policy: strict-origin-when-cross-origin`
  - Configurado límite global de tamaño de carga útil `MAX_CONTENT_LENGTH = 16 MB` para prevenir denegación de servicio por subida desmedida de ficheros.
  - Configurado `SECRET_KEY` desde variable de entorno con fallback documentado.
- **Validación de Configuración al Arrancar (`config.py`)**:
  - Implementada función `validate_config()` que comprueba formato y esquema de URLs críticas (`PROWLARR_URL`, `DELUGE_URL`, `REDIS_URL`) y acota `PROWLARR_SEARCH_LIMIT` entre 0 y 2000.
- **Pruebas de Seguridad**:
  - Se agregaron tests en `tests/test_security.py` verificando la presencia de las cabeceras de seguridad HTTP y el rechazo por falta o invalidez de token en `/api/deluge/add` (`403 Forbidden`).
  - Suite completa: **100 tests pasando (100% verde)**.
- **Hoja de ruta actualizada**: Marcados como completados los 6 ítems de la *Etapa 4 — Seguridad y producción* en `media-tracker-hoja-de-ruta.md`.

### Qué quedó pendiente
- Avanzar con la *Etapa 5 — Evolución del producto* (historial en LocalStorage en UI, filtros guardados, ordenamiento dinámico de resultados).

### Decisiones tomadas
- `API_SECRET_TOKEN` es opcional: si no se define, se mantiene el comportamiento predeterminado de red local sin fricción; si se define en `.env`, el endpoint `/api/deluge/add` queda estrictamente restringido con HTTP 403 ante llamadas no autorizadas.

---

## Sesión 2026-11-19 (cont.) — Implementación de la Etapa 5 de la Hoja de Ruta (Evolución del Producto y UX)

### Qué se completó
- **Historial de Búsquedas Recientes (`static/js/app.js` y `templates/index.html`)**:
  - Almacenamiento local seguro en `LocalStorage` (`mt_search_history`) de las últimas 8 consultas únicas.
  - Barra visual de etiquetas clickeables ("Recientes") que permite re-ejecutar búsquedas en un clic y botón para limpiar el historial.
- **Selector de Ordenamiento Dinámico de Resultados**:
  - Añadido selector en cabecera de resultados (`#sortSelector`) con múltiples modos de ordenamiento:
    - *Más Seeders* (modo predeterminado por salud del torrent).
    - *Más Recientes (Año descendente)*.
    - *Más Antiguas (Año ascendente)*.
    - *Título (A-Z)*.
  - Reordenamiento instantáneo en cliente sin necesidad de re-consultar al backend.
- **Accesibilidad y UX Móvil (a11y)**:
  - Atributos `aria-label` en inputs, selectores y botones de búsqueda y exportación.
  - Contenedores flexibles responsivos para pantallas estrechas.
- **Pruebas y Verificación**:
  - Validación de sintaxis JS con `node --check static/js/app.js` exitosa.
  - Suite de tests `pytest`: **100 tests pasando (100% verde)**.
- **Hoja de ruta actualizada**: Marcados como completados los 7 ítems de la *Etapa 5 — Evolución del producto* en `media-tracker-hoja-de-ruta.md`.

### Qué quedó pendiente
- Avanzar con la *Etapa 6 — Escalado según demanda* (métricas de rendimiento y observabilidad).

### Decisiones tomadas
- El historial y ordenamiento se resuelven del lado del cliente vía `LocalStorage` y arrays en memoria para velocidad instantánea sin añadir latencia de red ni carga de estado al servidor.

---

## Sesión 2026-11-19 (cont.) — Lanzador único (Media Tracker + FlareSolverr)

### Qué se completó
- Creado `iniciar-media-tracker.bat` en la raíz del proyecto.
- Verificada la estructura real antes de implementar: `dist\app.exe`, `flaresolverr\flaresolverr.exe` (carpeta en minúsculas) y el `.bat` previo `flaresolverr\iniciar-flaresolverr.bat`.
- El lanzador detecta su ubicación con `%~dp0`, configura `LANG=en-US` y `LOG_LEVEL=info`, arranca FlareSolverr en ventana propia y espera al health check de `http://127.0.0.1:8191/` (exige HTTP 200 y el texto `FlareSolverr is ready!`).
- Luego inicia `dist\app.exe`, espera a `http://127.0.0.1:5000/` y abre el navegador (la app no lo abría por sí sola; se confirmó que `app.py` no llama a `webbrowser`).
- Evita duplicados comprobando proceso (`tasklist`) y puerto (`netstat`) antes de cada arranque; muestra mensajes de error claros y NO cierra la ventana ante fallos (`pause`).
- README: nueva sección "Inicio con un solo clic (Windows)" con la estructura de carpetas y el flujo del lanzador.

### Pruebas realizadas
- 1.ª prueba: FlareSolverr levantó y respondió, pero Media Tracker agotó el tiempo de espera. Causa: `timeout /t` se saltea cuando la entrada está redirigida, por lo que el bucle de reintentos se consumía en milisegundos.
- Corrección: reemplazado `timeout` por `ping -n 3 127.0.0.1 >nul` en el bucle de espera (independiente de la consola).
- 2.ª prueba (arranque limpio): ambos servicios iniciados, health checks OK, navegador abierto, salida exitosa.
- 3.ª prueba (servicios ya activos): detectó ambos procesos, no creó instancias nuevas y abrió el navegador igualmente.
- Limpieza final: procesos terminados; solo queda un `TIME_WAIT` inofensivo en el puerto 5000.

### Qué quedó pendiente
- Nada de esta tarea. Sigue pendiente lo ya registrado: iniciar Prowlarr con indexers y asignarles el tag `flaresolverr`.

### Decisiones tomadas
- La carpeta real es `flaresolverr` (minúsculas), no `FlareSolverr`; se respetó para no romper rutas existentes.
- Se usa `%~dp0` con una variable `ROOT` intermedia y `/D "%ROOT%."` para evitar problemas de comillas finales en `start`.
- No se activó `LOG_HTML=true` (solo se usó en diagnóstico previo) y no se tocó la configuración de Prowlarr.
- Se mantuvo `LOG_LEVEL=info` y se usó el endpoint raíz de FlareSolverr como health check, verificado en sesiones anteriores (`{"msg":"FlareSolverr is ready!"}`).
- No se modificó código Python ni dependencias.

---

## Sesión 2026-11-19 (cont.) — Rebuild de `dist/app.exe`

### Qué se completó
- Verificado que el ejecutable estaba desactualizado: `dist\app.exe` era de las 12:52 mientras las fuentes (Etapas 1–5 de la hoja de ruta) llegaban hasta las 16:32.
- Recompilado con `python -m PyInstaller app.spec --noconfirm` (PyInstaller 6.22.3, Python 3.15.2). Nuevo `dist\app.exe`: 16.330.927 bytes, 16:55.
- Prueba de humo del nuevo EXE contra `http://127.0.0.1:5000/`:
  - `GET /` → 200, con `sortSelector` y la barra de búsquedas "Recientes"; cabecera `X-Content-Type-Options: nosniff` presente.
  - `GET /static/js/app.js` → 200, con `mt_search_history` y `escapeHtml`, y **0 `onclick=`**.
  - `GET /no-existe` → 404 con la página dinámica ("404 - No encontramos lo que buscas").
  - `GET /api/no-existe` → 404 en JSON.
  - `GET /api/search?query=test&category=invalido` → 400 con `error_detail` (`INVALID_CATEGORY`).
- Procesos de prueba terminados (`taskkill /F /IM app.exe /T`).

### Qué quedó pendiente
- Nada de esta tarea.

### Decisiones tomadas
- Se recompiló usando el `app.spec` existente; no hizo falta agregar `hiddenimports` ni dependencias nuevas porque los módulos nuevos (`utils/*`, `services/*`) son importados desde `app.py` y PyInstaller los resolvió.
- Se mantuvo `dist/app.exe` como artefacto ignorado por git: el cambio queda en el equipo, no en el repositorio.
- `Start-Process` desde PowerShell no sirvió para la prueba de humo (el onefile no respondió); se validó ejecutando el EXE directamente desde la shell, que es el mismo escenario del doble clic.

---

## Sesión 2026-11-19 (cont.) — Commit y push del lanzador

### Qué se completó
- Eliminados `instrucciones.md` y `media-tracker-hoja-de-ruta.md` (confirmado por el usuario); se conservan README.md, AGENTS.md y session_log.md.
- Agregada regla `flaresolverr/` a `.gitignore`.
- Commiteados: lanzador `.bat`, README, session_log, `.gitignore` y las dos borraciones. Pusheado a `origin/main`.

### Qué quedó pendiente
- Nada de esta tarea.

### Decisiones tomadas
- La carpeta `flaresolverr/` **no se versiona**: pesa ~842 MB y contiene dos archivos de 341 MB y 313 MB, por encima del límite de 100 MB por archivo de GitHub. Sigue siendo una instalación local, como cuando se instaló originalmente fuera del repositorio. El lanzador la requiere en la raíz del proyecto.
- No se usó Git LFS porque no está configurado en el repo y consumes cuota; requiere decisión explícita.
- `dist/app.exe` sigue ignorado (`dist/` en `.gitignore`), coherente con el resto de builds.

---

## Sesión 2026-11-20 — Estimación técnica de releases en la búsqueda

### Qué se completó
- **Opción A (estimación antes de descargar)** implementada de punta a punta, según el plan acordado en modo Plan:
  - Nuevo `utils/media_meta.py`: `parse_release_meta()` deduce del nombre del torrent fuente (REMUX/BluRay/WEB-DL/WEBRip), resolución, códec, bit depth, HDR/DV/HLG, formato de audio con canales, edición y grupo; `estimate_quality()` calcula Mbps y **bits por píxel (bpp)** a partir del tamaño y la duración, y devuelve veredicto (`Excelente`/`Muy buena`/`Correcta`/`Floja`/`Remux`/`Sin datos`), puntaje y flag de bitrate bajo.
  - `services/tmdb.py`: nuevo `_fetch_runtime()` (movie `runtime` / tv `episode_run_time[0]`) dentro del mismo caché de 24 h; si falla, devuelve `None` y la estimación queda "sin datos" sin romper la búsqueda.
  - `services/search_service.py`: cada torrent lleva un bloque `tech` con la estimación; nuevos filtros `min_bpp` y `sdr_only`; nuevo `sort_results()` aplicado **después de la caché** (un solo conjunto cacheado sirve para todos los criterios de orden, sin mutarlo).
  - `routes/search.py` y `utils/validators.py`: parámetros HTTP nuevos validados (`min_bpp` 0–1, `sdr_only`, `sort` ∈ seeders_desc/bpp_desc/year_desc/year_asc/title_asc) y incluidos en la clave de caché salvo `sort`.
  - `static/js/app.js` y `templates/index.html`: badges técnicos por torrent (fuente, bits, HDR, Mbps, bpp y chip de veredicto con color y tooltip), filtro "Calidad Mínima (bpp)", casilla "Solo SDR", opción de orden "Mejor Calidad (bpp)" (al cambiarlo se relanza la búsqueda para que la paginación server-side respete el orden) y nuevas columnas `Mbps/bpp/Veredicto` en la exportación CSV (y `tech` en JSON).
  - `README.md`: nueva característica documentada.
  - Tests nuevos: `tests/test_media_meta.py` (parseo + umbrales), 8 tests en `tests/test_search.py` (estimación en API, min_bpp, sdr_only, orden por bpp entre grupos y dentro del grupo, validaciones) y ajuste de `tests/test_tmdb.py` para aislar el test de reintento 429 del request extra de duración.
- **Verificación**: `python -m pytest -q` → **118 tests pasando**; `node --check static/js/app.js` → OK.
- **Recompilado `dist/app.exe`** con `python -m PyInstaller app.spec --noconfirm` (PyInstaller 6.22.3) para que el lanzador `.bat` use el código nuevo (sin dependencias nuevas, sin tocar `app.spec`). Prueba de humo del EXE: `GET /` → 200, `/static/js/app.js` → 200 con `filterMinBpp`, `filterSDR` y `bpp_desc`, y `/api/search?query=test&category=invalido` → 400. Proceso de prueba terminado.

### Qué quedó pendiente
- Nada de esta tarea. Sin implementar: verificación real con ffprobe (Opción B) y lectura de la biblioteca de Plex (Opción C), descartadas para esta iteración.

### Decisiones tomadas
- Defaults acordados: **fps fijo 24**, packs de temporada sin bpp confiable y **`10bit` solo si el nombre lo dice** (no se asume por tratarse de x265).
- Los archivos que no tienen resolución o duración se marcan "Sin datos" y **no se descartan** con `min_bpp`; se prefiere no perder resultados por falta de información.
- `REMUX` no se evalúa por bpp: es copia directa del disco y se marca como máxima calidad.
- `sdr_only` se aplica sobre la detección de HDR en el nombre; no modifica la opción existente `hdr` (que exige HDR).
- El orden por bpp usa el mayor `score` del grupo; el color del chip distingue niveles y todos los valores se presentan como **estimaciones**, nunca como mediciones del archivo.
- No se agregaron dependencias: `requirements.txt` queda intacto.

---

## Sesión 2026-11-21 — Rebuild de `dist/app.exe` con el diseño Filmoteca Editorial

### Qué se completó
- Verificado que `dist\app.exe` (20/11 12:28) no incluía el commit `9b3d59c` "feat(style): Aplicar diseño editorial Filmoteca Editorial": `templates/index.html` (14:49) y `static/js/app.js` (14:54) eran más nuevos.
- Cerrados dos procesos `dist\app.exe` que estaban en ejecución (`taskkill /F /IM app.exe /T`), necesario para que PyInstaller pudiera sobrescribir el ejecutable.
- Recompilado con `python -m PyInstaller app.spec --noconfirm` (PyInstaller 6.22.3, Python 3.15.2). Código de salida **0**. Sin módulos críticos faltantes en `warn-app.txt` (solo ausencias opcionales/de plataforma: `cryptography`, `boto3`, `pymongo`, `hiredis`, módulos POSIX, etc.).
- Nuevo `dist\app.exe`: **21/11/2026 17:03:10**, **16.339.921 bytes**.
- Prueba de humo del nuevo EXE contra `http://127.0.0.1:5000/` (Waitress en modo producción):
  - `GET /` → 200 (31.050 bytes) con los marcadores del diseño nuevo: "Precisión editorial y control de catálogo", "Archivo Cinematográfico", `text-headline-xl` y "DM Serif Display".
  - `GET /static/js/app.js` → 200 (61.323 bytes) con `filterMinBpp`, `filterSDR` y `bpp_desc`.
  - `GET /api/search?query=test&category=invalido` → 400 JSON con `error_detail.code = INVALID_CATEGORY`.
- Procesos de prueba terminados (`taskkill /F /IM app.exe /T`).
- `python -m pytest -q` → **118 tests pasando** (0 fallos, 1 warning preexistente de flask-limiter por almacenamiento en memoria).

### Qué quedó pendiente
- Nada de esta tarea.

### Decisiones tomadas
- Se reutilizó `app.spec` sin modificarlo: las plantillas, `assets/` y `static/` ya están en `datas`, y los imports nuevos se resolvieron solos.
- No se agregaron ni actualizaron dependencias.
- No se hizo commit: `dist/` está en `.gitignore` y el cambio del ejecutable es un artefacto local.

---

## Sesión 2026-11-21 (cont.) — Corrección de hallazgos de la revisión técnica y rebuild final

### Qué se completó
- Revisión técnica completa del proyecto (solo lectura): 1 crítico, 4 altos, 16 medios y varios bajos, con verificación real de `py_compile`, `pytest` (118 tests, 93 % de cobertura) y dependencias.
- **Crítico C1 corregido**: `sendToDeluge()` buscaba un `<i>` que no existe en el botón (usa `<span class="material-symbols-outlined">`) y lanzaba `TypeError` antes del `try`, inhabilitando "Enviar a Deluge". Ahora usa `data-role="deluge-icon"` con fallback al span, y todo el acceso al DOM quedó dentro de `try/catch/finally`.
- **Altos corregidos**:
  - A1: `allow_redirects=False` + `stream=True` en todas las descargas; cada `Location` se valida por separado (máx. 5 saltos); `_ip_is_blocked()` usa `ipaddress` y bloquea IPv4-mapeadas (`::ffff:169.254.169.254`), link-local, multicast y direcciones reservadas.
  - A2: descarga de `.torrent` con tope de 10 MB (`Content-Length` + conteo de chunks) y validación mínima de bencode.
  - A3: `utils/security.py` con `redact_secrets()` para logs; los handlers de Deluge, Prowlarr, TMDB y OpenSubtitles dejaron de devolver `str(e)` al cliente.
  - A4: `TMDB_MAX_RESOLUTIONS=40` y rediseño del lock anti-*stampede* con `Event` (los seguidores no retienen locks durante I/O).
- **Medios corregidos**: validación de cuerpo JSON (M1), `infoUrl` ya no se trata como magnet (M2), `release_date: None` (M3), lock y re-login del token de OpenSubtitles (M4), default `min_size_gb` unificado en 5 (M5), aviso visible cuando `min_bpp` no se pudo aplicar (M6), CSV injection (M7), `noopener,noreferrer` (M8), token de API con meta tag + `X-Api-Token` (M10), host configurable `127.0.0.1` y `debug=False` (M11), barra de progreso única (M13), estilos de filtro activo y `aria-pressed` (M14), `AbortController` + guardia de secuencia en "Cargar más" (M15), `Number(null)` corregido (M16).
- **Bajos corregidos**: imports muertos, desacoplamiento servicio→ruta mediante inyección de `resolver`, fuente única de códecs de audio en `utils/audio_patterns.py` (incluida la regex `dd\+`), cierre de la `Session` de Deluge, `hmac.compare_digest`, focus trap y `role="dialog"` en modales, botón de filtros sin `onclick` inline, ruta `/assets/<filename>` para la captura, textos de exportación ajustados a "resultados cargados" y clases `font-label-sm` → `text-label-sm`.
- **Tests nuevos**: `tests/test_review_fixes.py` (16 cases: IPv4-mapeada, cada redirección, redirección a magnet, `Content-Length` excesivo, contenido no-bencode, 5 variantes de body inválido, token de API, `redact_secrets`, `release_date: None`, `dd+`), `tests/frontend_review_check.js` (csvEscape real contra fórmulas) y dos tests en `test_frontend.py` (regresión C1 + csvEscape).
- **Verificación final**: `python -m pytest -q` → **134 tests pasando** (0 fallos, 1 warning preexistente de flask-limiter); `compileall` → OK; `node --check static/js/app.js` → OK.
- **Recompilado `dist/app.exe`**: 21/11/2026 17:31:24, **16.351.016 bytes**, con `python -m PyInstaller app.spec --noconfirm` (código de salida 0, sin módulos críticos faltantes). Humo test: `GET /` → 200 con `text-label-sm` y sin `font-label-sm`; `/static/js/app.js` → 200 con `data-role="deluge-icon"` y sin `querySelector('i')`; `/api/search?query=test&category=invalido` → 400. Procesos de prueba terminados.

### Qué quedó pendiente
- **M9**: CSP/HSTS y self-hosting de Tailwind/Google Fonts (requiere decisión de infra y agregar dependencias; se agregó únicamente `Cross-Origin-Opener-Policy: same-origin`, de bajo riesgo).
- Lock anti-*stampede* distribuido con Redis cuando haya más de un worker/proceso.
- Deduplicación de torrents entre indexers.
- Test de DOM real para `sendToDeluge` con jsdom (requeriría npm; se cubrió con test estático + revisión manual).
- Queda en el directorio el archivo sin versionar `build_log.txt`, generado por la redirección del output de PyInstaller.

### Decisiones tomadas
- No se cambió el mecanismo de autenticación de TMDB: la API v3 exige `api_key` en query string. Solo se redacta en logs y se evita devolver el error crudo al cliente.
- La política SSRF por defecto sigue permitiendo privados/loopback (`SSRF_ALLOW_PRIVATE_TARGETS=true`) porque Prowlarr y Deluge suelen correr en la misma máquina o en la LAN; los rangos de metadatos (link-local, IPv4-mapeadas, multicast, reservados) se bloquean siempre.
- Con `min_bpp` activo y sin duración de TMDB, el resultado **no se descarta**: se marca con la nota "bpp no disponible: filtro no aplicado" para no perder resultados por falta de datos.
- El token de API se inyecta en un `<meta>` renderizado por Jinja (autoescape activo) y se envía como `X-Api-Token`; si no está configurado, el header no se envía.
- No se agregaron dependencias: `requirements.txt` y `app.spec` quedaron intactos. No se hizo commit ni push.

---

## Sesión 2026-11-21 (cont.) — Diagnóstico y análisis del estado actual del proyecto

### Qué se completó
- **Auditoría completa del estado de la aplicación**:
  - **Suite de pruebas**: 134/134 tests pasando (100% verde en ~7-11 s).
  - **Cobertura de código**: 91% en total sobre el código de producción medido con `pytest-cov`.
  - **Sintaxis y compilación**: `node --check static/js/app.js` OK (sin errores de sintaxis); `compileall` en Python sin advertencias.
  - **Control de versiones (Git)**:
    - Rama activa: `feature/stitch-design-system` al día con `origin/feature/stitch-design-system`.
    - Diferencia con `main`: 2 commits por delante (`9b3d59c` con el diseño Filmoteca Editorial y `27384d7` con la resolución de 25+ correcciones técnicas y de seguridad).
    - Árbol de trabajo limpio (solo `build_log.txt` untracked, generado por PyInstaller).
  - **Servicios e infraestructura local**:
    - **Prowlarr**: Activo y escuchando en el puerto 9696 (PID 13432).
    - **Deluge**: Activo y escuchando en el puerto 8112 (PID 14084).
    - **FlareSolverr**: Detenido (puerto 8191 libre; operable vía `iniciar-media-tracker.bat` o standalone).
    - **Media Tracker**: Detenido (puerto 5000 libre; ejecutable `dist/app.exe` recompilado y listo).
  - **Configuración (`.env`)**: Variables críticas (`PROWLARR_*`, `TMDB_*`, `OPENSUBTITLES_*`, `DELUGE_*`) presentes y operativas.

### Qué quedó pendiente
- Integración/Merge de `feature/stitch-design-system` a `main` cuando se decida consolidar la release.
- Decidir si ignorar `build_log.txt` en `.gitignore` o eliminarlo.
- Iniciar FlareSolverr en caso de usar indexers de Prowlarr con Cloudflare activo.

### Decisiones tomadas
- Se mantuvieron inalteradas las fuentes y configuración durante el diagnóstico (modo auditoría de solo lectura).


## Sesión 2026-11-22 — Diagnóstico de rechazo de URL en Deluge

### Qué se completó
- Se rastreó el mensaje del navegador hasta `routes/deluge.py`: `_download_torrent()` devuelve "URL de descarga rechazada: el destino no está permitido." cuando la URL recibida inicialmente no pasa `_is_safe_remote_url()`.
- Se confirmó que la URL proviene de `magnetUrl` o `downloadUrl` de Prowlarr (`services/search_service.py`). Si es una URL web, el backend valida esquema y resolución DNS antes de hacer la petición.
- Se revisó la configuración: `PROWLARR_URL=http://localhost:9696`; `SSRF_ALLOW_PRIVATE_TARGETS` no aparece en `.env`, por lo que aplica el valor predeterminado `true` y permite localhost/LAN. Siguen bloqueados destinos link-local/reservados, multicast y no especificados; también se rechazan esquemas que no sean HTTP(S) o nombres no resolubles.

### Qué quedó pendiente
- Confirmar cuál URL de descarga devuelve el resultado de Prowlarr que falla. El mensaje por sí solo no incluye el hostname para no exponer detalles de la petición.
- No se modificó código ni configuración y no se ejecutaron tests; el usuario pidió diagnóstico.

### Decisiones tomadas
- Mantener las protecciones SSRF. Para aislar el caso, revisar el `downloadUrl` del resultado y su DNS/ruta; no desactivar el control sin identificar el destino.

## Sesión 2026-11-22 (cont.) — Diagnóstico más claro de URL bloqueada

### Qué se completó
- `routes/deluge.py` ahora identifica en el error si la URL inicial tiene un esquema no permitido, no tiene host, el host no resuelve por DNS o resuelve a una dirección bloqueada por seguridad.
- Se mantuvo intacta la política de seguridad: no se habilitaron rangos especiales ni se desactivó la validación SSRF.

### Qué quedó pendiente
- El destino concreto que devuelve Prowlarr no está disponible en el contexto, así que todavía no se puede corregir su URL/DNS o configuración del indexer.
- No se ejecutaron tests.

### Decisiones tomadas
- No permitir a ciegas destinos especiales: se conserva el rechazo y se hace el motivo visible para orientar la corrección específica.

## Sesión 2026-11-22 (cont.) — Recompilación de ejecutable

### Qué se completó
- Se reconstruyó `dist/app.exe` desde `app.spec` con PyInstaller 6.22.3; la compilación terminó correctamente.
- El ejecutable incluye la mejora de diagnóstico en la validación de URLs de Deluge.

### Qué quedó pendiente
- Probar el ejecutable en el equipo con el resultado de Prowlarr que antes fallaba.

### Decisiones tomadas
- Se usó el spec existente sin cambiar dependencias ni opciones de empaquetado.

## Sesión 2026-11-22 (cont.) — Diagnóstico de IP bloqueada

### Qué se completó
- El nuevo mensaje confirma que el host de descarga de Prowlarr resuelve a una dirección que la validación SSRF bloquea.
- Se amplió el detalle del error para mostrar el hostname y la IP resuelta, facilitando identificar si es un destino especial o una IP privada bloqueada por configuración.
- La instancia activa mantenía `dist/app.exe` bloqueado; sin detenerla, se compiló con éxito una versión diagnóstica en `dist-diagnostico/app.exe` usando `app.spec` y una ruta de salida separada.

### Qué quedó pendiente
- Cerrar la instancia actual del puerto 5000, arrancar la compilación diagnóstica con el directorio de trabajo del proyecto y volver a intentar el mismo resultado.
- Con el hostname/IP visibles se puede decidir si corregir el indexer/DNS o la política local sin abrir acceso a destinos no confiables.

### Decisiones tomadas
- No se permitió la IP bloqueada automáticamente. Se conserva el control SSRF y se revela la IP para corregir la causa concreta.

## Sesión 2026-11-22 (cont.) — Corrección de localhost IPv6 en SSRF

### Qué se completó
- El mensaje de prueba identificó el falso positivo: `localhost` resuelve a `::1`, y Python 3.15 marca esa dirección como loopback, privada y reservada.
- Se ajustó `_ip_is_blocked()` para evaluar loopback según `SSRF_ALLOW_PRIVATE_TARGETS` antes de la categoría `is_reserved`. Así `::1`/`127.0.0.1` se aceptan con la política predeterminada, mientras que link-local, unspecified, multicast y los demás rangos reservados siguen bloqueados.
- Se compiló correctamente `app.spec` a `dist-fix/app.exe`, ya que la instancia anterior mantiene ocupados los otros ejecutables.

### Qué quedó pendiente
- Cerrar la instancia actual y probar `dist-fix/app.exe` desde la carpeta del proyecto para que cargue `.env`.

### Decisiones tomadas
- Se permitió loopback explícitamente bajo la opción ya existente para privados/loopback; no se amplió esa opción a rangos reservados genéricos.
- No se ejecutaron tests.

### Aclaración posterior — URL HTTP de Prowlarr
- Se contrastó el análisis externo: no es correcto que el proyecto solo admita magnets puros ni que bloquee localhost por diseño.
- `services/search_service.py` selecciona `magnetUrl` o `downloadUrl`; `routes/deluge.py` descarga URLs HTTP(S), valida cada redirección y admite redirección final a magnet.
- El fallo de `localhost -> ::1` era un falso positivo de la clasificación `is_reserved` en Python 3.15; se corrigió en `dist-fix/app.exe`. La captura anterior corresponde a la compilación diagnóstica previa al arreglo.

## Sesión 2026-11-22 — Ajustes de contraste de texto

### Qué se completó
- Se elevó el contraste del placeholder de búsqueda (`/60` a `/80`; de aproximadamente 3.1:1 a 5.1:1 sobre el fondo de la búsqueda).
- Se cambiaron textos de error pálidos por el token oscuro `on-error-container` para mantener legibilidad sobre fondos claros.
- Se ajustaron badges de temporada completa y estados de éxito para usar pares de color diseñados para fondos claros.
- Se oscurecieron chips de calidad sin datos/bitrate, botones deshabilitados e iconos de estados vacíos; el texto gris del pie de la página de error pasó de `gray-500` a `gray-400`.

### Qué quedó pendiente
- Revisión visual en navegador cuando el servidor local esté iniciado. En esta sesión `localhost:5000` no respondió.

### Decisiones tomadas
- Se conservaron los colores y el tema general; se corrigieron combinaciones con contraste insuficiente.
- No se ejecutaron tests.

## Sesión 2026-11-22 (cont.) — Contraste, lanzador y compilación

### Qué se completó
- Se recompiló `dist/app.exe` desde `app.spec`; PyInstaller terminó correctamente con los cambios de contraste incluidos.
- Se ordenó `iniciar-media-tracker.bat`: se quitó el banner de compilación obsoleto, se describieron correctamente los reintentos de disponibilidad y se restauró la indicación para revisar los registros de FlareSolverr ante un fallo.
- Se conservaron los tiempos de espera ampliados que ya tenía el lanzador.

### Qué quedó pendiente
- No se ejecutaron tests ni se hizo una revisión visual del ejecutable.

### Decisiones tomadas
- El lanzador continúa iniciando `dist\\app.exe` desde la raíz del proyecto para cargar `.env` desde el directorio de trabajo.
