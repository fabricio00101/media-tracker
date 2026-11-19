@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Media Tracker - Iniciador
cd /d "%~dp0"

rem ============================================================
rem  Rutas relativas al directorio de este archivo (%%~dp0)
rem ============================================================
set "ROOT=%~dp0"
set "FS_DIR=%ROOT%flaresolverr"
set "FS_EXE=%FS_DIR%\flaresolverr.exe"
set "APP_EXE=%ROOT%dist\app.exe"
set "FS_URL=http://127.0.0.1:8191/"
set "APP_URL=http://127.0.0.1:5000/"

echo ============================================================
echo   Media Tracker + FlareSolverr - Iniciador unico
echo ============================================================
echo.

rem ---------- 1) Verificar ejecutables ----------
if not exist "%FS_EXE%" (
    echo [ERROR] No se encontro el ejecutable:
    echo         %FS_EXE%
    echo         Coloque flaresolverr.exe dentro de la carpeta "flaresolverr".
    goto :error
)
if not exist "%APP_EXE%" (
    echo [ERROR] No se encontro el ejecutable:
    echo         %APP_EXE%
    echo         Genere app.exe con PyInstaller en la carpeta "dist".
    goto :error
)
echo [OK] Ejecutables encontrados.

rem ---------- 2) FlareSolverr ----------
call :process_running flaresolverr.exe
set "FS_PROC=!errorlevel!"
call :port_listening 8191
set "FS_PORT=!errorlevel!"
set "FS_OCUPADO=0"

if "!FS_PROC!"=="0" (
    echo [INFO] FlareSolverr ya esta ejecutandose. No se inicia otra instancia.
    echo        Si se inicio sin LANG=en-US, reinicielo manualmente.
) else (
    if "!FS_PORT!"=="0" (
        echo [AVISO] El puerto 8191 esta ocupado pero no se detecto flaresolverr.exe.
        echo         No se inicia otra instancia; se verificara el estado.
        set "FS_OCUPADO=1"
    ) else (
        echo [INFO] Iniciando FlareSolverr en una ventana propia...
        set "LANG=en-US"
        set "LOG_LEVEL=info"
        start "FlareSolverr - registros" /D "%FS_DIR%" "%FS_EXE%"
    )
)

call :wait_url "%FS_URL%" 1 30
if errorlevel 1 (
    echo [ERROR] FlareSolverr no respondio en %FS_URL% dentro del tiempo esperado.
    if "!FS_OCUPADO!"=="1" echo         El puerto 8191 puede estar ocupado por otro programa.
    echo         Revise la ventana "FlareSolverr - registros" para ver los registros.
    goto :error
)
echo [OK] FlareSolverr disponible en %FS_URL%

rem ---------- 3) Media Tracker ----------
call :process_running app.exe
set "APP_PROC=!errorlevel!"
call :port_listening 5000
set "APP_PORT=!errorlevel!"
set "APP_OCUPADO=0"

if "!APP_PROC!"=="0" (
    echo [INFO] Media Tracker ya esta ejecutandose. No se inicia otra instancia.
) else (
    if "!APP_PORT!"=="0" (
        echo [AVISO] El puerto 5000 esta ocupado pero no se detecto app.exe.
        echo         No se inicia otra instancia; se verificara el estado.
        set "APP_OCUPADO=1"
    ) else (
        echo [INFO] Iniciando Media Tracker...
        start "Media Tracker" /D "%ROOT%." "%APP_EXE%"
    )
)

call :wait_url "%APP_URL%" 0 20
if errorlevel 1 (
    echo [ERROR] Media Tracker no respondio en %APP_URL% dentro del tiempo esperado.
    if "!APP_OCUPADO!"=="1" echo         El puerto 5000 puede estar ocupado por otro programa.
    goto :error
)
echo [OK] Media Tracker disponible en %APP_URL%

echo [INFO] Abriendo el navegador en %APP_URL% ...
start "" "%APP_URL%"

echo.
echo Todo listo. Puede cerrar esta ventana: los servicios siguen activos.
ping -n 6 127.0.0.1 >nul 2>&1
exit /b 0

rem ============================================================
rem  Subrutinas
rem ============================================================

:process_running
tasklist /FI "IMAGENAME eq %~1" /NH 2>nul | findstr /I /C:"%~1" >nul
exit /b %errorlevel%

:port_listening
netstat -ano 2>nul | findstr /C:":%~1" | findstr /I "LISTENING" >nul
exit /b %errorlevel%

:wait_url
set "W_URL=%~1"
set "W_FS=%~2"
set "W_MAX=%~3"
set /a W_N=0
:wait_url_loop
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; try { $r=Invoke-WebRequest -Uri '%W_URL%' -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -ne 200) { exit 1 }; if ('%W_FS%' -eq '1' -and $r.Content -notlike '*FlareSolverr is ready*') { exit 1 }; exit 0 } catch { exit 1 }"
if not errorlevel 1 exit /b 0
set /a W_N+=1
if %W_N% GEQ %W_MAX% exit /b 1
rem  ping se usa en lugar de timeout porque funciona aunque la entrada este redirigida
ping -n 3 127.0.0.1 >nul 2>&1
goto :wait_url_loop

:error
echo.
echo El lanzador se detuvo. Presione cualquier tecla para cerrar esta ventana.
pause >nul
exit /b 1
