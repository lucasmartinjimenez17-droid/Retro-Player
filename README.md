# Retro Player

Retro Player es un reproductor musical de escritorio desarrollado en Python y conectado a Spotify mediante su Web API.

El objetivo principal del proyecto es aprender y aplicar conceptos reales de desarrollo de software mientras se construye una aplicación funcional, visual y cuidada.

## Objetivo

Crear una interfaz alternativa para controlar Spotify con una estética de tocadiscos vintage, limpia y minimalista.

La idea final es que la aplicación muestre un gran tocadiscos en pantalla, con un vinilo animado cuya portada corresponda a la canción actual, además de búsqueda, playlists, álbumes, cola y controles de reproducción.

## Estado actual

Actualmente ya funcionan:

- Autenticación con Spotify mediante OAuth 2.0 + PKCE
- Obtención del access token
- Lectura de la canción actual
- Play y pause
- Siguiente canción
- Canción anterior
- Control de volumen
- Búsqueda de canciones
- Obtención de nombre, artista, álbum, portada y URI
- Reproducción de una canción concreta a partir de su Spotify URI

## Stack

- Python
- Spotify Web API
- Requests
- OAuth 2.0 + PKCE
- python-dotenv
- Git y GitHub

Más adelante:

- PySide6
- Qt / QSS
- Animaciones del tocadiscos

## Idea visual

La interfaz estará basada en una única pantalla principal:

- Tocadiscos grande como elemento central
- Vinilo girando durante la reproducción
- Portada del álbum en el centro del vinilo
- Brazo y aguja animados
- Buscador de canciones
- Playlists
- Álbumes
- Cola
- Controles de reproducción y volumen

La estética será vintage pero minimalista, priorizando una interfaz limpia, fluida y visualmente cuidada.

## Arquitectura prevista

El proyecto se irá separando progresivamente en diferentes responsabilidades:

```text
RetroPlayer/
│
├── main.py
├── auth.py
├── spotify_api.py
│
├── .env
├── .gitignore
└── requirements.txt
```

- `auth.py`: autenticación con Spotify
- `spotify_api.py`: comunicación con Spotify Web API
- `main.py`: coordinación principal de la aplicación

Más adelante se añadirá la interfaz gráfica con PySide6.

## Instalación

Clona el repositorio:

```bash
git clone <URL_DEL_REPOSITORIO>
```

Crea un entorno virtual:

```bash
python -m venv .venv
```

Actívalo en Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```bash
python -m pip install -r requirements.txt
```

## Configuración de Spotify

Es necesario crear una aplicación en Spotify for Developers y configurar un archivo `.env`:

```env
SPOTIFY_CLIENT_ID=tu_client_id
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

El archivo `.env` no debe subirse a GitHub.

## Próximos pasos

- Refactorizar la autenticación y la lógica de Spotify
- Crear `SpotifyClient`
- Añadir playlists
- Añadir álbumes
- Añadir cola
- Construir la interfaz con PySide6
- Diseñar el tocadiscos
- Añadir animaciones limpias y fluidas
- Pulir errores y experiencia de usuario

## Objetivo de aprendizaje

Este proyecto no busca únicamente conseguir que la aplicación funcione.

El objetivo es entender cómo se construye, poder modificarla y aprender conceptos como APIs, HTTP, JSON, OAuth, seguridad, POO, arquitectura de software, interfaces gráficas y Git mientras se desarrolla un proyecto real.
