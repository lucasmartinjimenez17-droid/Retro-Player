# Retro Player

Retro Player es un reproductor musical de escritorio desarrollado en Python y conectado a Spotify mediante su Web API.

El objetivo principal del proyecto es aprender y aplicar conceptos reales de desarrollo de software mientras se construye una aplicación funcional, visual y cuidada.

## Objetivo

Crear una interfaz alternativa para controlar Spotify con una estética de tocadiscos vintage, limpia y minimalista.

La idea final es que la aplicación muestre un gran tocadiscos en pantalla, con un vinilo animado cuya portada corresponda a la canción actual, además de búsqueda, playlists, álbumes, cola y controles de reproducción.

## Estado actual

La primera fase del proyecto, centrada en la integración con Spotify y la lógica principal, está completada.

Actualmente funcionan:

- Autenticación con Spotify mediante OAuth 2.0 + PKCE
- Sesión persistente mediante refresh token
- Renovación automática del access token
- Lectura de la canción actual
- Play y pause
- Siguiente canción
- Canción anterior
- Control de volumen
- Búsqueda de canciones
- Obtención de nombre, artista, álbum, portada y URI
- Reproducción de una canción concreta a partir de su Spotify URI
- Lectura de playlists del usuario
- Lectura de álbumes guardados
- Lectura de la cola de reproducción
- Transformación de las respuestas JSON de Spotify en estructuras más simples para la aplicación

La siguiente fase del proyecto será construir la interfaz gráfica con PySide6.

## Stack

- Python
- Spotify Web API
- Requests
- OAuth 2.0 + PKCE
- python-dotenv
- Git y GitHub

Próxima fase:

- PySide6
- Qt / QSS
- Animaciones del tocadiscos

## Arquitectura actual

```text
RetroPlayer/
│
├── main.py
├── auth.py
├── spotify_api.py
├── README.md
├── requirements.txt
├── .env
├── token_cache.json
└── .gitignore
```

### `auth.py`

Gestiona la autenticación con Spotify:

- Generación de PKCE
- Construcción de la URL de autorización
- Servidor local de callback
- Intercambio del authorization code por tokens
- Guardado y lectura del refresh token
- Renovación automática del access token

### `spotify_api.py`

Contiene la clase `SpotifyClient`, encargada de comunicarse con Spotify Web API.

Actualmente permite:

- `play()`
- `pause()`
- `next()`
- `previous()`
- `set_volume()`
- `get_current_track()`
- `search_tracks()`
- `play_track()`
- `get_playlists()`
- `get_saved_albums()`
- `get_queue()`

Los métodos que reciben respuestas grandes de Spotify transforman el JSON original y devuelven únicamente los datos que Retro Player necesita.

### `main.py`

Es el punto de entrada de la aplicación y coordina:

1. La autenticación.
2. La creación de `SpotifyClient`.
3. El uso de las distintas funcionalidades de Spotify.

Actualmente también se utiliza como banco de pruebas antes de conectar toda la lógica con la futura interfaz gráfica.

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

## Instalación

Clona el repositorio:

```bash
git clone https://github.com/lucasmartinjimenez17-droid/Retro-Player.git
cd Retro-Player
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

Los archivos sensibles o locales no deben subirse al repositorio:

- `.env`
- `token_cache.json`

Ambos están incluidos en `.gitignore`.

## Roadmap

### Fase 1 — Spotify y backend

- [x] OAuth 2.0 + PKCE
- [x] Sesión persistente
- [x] SpotifyClient
- [x] Play / pause
- [x] Next / previous
- [x] Volumen
- [x] Canción actual
- [x] Búsqueda
- [x] Reproducción de canciones
- [x] Playlists
- [x] Álbumes guardados
- [x] Cola

### Fase 2 — Interfaz con PySide6

- [ ] Aprender los fundamentos de PySide6
- [ ] Crear la ventana principal
- [ ] Diseñar layouts y widgets
- [ ] Añadir controles de reproducción
- [ ] Crear búsqueda visual
- [ ] Mostrar playlists, álbumes y cola
- [ ] Conectar la interfaz con `SpotifyClient`
- [ ] Construir el tocadiscos

### Fase 3 — Pulido

- [ ] Animación del vinilo
- [ ] Portada integrada en el vinilo
- [ ] Animación del brazo y la aguja
- [ ] Transiciones y QSS
- [ ] Gestión visual de errores
- [ ] Mejorar la experiencia de usuario

## Mejoras técnicas previstas

Estas mejoras no son prioritarias para comenzar la interfaz, pero se abordarán más adelante:

- Centralizar los headers HTTP repetidos de `SpotifyClient`
- Mejorar la gestión de errores y excepciones de red
- Diferenciar entre resultados vacíos y errores de API
- Añadir paginación para playlists y álbumes con más de 50 elementos
- Eliminar dependencias de estado global en la autenticación
- Evitar que las peticiones HTTP bloqueen la interfaz gráfica usando workers o threads cuando sea necesario
- Seguir refactorizando solo cuando aporte claridad o mantenibilidad real

## Objetivo de aprendizaje

Este proyecto no busca únicamente conseguir que la aplicación funcione.

El objetivo es entender cómo está construida, poder modificarla y aprender conceptos como APIs, HTTP, JSON, OAuth, seguridad, POO, arquitectura de software, interfaces gráficas y Git mientras se desarrolla un proyecto real.

La prioridad es comprender las decisiones técnicas y ser capaz de mantener y ampliar el proyecto de forma progresivamente más autónoma.
