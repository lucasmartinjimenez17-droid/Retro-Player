import os
import secrets
import hashlib
import base64
import urllib.parse
import webbrowser
import requests

from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

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
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "error" in params:
            print("Spotify devolvió un error:", params["error"][0])
            return

        code = params["code"][0]
        received_state = params["state"][0]

        if received_state != state:
            print("Error: state no coincide")
            return
        
        response = exchange_code_for_token(code, verifier)
        
        if response.status_code != 200:
            print("Error obteniendo token:", response.status_code)
            return
        
        token_data = response.json()
        access_token = token_data["access_token"]

        #pause_response = pause_playback(access_token)
        #print("Pause status:", pause_response.status_code)

        #play_response = resume_playback(access_token)
        #print("Play status:", play_response.status_code)

        #volume_response = set_volume(access_token, 100)
        #print("Volume status:", volume_response.status_code)

        #next_response = next_track(access_token)
        #print("Change status:", next_response.status_code)

        #previous_response = previous_track(access_token)
        #print("Change status:", previous_response.status_code)

        search_response = search_tracks(access_token, "Kanye West")
        print("Search status:", search_response.status_code)

        if search_response.status_code == 200:
            data = search_response.json()
            tracks = data["tracks"]["items"]

            songs = []

            for track in tracks:
                song = {
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                    "album": track["album"]["name"],
                    "image": track["album"]["images"][0]["url"],
                    "uri": track["uri"]
                }

                songs.append(song)

            print(songs)

            if songs:
                selected_song = songs[0]

                print(
                    "Reproduciendo:",
                    selected_song["name"],
                    "-",
                    selected_song["artist"]
                )

                play_response = play_track(
                    access_token,
                    selected_song["uri"]
                )

                print("Play track status:", play_response.status_code)
                
        track_response = get_current_track(access_token)
        print("Estado canción:", track_response.status_code)

        if track_response.status_code == 200:
            track_data = track_response.json()

            song_name = track_data["item"]["name"]
            artist_name = track_data["item"]["artists"][0]["name"]

            print("Canción:", song_name)
            print("Artista:", artist_name)
        else:
            print("No hay ninguna canción reproduciéndose.")

        print("Status:", response.status_code)
        
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

def get_current_track(access_token):
    url = "https://api.spotify.com/v1/me/player/currently-playing"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)

    return response

def pause_playback(access_token):
    url = "https://api.spotify.com/v1/me/player/pause"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.put(url, headers=headers)
    return response

def resume_playback(access_token):
    url = "https://api.spotify.com/v1/me/player/play"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.put(url, headers=headers)
    return response

def next_track(access_token):
    url = "https://api.spotify.com/v1/me/player/next"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.post(url, headers=headers)
    return response

def previous_track(access_token):
    url = "https://api.spotify.com/v1/me/player/previous"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.post(url, headers=headers)
    return response

def set_volume(access_token, volume_percent):
    url = "https://api.spotify.com/v1/me/player/volume"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
    "volume_percent": volume_percent
    }
    if 0 <= volume_percent <= 100:
        response = requests.put(url, headers=headers, params=params)
        return response
    else:
        raise ValueError("El volumen debe estar entre 0 y 100")

def search_tracks(access_token, query):
    url = "https://api.spotify.com/v1/search"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "q": query,
        "type": "track",
        "limit": 5
    }
    response = requests.get(url, headers=headers, params=params)
    return response

def play_track(access_token, track_uri):
    url = "https://api.spotify.com/v1/me/player/play"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    data = {
        "uris": [track_uri]
    }

    response = requests.put(
        url,
        headers=headers,
        json=data
    )

    return response

#INICIO DEL PROGRAMA
verifier = generate_code_verifier()
challenge = generate_code_challenge(verifier)
state = generate_state()
url = build_auth_url(challenge, state)
start_callback_server(url)
