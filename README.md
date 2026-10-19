# Retro Player

Retro Player es un reproductor musical de escritorio desarrollado en Python y conectado a Spotify mediante su Web API.

El objetivo principal del proyecto es aprender y aplicar conceptos reales de desarrollo de software mientras se construye una aplicación funcional, visual y cuidada.

## Objetivo

Crear una interfaz alternativa para controlar Spotify con una estética de tocadiscos vintage, limpia y minimalista.

La idea final es que la aplicación muestre un gran tocadiscos en pantalla, con un vinilo animado cuya portada corresponda a la canción actual, además de búsqueda, playlists, álbumes, cola y controles de reproducción.

## Estado actual

La primera fase del proyecto, centrada en la integración con Spotify y la lógica principal, está completada.

El frontend **PySide6** funciona actualmente con datos mock independientes del backend.
Se abre con `python main.py`, sin OAuth, credenciales ni llamadas a Spotify.
Incluye tocadiscos dibujado con QPainter, controles ficticios, Search con navegación
a álbumes y artistas, Playlists, Albums, Queue y Liked Songs. Permite guardar
álbumes, crear playlists y añadir canciones durante la sesión.

Documentación del frontend:

- [Ejecución, estructura, pruebas y límites visuales](docs/frontend-v1.md).
- [Menús, favoritos y gestión de canciones](docs/song-management.md).
- [Navegación de Search y perfiles de artistas](docs/search-navigation.md).
- [Álbumes guardados y creación de playlists](docs/library-management.md).

En el backend ya funcionan:

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

La integración de la interfaz con el backend de Spotify sigue pendiente.

## Stack

- Python
- Spotify Web API
- Requests
- OAuth 2.0 + PKCE
- python-dotenv
- PySide6 y Qt / QSS
- Git y GitHub

Más adelante: integración del frontend con Spotify y animaciones del tocadiscos.

## Arquitectura actual

```text
RetroPlayer/
│
├── main.py
├── main_window.py
├── ui/
├── tests/
├── docs/
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

Es el punto de entrada de la demo visual: crea QApplication y abre MainWindow.
Antes de desarrollar el frontend se utilizaba como banco de pruebas para la
autenticación, la creación de `SpotifyClient` y las funciones de Spotify.
Los módulos originales del backend se conservan intactos, pero la demo no los importa.

### Frontend y pruebas

`main_window.py` coordina la interfaz; `ui/` contiene widgets, estilos, datos mock
y estado compartido. `tests/` verifica interacciones, navegación y distribución;
`docs/` incluye guías y capturas. No hay persistencia de cambios mock al cerrar.

```powershell
python main.py
python -m unittest discover -s tests -v
```

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

Esta configuración solo se necesita para el backend; la demo visual funciona sin credenciales.

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
- [x] Crear la ventana principal
- [x] Diseñar layouts y widgets
- [x] Añadir controles de reproducción
- [x] Crear búsqueda visual
- [x] Mostrar playlists, álbumes y cola
- [ ] Conectar la interfaz con `SpotifyClient`
- [x] Construir el tocadiscos estático
- [x] Favoritos, perfiles de artistas y navegación entre vistas
- [x] Guardar álbumes y crear playlists en la sesión mock

### Fase 3 — Pulido

- [ ] Animación del vinilo
- [x] Portada mock integrada en el vinilo
- [ ] Animación del brazo y la aguja
- [ ] Transiciones y QSS
- [ ] Gestión visual de errores
- [ ] Mejorar la experiencia de usuario

## Mejoras técnicas previstas

Estas mejoras siguen pendientes para la integración y evolución del proyecto:

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
