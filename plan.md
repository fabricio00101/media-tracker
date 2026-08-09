# Plan de Mejoras — Media Tracker

## 🔴 Seguridad (Crítico)

### 1. `.env` con credenciales reales committeado
- **Problema:** El `.gitignore` excluye `.env`, pero el archivo existe con API keys reales (Prowlarr, TMDB, OpenSubtitles). Si fue pusheado alguna vez, las credenciales están en el historial de git.
- **Solución:**
  - Crear `.env.example` con valores vacíos/plantilla.
  - Rotar todas las API keys comprometidas.
  - Verificar el historial de git con `git log --all --full-history -- .env` para confirmar si fue committeado.

### 2. XSS en magnet URLs
- **Problema:** En `templates/index.html:770-779`, los magnets se insertan en el DOM con `replace(/'/g, "\\'")` para escapar comillas simples. Esto es bypassable si un título contiene secuencias como `</script>` o eventos HTML.
- **Solución:**
  - No insertar magnets directamente en atributos `onclick`.
  - Usar `data-` attributes + event listeners en JS vanilla en vez de `onclick` inline.
  - Aplicar sanitización con una función helper que escape HTML entities.

### 3. Sin rate limiting
- **Problema:** No hay protección contra abuso en los endpoints `/api/search` y `/api/subtitles/*`. Un atacante podría hacer flooding de requests a Prowlarr o OpenSubtitles, agotando cuotas.
- **Solución:**
  - Integrar `flask-limiter` con una regla base (ej: 30 req/min por IP en búsqueda, 10 req/min en subtítulos).
  - Actualizar `requirements.txt` con la nueva dependencia.

---

## 🟡 Arquitectura y Calidad del Código

### 4. `app.py` monolítico (572 líneas)
- **Problema:** Todo el backend está en un solo archivo: routing, lógica de negocio, clientes HTTP, parsing. Dificulta mantenimiento y testing.
- **Solución:** Reestructurar en módulos:
  ```
  app.py                 → Solo init de Flask + registro de blueprints
  routes/
    __init__.py
    search.py            → Blueprint de /api/search
    subtitles.py         → Blueprint de /api/subtitles/*
    deluge.py            → Blueprint de /api/deluge/*
  services/
    __init__.py
    tmdb.py              → get_tmdb_info()
    grouping.py          → Lógica de agrupación con PTN
    subtitles.py         → get_opensubtitles_token(), lógica de subtítulos
  clients/
    __init__.py
    prowlarr.py          → Cliente HTTP para Prowlarr
    deluge.py            → Cliente JSON-RPC para Deluge
    opensubtitles.py     → Cliente REST para OpenSubtitles
  ```

### 5. `index.html` monolítico (963 líneas)
- **Problema:** HTML + todo el JS inline (~560 líneas de JavaScript). Dificulta debugging y mantenimiento.
- **Solución:**
  - Mover todo el JS a `static/js/app.js`.
  - Mantener en `index.html` solo HTML + CSS + la línea `<script src="/static/js/app.js"></script>`.
  - Actualizar `app.spec` para incluir `static/` en `datas`.

### 6. Caché inconsistente
- **Problema:** `get_opensubtitles_token` usa timeout `86000` (línea 343) y `get_tmdb_info` usa `86400` (línea 45). El token de OpenSubtitles expira en ~24h pero no se valida expiración.
- **Solución:**
  - Unificar timeouts de caché en constantes al inicio del archivo: `CACHE_24H = 86400`, `CACHE_1H = 3600`, `CACHE_5MIN = 300`.
  - Agregar validación de expiración en el token de OpenSubtitles (guardar timestamp + token, verificar `time.time() - timestamp < 82800` antes de reusar).

### 7. Excepciones silenciadas
- **Problema:** `get_tmdb_info` (líneas 86-87): `except Exception: pass` sin logging. Si TMDB falla, no hay forma de diagnosticar.
- **Solución:**
  - Agregar `logging.warning(f"Error consultando TMDB para '{query_title}': {e}")` en el bloque except.

### 8. `import base64` dentro de una función
- **Problema:** Línea 490: el import está dentro del bloque `else` de `add_to_deluge`. Es un code smell y afecta rendimiento marginalmente.
- **Solución:** Mover `import base64` al tope del archivo con los otros imports.

---

## 🟠 Funcionalidad

### 9. No hay tests
- **Problema:** `AGENTS.md` menciona `python -m pytest` pero no existe ningún archivo de test. No hay forma automatizada de validar que los flujos no se rompen.
- **Solución:**
  - Crear `tests/` con estructura:
    ```
    tests/
      __init__.py
      conftest.py          → Fixtures: Flask test client, mocks de APIs
      test_search.py       → Tests de /api/search (mock Prowlarr)
      test_tmdb.py         → Tests de get_tmdb_info (mock requests)
      test_subtitles.py    → Tests de /api/subtitles/* (mock OpenSubtitles)
      test_deluge.py       → Tests de /api/deluge/add (mock Deluge RPC)
    ```
  - Usar `unittest.mock.patch` para simular respuestas de APIs externas.
  - Mockear `requests.get`/`requests.post` para no depender de servicios reales.

### 10. `.env.example` no existe
- **Problema:** El README lo referencia pero no está en el repo. Dificulta la instalación para nuevos usuarios.
- **Solución:** Crear `.env.example`:
  ```
  PROWLARR_URL=http://localhost:9696
  PROWLARR_API_KEY=
  TMDB_API_KEY=
  DELUGE_URL=
  DELUGE_PASSWORD=
  OPENSUBTITLES_API_KEY=
  OPENSUBTITLES_USER=
  OPENSUBTITLES_PASSWORD=
  FLASK_ENV=production
  ```

### 11. Búsqueda sin paginación server-side
- **Problema:** La búsqueda carga todos los resultados de Prowlarr de una. Con indexadores grandes, esto puede ser muy lento y consumir mucha memoria.
- **Solución (futuro):**
  - Agregar parámetros `page` y `per_page` al endpoint `/api/search`.
  - Implementar paginación en el cliente Prowlarr (`offset`/`limit`).
  - Retornar metadata de paginación (`total_results`, `next_page`).

---

## 🔵 Frontend / UX

### 12. Typo en footer
- **Problema:** Línea 388 de `index.html`: `containter` en vez de `container`.
- **Solución:** Corregir a `container`.

### 13. Filtros de idioma no sincronizados con backend
- **Problema:** Los checkboxes de idioma (Latino, Castellano, Sub, Otros) filtran en el frontend pero el backend también retorna `spanish_support`. Si Prowlarr retorna 1000 resultados, se descargan todos y se filtran localmente, desperdiciando ancho de banda.
- **Solución:**
  - Agregar parámetro `lang_filter` al endpoint `/api/search` (valores: `latino`, `castellano`, `sub`, `all`).
  - Filtrar en el backend antes de agrupar, para reducir payloads innecesarios.
  - Mantener el filtro local como fallback para edge cases.

### 14. Sin timeout en fetch de subtítulos
- **Problema:** El modal de subtítulos muestra un spinner pero no hay timeout si la API tarda demasiado. El usuario queda colgado indefinidamente.
- **solución:**
  - Agregar `AbortController` con timeout de 15 segundos en el `fetch` de subtítulos.
  - Mostrar mensaje de error específico si el timeout se activa.

---

## Plan de Ejecución Propuesto

| Fase | Pasos | Esfuerzo | Dependencias |
|------|-------|----------|--------------|
| **Fase 1 — Seguridad** | Crear `.env.example`, rotar credenciales, fix XSS, agregar rate limiting | Bajo-Medio | Ninguna |
| **Fase 2 — Limpieza** | Mover JS a `static/js/`, fix typo, mover import, fix caché, agregar logging | Bajo | Ninguna |
| **Fase 3 — Tests** | Crear estructura `tests/`, tests de cada endpoint con mocks | Medio | Fase 2 (para imports limpios) |
| **Fase 4 — Refactor** | Separar `app.py` en blueprints y servicios | Alto | Fase 2 + Fase 3 |
| **Fase 5 — Funcionalidad** | Filtros de idioma server-side, paginación server-side | Medio-Alto | Fase 4 |

---

## Decisiones Pendientes

- [ ] ¿Rotar todas las API keys o solo las que estuvieron en el historial de git?
- [ ] ¿Usar `flask-limiter` o una implementación custom de rate limiting?
- [ ] ¿Priorizar tests o refactor de módulos primero?
- [ ] ¿Mover a Flask Blueprints o mantener monolítico con funciones separadas?
