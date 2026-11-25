# AGENTS.md

## Contexto del proyecto
- Stack: Flask 3.0.0, Waitress 3.0.2, HTML5, Tailwind CSS, Vanilla JS
- Python: 3.10 o superior
- Base de datos: No utiliza base de datos relacional (persistencia local vía LocalStorage y caché Flask-Caching con Redis opcional vía REDIS_URL; fallback a SimpleCache en memoria)
- Estructura: blueprints Flask en routes/ (search, subtitles, deluge), servicios en services/, utilidades en utils/
- Docker: incluye Dockerfile y docker-compose.yml que levanta la app (Waitress) junto a Redis

## Comandos
- Correr servidor: python app.py
- Correr tests: python -m pytest
- Instalar dependencias: pip install -r requirements.txt
- Levantar con Docker (app + Redis): docker compose up -d --build

## Convenciones
- Comentarios en español
- Funciones pequeñas, una responsabilidad por función
- Siempre actualizar requirements.txt al agregar dependencias

## Restricciones
- NO modificar archivos fuera del directorio del proyecto
- NO instalar dependencias sin confirmar con el usuario
- NO borrar archivos existentes sin confirmar
- NO asumir estructura de base de datos, siempre leer los modelos primero

## Al terminar cada sesión
Generá un resumen en session_log.md con:
qué se completó, qué quedó pendiente, qué decisiones se tomaron.