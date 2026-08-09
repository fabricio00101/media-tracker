import base64
import requests
import logging
from flask import Blueprint, request, jsonify
import config

deluge_bp = Blueprint("deluge", __name__)

@deluge_bp.route("/api/deluge/add", methods=["POST"])
def add_to_deluge():
    if not config.DELUGE_URL or not config.DELUGE_PASSWORD:
        return (
            jsonify(
                {
                    "error": "Las credenciales de Deluge no están configuradas en .env (DELUGE_URL y DELUGE_PASSWORD)."
                }
            ),
            500,
        )

    data = request.get_json()
    magnet_url = data.get("magnet")

    if not magnet_url:
        return jsonify({"error": "Se requiere un magnet válido."}), 400

    session = requests.Session()
    json_rpc_url = f"{config.DELUGE_URL}/json"

    # Paso 1: Autenticación
    login_payload = {"method": "auth.login", "params": [config.DELUGE_PASSWORD], "id": 1}

    try:
        login_res = session.post(json_rpc_url, json=login_payload, timeout=10)
        login_res.raise_for_status()
        login_data = login_res.json()

        if not login_data.get("result"):
            return jsonify({"error": "Contraseña de Deluge incorrecta."}), 401

        magnet_url = magnet_url.strip()
        # Paso 2: Añadir el torrent (Magnet o Archivo físico)
        if magnet_url.lower().startswith("magnet:"):
            add_payload = {
                "method": "core.add_torrent_magnet",
                "params": [magnet_url, {}],
                "id": 2,
            }
        else:
            try:
                # Es un link HTTP a Prowlarr. Lo descargamos en RAM.
                # Aumentamos el timeout y desactivamos la auto-redirección
                t_res = requests.get(magnet_url, timeout=120, allow_redirects=False)

                add_payload = None

                # Prowlarr a veces devuelve un 302 Found redirigiendo a un Magnet Real.
                if t_res.status_code in [301, 302, 303, 307, 308]:
                    location = t_res.headers.get("Location", "")
                    if location.lower().startswith("magnet:"):
                        add_payload = {
                            "method": "core.add_torrent_magnet",
                            "params": [location, {}],
                            "id": 2,
                        }
                    else:
                        # Si redirige a otra web, la seguimos manualmente
                        t_res = requests.get(location, timeout=120)
                        t_res.raise_for_status()

                # Si no se ha fabricado la payload asumiendo un magnet, es un archivo .torrent
                if not add_payload:
                    t_res.raise_for_status()
                    b64_torrent = base64.b64encode(t_res.content).decode("utf-8")

                    add_payload = {
                        "method": "core.add_torrent_file",
                        "params": ["descarga.torrent", b64_torrent, {}],
                        "id": 2,
                    }
            except Exception as e:
                return (
                    jsonify(
                        {
                            "error": f"Fallo interceptando .torrent desde Prowlarr local: {e}"
                        }
                    ),
                    500,
                )

        add_res = session.post(json_rpc_url, json=add_payload, timeout=10)
        add_res.raise_for_status()
        add_data = add_res.json()

        if add_data.get("error"):
            return (
                jsonify({"error": f"Error insertando en Deluge: {add_data['error']}"}),
                500,
            )

        return jsonify({"message": "Añadido exitosamente a Deluge."})

    except requests.exceptions.ConnectionError:
        return jsonify({"error": f"No se pudo conectar a Deluge en {config.DELUGE_URL}"}), 503
    except Exception as e:
        logging.error(f"Error al contactar Deluge Web UI: {e}")
        return (
            jsonify({"error": f"Error interno contactando con Deluge: {str(e)}"}),
            500,
        )
