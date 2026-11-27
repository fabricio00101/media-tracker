# Media Tracker - Buscador de Alta Fidelidad

Una aplicación web para buscar películas, series y documentales mediante una instancia de [Prowlarr](https://github.com/Prowlarr/Prowlarr). Agrupa releases, obtiene metadatos de TMDB y permite enviar magnets o archivos `.torrent` a Deluge.

## ✨ Características Principales

- **Filtros Avanzados**: Búsqueda exclusiva por categorías (Películas, Series, Documentales o Todos) y filtro visual rápido por calidad gráfica (1080p, 4K UHD, REMUX, WEBRip).
- **Agrupación Inteligente**: En lugar de mostrar cientos de torrents desordenados, la aplicación (gracias a `parse-torrent-title`) agrupa todas las variantes de una misma obra bajo una única tarjeta expandible.
- **Integración con TMDB**: Automáticamente obtiene el póster oficial, año de lanzamiento y sinopsis en español de la base de datos de TMDB para presentar las obras.
- **Temporadas Completas Destacadas**: Detección de packs de temporada (`is_full_season`) y prioridad dentro de cada grupo.
- **Copiar Magnet con un Clic**: Interfaz sin fricciones. Un solo botón para abrir el Torrent o un botón dedicado para copiar el Magnet al portapapeles y pasarlo por WhatsApp/Telegram.
- **Soporte para FlareSolverr**: Prowlarr puede usar FlareSolverr como proxy para indexadores que lo requieran. El timeout de búsqueda de Prowlarr es configurable y su valor predeterminado es 300 segundos.
- **Indicadores de Idioma**: Detección inteligente si el archivo contiene audio "Latino", "Castellano" o "Subtitulado".
- **Estimación Técnica por Release**: A partir del nombre del torrent y de la duración real de TMDB se estiman fuente (REMUX/BluRay/WEB-DL), códec, bits de color, HDR, formato de audio, bitrate y **bits por píxel (bpp)**, con un veredicto de calidad (Excelente / Muy buena / Correcta / Floja). Permite filtrar por calidad mínima, excluir HDR y ordenar por mejor calidad sin descargar nada.
- **Colección e historial locales**: Los favoritos y las búsquedas recientes se guardan en el `localStorage` del navegador.

## 🚀 Requisitos

Necesitarás tener instalado y corriendo en tu equipo local:

- Python 3.10 o superior.
- [Prowlarr](https://github.com/Prowlarr/Prowlarr) (Corriendo por defecto en el puerto `9696`).
- _(Opcional pero Recomendado)_ [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) para acceder a indexadores protegidos por Cloudflare como 1337x.

## 🛠 Instalación y Uso

1. **Clonar este repositorio:**

   ```bash
   git clone https://github.com/fabricio00101/media-tracker.git
   cd media-tracker
   ```

2. **Crear y activar un entorno virtual (opcional pero recomendado):**

   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   ```

3. **Instalar dependencias:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar las variables de entorno:**
   Copia `.env.example` como `.env` en la raíz y completa las credenciales de los servicios que quieras usar. En PowerShell:

   ```powershell
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   ```

   `PROWLARR_API_KEY` es necesaria para buscar. TMDB, OpenSubtitles, Deluge y Redis son opcionales; las variables disponibles y sus valores predeterminados están documentados en `.env.example`. Antes de exponer la aplicación en una red, configura `SECRET_KEY` y `API_SECRET_TOKEN`.

5. **Ajustes adicionales de Prowlarr (recomendado):**
   - Asegúrate de asignar FlareSolverr como proxy en Prowlarr desde _Settings > Indexers_, en caso de indexadores caidos o bloqueados por CF.

6. **Ejecutar el servidor web:**

   ```bash
   python app.py
   ```

   Por defecto escucha en `127.0.0.1:5000`. `HOST` y `PORT` permiten cambiar la dirección y el puerto; con `FLASK_ENV=production` usa Waitress.

7. **Abrir la aplicación:** visita [http://localhost:5000](http://localhost:5000).

## 🐳 Despliegue con Docker (opcional)

El proyecto incluye un `Dockerfile` y un `docker-compose.yml` listos para producción. El compose levanta la app con **Waitress multi-hilo** y un **Redis** para caché y rate-limiting persistentes.

```powershell
# 1. Copiar .env.example solo si todavía no existe .env
if (-not (Test-Path .env)) { Copy-Item .env.example .env }

# 2. Levantar app + Redis
docker compose up -d --build
```

La aplicación quedará disponible en [http://localhost:5000](http://localhost:5000). Redis almacena el estado de caché y de los límites de peticiones, por lo que sobrevive a reinicios y funciona correctamente con múltiples hilos.

## 🖥️ Ejecutable para Windows (PyInstaller)

El proyecto puede empaquetarse como un único `app.exe` que incluye `templates`, `static` y `assets`.

```bash
pip install pyinstaller
python -m PyInstaller app.spec --noconfirm
```

El ejecutable se genera en `dist/app.exe`.

> **Importante:** el `.exe` lee las claves del archivo `.env` ubicado en el **directorio de trabajo** desde donde se ejecuta. Si lo lanzás desde `dist/`, colocá ahí tu `.env` (por ejemplo `dist/.env`).

### Inicio con un solo clic (Windows)

Hacé doble clic en `iniciar-media-tracker.bat`, en la raíz del proyecto. La estructura esperada es:

```text
Media-Tracker/
├── dist/app.exe
├── flaresolverr/flaresolverr.exe
└── iniciar-media-tracker.bat
```

El lanzador usa rutas relativas, inicia FlareSolverr en una ventana propia con `LANG=en-US` y `LOG_LEVEL=info` (dejá esa ventana abierta para consultar los registros), espera a que `http://127.0.0.1:8191/` responda `FlareSolverr is ready!`, y recién después arranca `dist\app.exe`. Cuando `http://127.0.0.1:5000/` responde, abre el navegador. Si alguno de los dos servicios ya está ejecutándose, no inicia otra instancia.

## 📚 Endpoints de la API REST

| Método | Endpoint | Parámetros Principales | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/search` | `query`, `category`, `min_size_gb`, `quality_tag`, `hdr`, `hevc`, `sdr_only`, `lang_filter`, `min_bpp`, `sort`, `page`, `per_page` | Metabúsqueda, agrupación de torrents, metadatos TMDB y paginación de grupos. |
| `GET` | `/api/subtitles/search` | `tmdb_id`, `media_type`, `season`, `episode` | Búsqueda de subtítulos en OpenSubtitles v3 para películas y series. |
| `GET` | `/api/subtitles/download` | `file_id` | Obtiene el enlace de descarga oficial para el archivo de subtítulo. |
| `POST` | `/api/deluge/add` | Body JSON: `{"magnet": "magnet:?..."}` (también acepta una URL HTTP(S) de un `.torrent`) | Envía un magnet o un `.torrent` directamente a la cola de Deluge Web UI. |

La búsqueda devuelve `results` junto con `page`, `per_page`, `total_groups`, `total_torrents` y `has_more`. `per_page` vale 16 por defecto y se limita a 50. La paginación se aplica a los grupos después de consultar y procesar la respuesta de Prowlarr; no reduce la cantidad solicitada a Prowlarr. `PROWLARR_SEARCH_LIMIT` controla esa cantidad (500 por defecto; 0 significa sin límite).

### Formato de errores

Los endpoints devuelven JSON en caso de error. `/api/search` incluye además `error_detail` con un código y un mensaje; los demás endpoints pueden devolver solo `error`. Por ejemplo:

```json
{
  "error": "Mensaje legible del error",
  "error_detail": {
    "code": "CODIGO_ERROR_ESTANDARIZADO",
    "message": "Detalle técnico o validación"
  }
}
```

## 🧩 Arquitectura y pruebas

- `app.py` configura Flask, extensiones y cabeceras; `routes/` contiene los blueprints HTTP.
- `services/` implementa las integraciones y el procesamiento; `utils/` contiene validadores y lógica compartida.
- `templates/index.html` sirve la interfaz y `static/js/app.js` implementa la lógica del navegador.
- La caché y los límites de peticiones pueden usar Redis mediante `REDIS_URL`; sin Redis funcionan en memoria y no se comparten entre procesos.
- Ejecuta las pruebas con `python -m pytest`.

La arquitectura, configuración y comportamiento detallados están descritos en [`spec.md`](spec.md).

## 📸 Capturas de Pantalla

![Página de Resultados de Media Tracker](assets/screenshot.png)

---

_Hecho para amantes del cine. Ningún Torrent está hosteado en este proyecto, solo se conectan APIs bajo la responsabilidad del usuario._
