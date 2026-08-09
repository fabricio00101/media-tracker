
\# ESPECIFICACIÓN TÉCNICA DE IMPLEMENTACIÓN: MEDIA TRACKER

\#\# 1\. Arquitectura y Stack Tecnológico  
\* **\*\*Backend:\*\*** Flask 3.0.0 (WSGI Server: Waitress 3.0.2).  
\* **\*\*Caché:\*\*** Flask-Caching 2.3.1 (Estrategia: \`SimpleCache\` en memoria).  
\* **\*\*Procesamiento:\*\*** parse-torrent-title 2.8.2 (\`PTN\`).  
\* **\*\*Integraciones:\*\*** Prowlarr API (Búsqueda), TMDB API v3 (Metadatos), OpenSubtitles REST API v1 (Subtítulos), Deluge Web JSON-RPC (Descargas).  
\* **\*\*Frontend:\*\*** Single Page Application (SPA), HTML5, Tailwind CSS (CDN), Vanilla JS (Fetch API, LocalStorage).

\---

\#\# 2\. Estructura de Directorios Exacta  
El agente debe estructurar el workspace exactamente de la siguiente forma:  
\`\`\`text  
media-tracker/  
├── .gitignore  
├── README.md  
├── requirements.txt  
├── app.py  
├── app.spec  
├── assets/  
│   └── screenshot.png  
└── templates/  
    └── index.html

## **3\. Configuración del Entorno (.env)**

Crear un archivo .env en la raíz con las siguientes variables:

Fragmento de código  
PROWLARR\_URL=http://localhost:9696  
PROWLARR\_API\_KEY=  
TMDB\_API\_KEY=  
DELUGE\_URL=  
DELUGE\_PASSWORD=  
OPENSUBTITLES\_API\_KEY=  
OPENSUBTITLES\_USER=  
OPENSUBTITLES\_PASSWORD=  
FLASK\_ENV=production

## **4\. Requisitos de Dependencias (requirements.txt)**

Instalar estrictamente las siguientes dependencias base:

Plaintext  
Flask==3.0.0  
Werkzeug==3.1.3  
Jinja2==3.1.6  
waitress==3.0.2  
Flask-Caching==2.3.1  
requests==2.31.0  
python-dotenv==1.0.0  
parse-torrent-title==2.8.2

## **5\. Instrucciones Secuenciales de Implementación y Criterios de Verificación**

### **Paso 1: Inicialización del Entorno**

* **Instrucción:** Crear el entorno virtual, instalar requirements.txt y configurar el módulo de carga de variables de entorno (python-dotenv) en app.py. Validar la presencia obligatoria de PROWLARR\_API\_KEY al iniciar.  
* **Criterio de Verificación:** Al ejecutar python app.py, si PROWLARR\_API\_KEY está vacía, el sistema debe registrar un error crítico en el log (logging.error). Si está presente, el servidor debe iniciar sin excepciones en el puerto 5000\.

### **Paso 2: Endpoint de Búsqueda Base (/api/search)**

* **Instrucción:** Crear la ruta GET /api/search que acepte los parámetros query, category, min\_size\_gb, quality\_tag, hdr y hevc. Configurar requests.get hacia la API de Prowlarr (/api/v1/search) con un timeout estricto de 160 segundos para mitigar demoras de FlareSolverr.  
* **Criterio de Verificación:** Una petición HTTP manual a http://localhost:5000/api/search?query=test debe retornar un JSON con código de estado 200 OK conteniendo la lista de resultados mapeados desde Prowlarr, o 503/502 controlados si el servicio destino está caído.

### **Paso 3: Agrupación Inteligente e Integración de Metadatos (PTN \+ TMDB)**

* **Instrucción:** Implementar la función get\_tmdb\_info protegida por @cache.memoize(timeout=86400). Usar PTN.parse() para extraer el título limpio y el año de cada torrent. Agrupar los torrents en un diccionario cuya clave sea el ID de TMDB (si existe) o una clave local estandarizada ({titulo}\_{año}\_{es\_tv}). Marcar is\_full\_season=True en series si se detecta un pack de temporada completa. Ordenar los torrents internos por is\_full\_season y seeders de forma descendente.  
* **Criterio de Verificación:** Buscar un término con múltiples versiones. El JSON resultante debe consolidar los diferentes torrents bajo una estructura unificada de grupos (group\_info y lista de torrents), inyectando el póster oficial y la sinopsis en español.

### **Paso 4: Cliente de Descargas (Deluge JSON-RPC)**

* **Instrucción:** Crear la ruta POST /api/deluge/add que reciba un objeto JSON con la clave magnet. Implementar un flujo con requests.Session() que ejecute el método RPC auth.login utilizando DELUGE\_PASSWORD. Si el enlace no empieza con magnet:, resolver los redireccionamientos HTTP de Prowlarr y codificar el archivo .torrent resultante en Base64 para enviarlo mediante core.add\_torrent\_file. Si es un magnet directo, usar core.add\_torrent\_magnet.  
* **Criterio de Verificación:** Enviar un POST válido a /api/deluge/add. La respuesta debe ser 200 OK con {"message": "Añadido exitosamente a Deluge."} y el torrent debe aparecer listado en la interfaz de Deluge de forma inmediata.

### **Paso 5: Módulo de Subtítulos (OpenSubtitles REST API v1)**

* **Instrucción:** Implementar GET /api/subtitles/search?tmdb\_id=... apuntando a api.opensubtitles.com/api/v1/subtitles filtrando por lenguajes es,es-mx. Implementar GET /api/subtitles/download?file\_id=... que obtenga un token persistente mediante el endpoint /api/v1/login utilizando las credenciales del .env y retorne el enlace de descarga final (link). Añadir obligatoriamente la cabecera User-Agent: RastreadorTorrents/1.0 en todas las peticiones.  
* **Criterio de Verificación:** Invocar el endpoint de búsqueda con un ID válido de TMDB. Debe retornar la lista de archivos de subtítulos disponibles con sus metadatos (file\_id, language, ratings). Invocar el endpoint de descarga debe devolver un enlace directo de descarga de OpenSubtitles.

### **Paso 6: Interfaz de Usuario Monopágina (templates/index.html)**

* **Instrucción:** Construir una interfaz oscura basada en Tailwind CSS. Configurar filtros avanzados dinámicos de categoría, tamaño, idiomas locales (Latino, Castellano, Sub, Otros) y etiquetas especiales (HDR, HEVC). Implementar lógica Vanilla JS para procesar el formulario de forma asíncrona, capturar errores de red con reintentos automáticos (fetchWithRetry), renderizar tarjetas interactivas expandibles (\<details\>) con paginación manual por lotes (16 resultados por página) y persistir la colección de favoritos en el objeto localStorage bajo la clave mt\_favorites.  
* **Criterio de Verificación:** Al realizar una búsqueda, la interfaz debe mostrar un spinner de carga, ocultar los errores previos y renderizar exactamente un máximo de 16 tarjetas. Presionar "Cargar Más" debe anexar el siguiente lote de resultados sin reconstruir el DOM existente. Al recargar la página, los elementos guardados en "Mi Colección Guardada" deben mantenerse intactos.

### **Paso 7: Empaquetamiento de Distribución (app.spec)**

* **Instrucción:** Configurar el archivo de especificación de PyInstaller app.spec para empaquetar la aplicación en modo consola. Declarar explícitamente la inclusión de las carpetas estáticas en el parámetro datas=\[('templates', 'templates'), ('assets', 'assets')\] e inyectar de forma forzada los módulos dinámicos dentro de hiddenimports=\['flask\_caching', 'PTN'\].  
* **Criterio de Verificación:** Ejecutar el comando pyinstaller app.spec. El proceso debe finalizar con código de salida 0 sin advertencias de dependencias críticas ausentes, generando un archivo ejecutable funcional dentro de la carpeta de distribución dist/.