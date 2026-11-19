# Media Tracker --- Correcciones y hoja de ruta de evolución

**Repositorio:**
[fabricio00101/media-tracker](https://github.com/fabricio00101/media-tracker)\
**Documento:** revisión técnica y propuestas para llevar la aplicación
al siguiente nivel\
**Alcance:** recomendaciones basadas en la revisión estática de
`routes/search.py`, `services/tmdb.py`, `config.py` y
`tests/test_search.py`.

> Este documento es una hoja de ruta, no un informe de cambios ya
> implementados. Antes de dar por resuelto un punto, hay que modificar
> el código, ejecutar las pruebas y comprobar el comportamiento de la
> aplicación.

------------------------------------------------------------------------

## 1. Objetivo general

Consolidar Media Tracker como una aplicación estable, mantenible y
preparada para crecer. La prioridad no es agregar funciones
indiscriminadamente, sino mejorar primero la confiabilidad del buscador
y después evolucionar la arquitectura, la experiencia de uso, la
observabilidad y el despliegue.

La estrategia propuesta tiene cuatro objetivos:

1.  **Robustez:** tolerar entradas inválidas, respuestas inesperadas y
    fallos de servicios externos.
2.  **Escalabilidad:** controlar correctamente la concurrencia, el caché
    y el volumen de trabajo.
3.  **Mantenibilidad:** separar responsabilidades y facilitar las
    pruebas.
4.  **Producto:** mejorar la experiencia de búsqueda y convertir la
    aplicación en un proyecto sólido para portfolio.

## 2. Correcciones prioritarias

### 2.1. Corregir el ciclo de vida de los locks de búsqueda

**Archivo:** `routes/search.py`\
**Prioridad:** alta

La función `_get_inflight_lock()` mantiene un diccionario de locks por
clave de caché. Su objetivo es evitar que varias solicitudes iguales
consulten Prowlarr simultáneamente.

La limpieza actual elimina locks que en ese instante no están adquiridos
(`lock.locked() == False`). Sin embargo, otro hilo podría haber obtenido
una referencia al lock y todavía no haberlo adquirido. Si se elimina del
diccionario y se crea otro lock para la misma clave, ambos hilos podrían
terminar trabajando en paralelo.

**Recomendación:**

-   No eliminar locks únicamente comprobando `locked()`.
-   Administrar cada clave con un contador de referencias o una
    estructura equivalente que permita saber si algún hilo todavía
    utiliza ese lock.
-   Eliminar una entrada solamente cuando no haya hilos esperando ni
    utilizando el lock.
-   Mantener la sección crítica del diccionario protegida por
    `_inflight_guard`.
-   Añadir una prueba concurrente que demuestre que varias solicitudes
    idénticas producen una sola consulta a Prowlarr.

**Criterio de aceptación:** ante varias solicitudes simultáneas con los
mismos parámetros y una caché vacía, se ejecuta una sola consulta a
Prowlarr.

### 2.2. Validar correctamente los parámetros de búsqueda

**Archivo:** `routes/search.py`\
**Prioridad:** alta

La conversión actual de `min_size_gb` captura `ValueError`, pero no
controla valores como `nan`, `inf` o números negativos.

**Recomendación:**

-   Usar `math.isfinite()` para rechazar `NaN` e infinitos.
-   Definir un rango permitido para el tamaño mínimo. Como punto de
    partida, podría ser de 0 a 1000 GB, ajustándolo al uso real.
-   Definir una longitud mínima y máxima para `query`.
-   Limitar la longitud de `quality_tag`.
-   Validar `category` contra una lista permitida (`all`, `movies`,
    `tv`, `docs`).
-   Validar los filtros de idioma contra valores conocidos.
-   Devolver HTTP 400 con mensajes claros cuando los parámetros sean
    inválidos.
-   Evitar que valores desconocidos se interpreten silenciosamente como
    filtros válidos.

**Criterio de aceptación:** los parámetros inválidos se rechazan de
forma consistente y no generan excepciones internas ni búsquedas
inesperadas.

### 2.3. Mejorar la selección de resultados de TMDB

**Archivo:** `services/tmdb.py`\
**Prioridad:** alta

Actualmente `get_tmdb_info()` selecciona siempre el primer elemento de
`results`. Esto puede asociar una película o serie con un póster,
sinopsis o año incorrectos cuando existen títulos similares, remakes o
traducciones.

**Recomendación:**

Crear una función que puntúe los candidatos de TMDB usando:

1.  Coincidencia del título normalizado.
2.  Coincidencia del año, cuando esté disponible.
3.  Tipo de contenido (película o serie).
4.  Coincidencia con el título original y los títulos localizados.
5.  Penalización para candidatos con diferencias importantes.

No conviene depender exclusivamente de una comparación literal: los
títulos pueden variar por traducción, puntuación o transliteración. Si
ningún candidato alcanza un umbral razonable, es preferible devolver
información local antes que mostrar metadatos incorrectos.

También conviene:

-   Mantener `media_type` en todos los resultados.
-   Añadir pruebas con remakes y títulos repetidos.
-   Comprobar el comportamiento cuando TMDB no devuelve resultados.
-   Evitar guardar en caché una selección incorrecta durante 24 horas
    sin una estrategia de invalidación.

**Criterio de aceptación:** los casos ambiguos se resuelven con una
coincidencia razonable o se muestran sin metadatos de TMDB; nunca se
fuerza arbitrariamente el primer resultado.

### 2.4. Evitar que se agrupen películas y series diferentes

**Archivo:** `routes/search.py`\
**Prioridad:** alta

La clave de agrupación de TMDB utiliza título y año, pero no incluye el
tipo de contenido. Dos resultados con igual título y año podrían
terminar en el mismo grupo.

**Recomendación:**

Incluir `media_type` en la clave de agrupación, por ejemplo:

``` python
media_type = info.get("media_type", "movie")
group_key = (
    f"tmdb_{media_type}_{info['title'].lower()}_"
    f"{info.get('year', '')}"
)
```

La clave definitiva también debería normalizar el título de forma
consistente.

**Criterio de aceptación:** una película y una serie con igual nombre y
año permanecen en grupos separados.

### 2.5. Limitar globalmente las consultas a TMDB

**Archivo:** `routes/search.py` o un servicio dedicado\
**Prioridad:** media-alta

`TMDB_MAX_WORKERS = 6` limita los hilos por búsqueda, no el total de la
aplicación. Si varias búsquedas se ejecutan simultáneamente, la cantidad
total de consultas concurrentes puede multiplicarse.

**Recomendación:**

-   Incorporar un `threading.Semaphore` compartido por la aplicación
    para limitar las consultas concurrentes a TMDB.
-   Si también se necesita controlar solicitudes por intervalo de
    tiempo, implementar un rate limiter específico.
-   Para despliegues con varios procesos o contenedores, recordar que un
    semáforo en memoria no es global: usar un mecanismo compartido, por
    ejemplo Redis, si se requiere un límite común.
-   Manejar explícitamente respuestas HTTP 429 y aplicar espera
    incremental (*backoff*) con un máximo razonable.
-   Mantener timeouts configurables.

**Criterio de aceptación:** la aplicación respeta un límite de
concurrencia definido incluso cuando recibe varias búsquedas diferentes
al mismo tiempo.

### 2.6. Validar las respuestas de Prowlarr

**Archivo:** `routes/search.py`\
**Prioridad:** media-alta

`_fetch_prowlarr()` contempla respuestas en forma de lista y objetos con
`Results`, pero no comprueba completamente el tipo ni la estructura de
los datos.

**Recomendación:**

-   Verificar que la respuesta JSON sea una lista o un objeto con
    `Results` de tipo lista.
-   Descartar elementos que no sean diccionarios.
-   Validar los campos usados por el procesamiento: título, tamaño,
    seeders, indexer y URLs.
-   Convertir y validar los valores numéricos antes de operar con ellos.
-   Tratar los campos opcionales como opcionales, sin asumir que siempre
    existen.
-   Registrar internamente respuestas inesperadas sin exponer trazas al
    usuario.

**Criterio de aceptación:** un elemento malformado no derriba toda la
búsqueda y una respuesta inválida de Prowlarr genera un error
controlado.

### 2.7. Mejorar la detección de idiomas y audio

**Archivo:** `routes/search.py`\
**Prioridad:** media

La detección actual busca subcadenas dentro del título. Etiquetas cortas
como `lat` pueden coincidir accidentalmente con partes de otras
palabras.

**Recomendación:**

-   Normalizar títulos y separar tokens mediante delimitadores
    habituales.
-   Utilizar expresiones regulares con límites de palabra o patrones
    específicos para etiquetas.
-   Mantener una lista documentada de variantes conocidas (`LAT`,
    `LATAM`, `ES-LAT`, `ES-ES`, etc.).
-   Añadir pruebas para falsos positivos y formatos de nombres reales.
-   No afirmar que un idioma está presente si la etiqueta es ambigua.

**Criterio de aceptación:** los filtros de idioma y audio producen
resultados reproducibles y cuentan con pruebas para sus principales
variantes.

------------------------------------------------------------------------

## 3. Mejoras de arquitectura

Estas tareas conviene abordarlas después de estabilizar el
comportamiento actual. No es necesario hacer una gran refactorización en
un único cambio.

### 3.1. Separar la lógica de búsqueda de las rutas Flask

Actualmente `routes/search.py` contiene el endpoint, la consulta a
Prowlarr, el procesamiento, la agrupación, la resolución de TMDB y la
paginación.

**Estructura propuesta:**

``` text
routes/
    search.py
    subtitles.py
    deluge.py

services/
    search_service.py
    prowlarr_service.py
    tmdb_service.py
    subtitles_service.py
    deluge_service.py

utils/
    title_parser.py
    language_detector.py
    validators.py

tests/
    unit/
    integration/
```

Responsabilidades:

-   `routes/search.py`: recibir parámetros, validar la petición HTTP y
    construir la respuesta.
-   `search_service.py`: coordinar el flujo de búsqueda y agrupación.
-   `prowlarr_service.py`: comunicarse con Prowlarr.
-   `tmdb_service.py`: buscar y seleccionar metadatos.
-   `title_parser.py`: interpretar nombres de archivos o releases.
-   `language_detector.py`: detectar idioma y audio.
-   `validators.py`: centralizar validaciones reutilizables.

La refactorización debe preservar primero el comportamiento existente.
Conviene mover una responsabilidad por vez y ejecutar las pruebas
después de cada cambio.

### 3.2. Centralizar la configuración

Mantener las variables de entorno en `config.py` es correcto, pero
conviene validar la configuración al iniciar la aplicación.

Recomendaciones:

-   Definir valores mínimos y máximos para variables numéricas.
-   Comprobar que las URLs tengan un formato válido.
-   Diferenciar configuración obligatoria y opcional.
-   No imprimir claves ni contraseñas en logs.
-   Documentar todas las variables en `.env.example`.
-   Usar una configuración específica para desarrollo, pruebas y
    producción.

### 3.3. Definir contratos de respuesta para la API

La API debería devolver estructuras consistentes tanto en éxito como en
error.

Por ejemplo, mantener una estructura uniforme:

``` json
{
  "error": {
    "code": "PROWLARR_UNAVAILABLE",
    "message": "No se pudo consultar el servicio de búsqueda."
  }
}
```

Los códigos internos pueden ser más específicos que los mensajes
visibles. No conviene devolver excepciones, trazas, rutas del servidor
ni secretos.

También conviene documentar:

-   Parámetros admitidos.
-   Valores por defecto.
-   Límites.
-   Códigos HTTP.
-   Estructura de resultados.
-   Estructura de errores.

------------------------------------------------------------------------

## 4. Seguridad y despliegue

La seguridad merece una revisión propia, especialmente si la aplicación
se va a publicar o permitir acceso desde fuera de la red local.

### 4.1. Proteger la integración con Deluge

Revisar especialmente `routes/deluge.py` y el endpoint
`/api/deluge/add`.

Antes de exponer la aplicación:

-   Incorporar autenticación y autorización para las acciones que
    modifican Deluge.
-   No confiar únicamente en que la URL sea difícil de adivinar.
-   Aplicar protección CSRF si se usan sesiones y cookies.
-   Limitar la frecuencia de solicitudes y registrar las acciones.
-   Mantener las credenciales fuera del repositorio y de las respuestas
    HTTP.
-   No exponer el panel o endpoint de control sin una capa de acceso.

### 4.2. Revisar SSRF y validación de URLs

Si el servidor acepta URLs proporcionadas por el cliente y luego las
consulta, puede convertirse en un vector de SSRF.

Recomendaciones:

-   Permitir solamente esquemas necesarios.
-   Validar cada destino después de resolver DNS.
-   Volver a validar los destinos de cada redirección, o deshabilitar
    redirecciones cuando no sean necesarias.
-   Bloquear destinos no permitidos según el modelo de despliegue.
-   Mantener explícitamente la compatibilidad con servicios locales solo
    cuando sea necesaria y controlada.
-   No asumir que validar la URL inicial basta para validar toda la
    cadena de redirecciones.

Una instalación doméstica que necesita acceder a servicios de la LAN
puede requerir reglas distintas a una instancia pública. Esa decisión
debe estar documentada.

### 4.3. Preparar la aplicación para producción

-   Usar HTTPS mediante un proxy inverso.
-   Configurar `SECRET_KEY` segura y no reutilizar valores de
    desarrollo.
-   Desactivar el modo debug.
-   Mantener Waitress u otro servidor WSGI de producción, no el servidor
    de desarrollo de Flask.
-   Configurar límites de tamaño de petición y timeouts.
-   Mantener dependencias actualizadas.
-   Añadir una política de backups si se almacena información
    persistente.
-   No publicar archivos `.env`, bases de datos ni logs con datos
    sensibles.

------------------------------------------------------------------------

## 5. Escalar la experiencia de usuario

Una vez que el núcleo sea confiable, estas mejoras pueden hacer que
Media Tracker se sienta más como un producto terminado.

### 5.1. Historial de búsquedas

Permitir consultar búsquedas recientes, con opción de borrar el
historial.

Posibles implementaciones:

-   LocalStorage para un historial exclusivamente local.
-   Base de datos si se necesita sincronización entre dispositivos o
    usuarios.

No guardar información sensible ni asumir que todos los usuarios quieren
conservar su actividad.

### 5.2. Filtros y búsquedas guardadas

Permitir guardar combinaciones como:

-   Categoría.
-   Calidad.
-   Tamaño mínimo.
-   Idioma.
-   Códec.
-   HDR.

Esto reduce pasos repetitivos y mejora la experiencia de uso frecuente.

### 5.3. Ordenamiento y presentación de resultados

Agregar opciones de ordenamiento claras:

-   Más seeders.
-   Menor tamaño.
-   Mayor tamaño.
-   Calidad.
-   Tipo de contenido.

Mostrar de forma consistente los datos disponibles y no inventar valores
cuando un proveedor no los devuelve.

### 5.4. Estados de carga y errores

La interfaz debería distinguir entre:

-   Búsqueda en curso.
-   Resultados encontrados.
-   Sin resultados.
-   Servicio externo no disponible.
-   Error de conexión.
-   Límite de solicitudes alcanzado.
-   Resultados parciales.

Evitar que un fallo de TMDB impida mostrar resultados que Prowlarr sí
devolvió.

### 5.5. Accesibilidad y responsive design

-   Navegación completa mediante teclado.
-   Estados de foco visibles.
-   Etiquetas accesibles para botones e inputs.
-   Contraste suficiente.
-   Mensajes de error asociados a los campos.
-   Diseño usable en móviles y pantallas pequeñas.
-   No depender exclusivamente del color para comunicar estados.

------------------------------------------------------------------------

## 6. Escalabilidad técnica

No todas estas medidas son necesarias desde el primer día. Deben
incorporarse cuando la carga o las necesidades del proyecto lo
justifiquen.

### 6.1. Caché

La caché actual es una buena base. Para evolucionarla:

-   Definir TTL distintos según el tipo de dato.
-   Documentar qué claves dependen de cada parámetro.
-   Añadir una estrategia de invalidación.
-   Medir hit rate y miss rate.
-   Evitar que un error temporal de un servicio externo quede cacheado
    como si fuera un resultado válido.
-   Si se ejecutan varias instancias, usar Redis como backend
    compartido.

### 6.2. Procesamiento asíncrono

Si las búsquedas empiezan a tardar demasiado o hay tareas pesadas,
evaluar una cola de trabajos.

Una evolución posible:

1.  El cliente solicita una búsqueda.
2.  El servidor crea un trabajo y devuelve un identificador.
3.  Un worker procesa la búsqueda.
4.  El cliente consulta el estado o recibe una actualización.
5.  El resultado se almacena temporalmente y se entrega al cliente.

No introducir Celery, RQ u otra cola antes de necesitarla: agrega
infraestructura y complejidad operativa.

### 6.3. Base de datos

Actualmente algunas funciones pueden funcionar con almacenamiento local
del navegador y caché. Una base de datos se vuelve útil si se
incorporan:

-   Usuarios y autenticación.
-   Listas sincronizadas entre dispositivos.
-   Historial persistente.
-   Preferencias guardadas en servidor.
-   Seguimiento de actividad o estadísticas.

Para ese escenario, SQLite puede servir en una primera etapa de uso
pequeño; PostgreSQL es una opción más adecuada cuando se necesita
concurrencia, múltiples usuarios y crecimiento sostenido.

### 6.4. Observabilidad

Incorporar logs estructurados y métricas básicas:

-   Duración total de cada búsqueda.
-   Tiempo de respuesta de Prowlarr y TMDB.
-   Cantidad de resultados recibidos y descartados.
-   Errores por servicio.
-   Uso de caché.
-   Respuestas HTTP 429.
-   Cantidad de búsquedas simultáneas.

Usar identificadores de petición para seguir una búsqueda entre rutas y
servicios. Nunca registrar API keys, contraseñas, tokens ni URLs
sensibles.

------------------------------------------------------------------------

## 7. Plan de trabajo por etapas

### Etapa 1 --- Estabilización

-   [x] Corregir el ciclo de vida de los locks.
-   [x] Validar `min_size_gb`, `query`, `category` y filtros.
-   [x] Validar la estructura de respuesta de Prowlarr.
-   [x] Separar películas y series en las claves de agrupación.
-   [x] Añadir pruebas para entradas inválidas y respuestas malformadas.

**Resultado esperado:** el buscador se comporta de manera predecible
ante entradas incorrectas y solicitudes simultáneas.

### Etapa 2 --- Calidad de metadatos y servicios externos

-   [x] Mejorar la selección de candidatos de TMDB.
-   [x] Añadir pruebas para títulos ambiguos, remakes y años diferentes.
-   [x] Implementar límite global de concurrencia.
-   [x] Manejar HTTP 429 y fallos temporales.
-   [x] Revisar detección de idiomas y audio.

**Resultado esperado:** resultados más precisos y menor riesgo de
saturar servicios externos.

### Etapa 3 --- Mantenibilidad

-   [x] Extraer la lógica de búsqueda a `search_service.py`.
-   [x] Separar la integración con Prowlarr.
-   [x] Centralizar validaciones.
-   [x] Definir respuestas de error consistentes.
-   [x] Documentar endpoints y configuración.
-   [x] Mantener o aumentar la cobertura de tests.

**Resultado esperado:** código más fácil de entender, probar y extender.

### Etapa 4 --- Seguridad y producción

-   [x] Revisar autenticación y autorización de Deluge.
-   [x] Auditar SSRF y redirecciones.
-   [x] Revisar CORS y CSRF según el despliegue.
-   [x] Verificar secretos y variables de entorno.
-   [x] Configurar HTTPS, logs y límites de recursos.
-   [x] Probar el despliegue desde una instalación limpia.

**Resultado esperado:** una instalación que pueda exponerse de forma
controlada y documentada.

### Etapa 5 --- Evolución del producto

-   [x] Historial de búsquedas.
-   [x] Filtros guardados.
-   [x] Ordenamiento avanzado.
-   [x] Estados de carga y errores más claros.
-   [x] Mejoras de accesibilidad.
-   [x] Mejor experiencia móvil.
-   [x] Evaluar persistencia en base de datos si aparecen necesidades
    reales.

**Resultado esperado:** una aplicación más cómoda para el uso cotidiano,
no solamente un buscador funcional.

### Etapa 6 --- Escalado según demanda

-   [ ] Medir tiempos y uso de caché.
-   [ ] Evaluar Redis compartido.
-   [ ] Evaluar workers y cola de tareas.
-   [ ] Evaluar PostgreSQL si se incorpora persistencia multiusuario.
-   [ ] Incorporar métricas y alertas.

**Resultado esperado:** escalar a partir de datos de uso, sin sumar
infraestructura innecesaria.

------------------------------------------------------------------------

## 8. Estrategia de pruebas

Cada corrección debe incluir pruebas. Como mínimo:

### Pruebas unitarias

-   Validación de parámetros.
-   Normalización de títulos.
-   Detección de idioma y audio.
-   Selección de candidatos de TMDB.
-   Construcción de claves de agrupación.
-   Conversión y validación de datos de Prowlarr.

### Pruebas de integración

-   Búsqueda con respuesta válida de Prowlarr.
-   Prowlarr no disponible.
-   TMDB sin resultados.
-   TMDB con resultados ambiguos.
-   Respuestas JSON inválidas.
-   Caché y paginación.
-   Integración de subtítulos y Deluge.

### Pruebas de concurrencia

-   Varias solicitudes iguales con caché vacía.
-   Varias solicitudes distintas simultáneas.
-   Límite global de consultas a TMDB.
-   Comportamiento cuando un servicio externo responde lentamente.

### Verificaciones antes de integrar cambios

1.  Ejecutar la suite de tests.
2.  Ejecutar el análisis de sintaxis y las verificaciones del frontend.
3.  Comprobar el flujo manual de búsqueda.
4.  Verificar logs y respuestas de error.
5.  Revisar que no se hayan agregado secretos al repositorio.

La cobertura porcentual es útil, pero no reemplaza la calidad de los
casos de prueba. Conviene priorizar escenarios críticos y regresiones
reales.

------------------------------------------------------------------------

## 9. Documentación y presentación del proyecto

Para que Media Tracker también funcione como proyecto de portfolio:

-   Actualizar el README con las funciones que realmente existen.
-   Incluir una captura de pantalla o GIF de la aplicación.
-   Explicar la arquitectura con un diagrama sencillo.
-   Documentar requisitos e instalación desde cero.
-   Explicar cómo configurar Prowlarr, TMDB, OpenSubtitles y Deluge.
-   Incluir una tabla de variables de entorno, sin valores secretos.
-   Documentar endpoints y ejemplos de respuestas.
-   Explicar cómo ejecutar los tests.
-   Mantener `plan.md` y otros documentos alineados con el estado real
    del proyecto.
-   Añadir una sección de decisiones técnicas: por qué Flask, por qué
    caché, cómo se limita la concurrencia y cómo se integran los
    servicios externos.

Una buena presentación no consiste en afirmar que la aplicación escala a
miles de usuarios, sino en explicar qué problemas resuelve, qué
decisiones técnicas toma y qué límites tiene actualmente.

------------------------------------------------------------------------

## 10. Qué no conviene hacer todavía

Para evitar complejidad prematura:

-   No migrar de Flask solamente por moda.
-   No introducir microservicios mientras la aplicación pueda mantenerse
    como un monolito modular.
-   No agregar Kubernetes sin una necesidad concreta.
-   No incorporar una base de datos si los datos actuales no necesitan
    persistencia.
-   No sumar una cola de tareas antes de medir tiempos y concurrencia.
-   No reescribir todo el frontend si los problemas pueden resolverse
    incrementalmente.
-   No perseguir un porcentaje de cobertura sin pruebas útiles.

La arquitectura modular de un monolito es suficiente para una aplicación
de este tamaño y permite crecer sin asumir desde el principio el costo
de un sistema distribuido.

------------------------------------------------------------------------

## 11. Definición de "siguiente nivel"

Se puede considerar que Media Tracker alcanzó una nueva etapa cuando
cumple estas condiciones:

-   Las entradas inválidas no rompen el buscador.
-   Los errores de servicios externos se manejan de manera controlada.
-   Las búsquedas concurrentes no duplican trabajo innecesariamente.
-   TMDB selecciona metadatos con criterios verificables.
-   Películas y series no se agrupan incorrectamente.
-   Los endpoints sensibles están protegidos.
-   La lógica de negocio está separada de las rutas HTTP.
-   Los tests cubren los escenarios críticos.
-   La instalación desde cero está documentada.
-   El README representa fielmente el estado actual del producto.
-   Hay métricas suficientes para decidir cuándo escalar
    infraestructura.

## 12. Recomendación final

El camino más razonable es **estabilizar, medir, modularizar y después
ampliar**.

La mayor oportunidad de mejora inmediata está en la calidad del
buscador: validación, concurrencia y precisión de TMDB. Una vez
resueltos esos puntos, la separación de servicios y la mejora de
seguridad van a dejar una base mucho más sólida.

Media Tracker ya integra varias tecnologías y servicios externos. El
siguiente salto no depende de sumar herramientas por sumar, sino de
demostrar que esas integraciones funcionan de manera confiable, que el
código puede mantenerse y que la aplicación puede evolucionar sin
volverse difícil de controlar.
