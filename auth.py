import os
import secrets
import hashlib
import base64
import urllib.parse
import webbrowser
import requests
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv


# Cargar variables del archivo .env
load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
TOKEN_CACHE_FILE = "token_cache.json"

SCOPES = [
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
    "playlist-read-collaborative",
    "user-library-read",
]

def generate_code_verifier():
    code = secrets.token_urlsafe(64)
    return code

def generate_code_challenge(code_verifier):
    code_bytes = code_verifier.encode("utf-8")
    hashed = hashlib.sha256(code_bytes).digest()
    encoded = base64.urlsafe_b64encode(hashed)
    challenge = encoded.decode("utf-8")
    challenge = challenge.rstrip("=")
    return challenge

def generate_state():
    return secrets.token_urlsafe(32)

def build_auth_url(code_challenge, state):
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
        "state": state,
    }
    query = urllib.parse.urlencode(params)
    auth_url = f"{AUTH_URL}?{query}"
    return auth_url

class CallbackHandler(BaseHTTPRequestHandler):
    access_token = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "error" in params:
            print("Spotify devolvió un error:", params["error"][0])
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Spotify devolvio un error de autorizacion.")
            return
        
        if "code" not in params or "state" not in params:
            print("Callback incompleto")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Callback de Spotify incompleto.")
            return
        
        code = params["code"][0]
        received_state = params["state"][0]

        if received_state != state:
            print("Error: state no coincide")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Error de seguridad: state incorrecto.")
            return
        
        response = exchange_code_for_token(code, verifier)
        
        if response.status_code != 200:
            print("Error obteniendo token:", response.status_code)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(
                b"No se pudo obtener el token de Spotify."
            )
            return
        
        token_data = response.json()
        CallbackHandler.access_token = token_data["access_token"]

        if "refresh_token" in token_data:
            save_refresh_token(token_data["refresh_token"])

        self.send_response(200)
        self.end_headers()
        self.wfile.write(
            b"Autorizacion recibida. Ya puedes cerrar esta ventana."
        )

def start_callback_server(url):
    server = HTTPServer(
        ("127.0.0.1", 8888),
        CallbackHandler
    )
    print("Servidor listo en http://127.0.0.1:8888")
    print("Esperando respuesta de Spotify...")
    webbrowser.open(url)
    server.handle_request()
    server.server_close()
    return CallbackHandler.access_token

def exchange_code_for_token(code, code_verifier):
    data = {
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }

    response = requests.post(TOKEN_URL, data=data)

    return response

def save_refresh_token(refresh_token):
    data = {
        "refresh_token": refresh_token
    }
    with open(TOKEN_CACHE_FILE, "w") as file:
        json.dump(data, file)

def load_refresh_token():
    try:   
        with open(TOKEN_CACHE_FILE, "r") as file:
            data = json.load(file) 
        return data["refresh_token"]
    except FileNotFoundError:
        return None

def refresh_access_token(refresh_token):
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID
    }
    response = requests.post(TOKEN_URL, data=data)
    if response.status_code == 200:
        token_data = response.json()
        if "refresh_token" in token_data:
            save_refresh_token(token_data["refresh_token"])
        access_token = token_data["access_token"]
        return access_token
    else:
        return None


def authenticate():
    global verifier, state

    refresh_token = load_refresh_token()

    if refresh_token:
        access_token = refresh_access_token(refresh_token)
        if access_token:
            return access_token

    CallbackHandler.access_token = None

    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    state = generate_state()

    url = build_auth_url(challenge, state)

    access_token = start_callback_server(url)

    if access_token is None:
        raise RuntimeError("No se pudo autenticar con Spotify.")

    return access_token
