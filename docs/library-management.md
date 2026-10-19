# Retro Player · Gestión de biblioteca (prompt 7)

## Funcionalidades

El detalle compartido de álbum muestra **Save album** o **Remove from library**
junto a los controles de la cabecera. Funciona al entrar desde Search, un perfil
de artista o Your Albums. Guardar actualiza inmediatamente la biblioteca y el
botón; eliminar conserva el álbum disponible en Search y en su artista. Ninguna
operación modifica canciones favoritas ni contenidos de playlists. Your Albums
tiene un mensaje específico cuando no quedan álbumes guardados.

El catálogo incorpora **Moonlit Water**, de **Nina Shore**, con tres canciones.
Empieza sin guardar: hay seis álbumes disponibles, cinco guardados inicialmente
y 37 canciones en el catálogo completo.

**+ New playlist** abre un formulario integrado en Your Library. Create valida
el nombre, elimina espacios de los extremos y acepta hasta 80 caracteres;
los nombres vacíos muestran un error. Cancel o salir de la sección descarta
el formulario. Una confirmación no puede crear dos listas accidentalmente.
Se permiten nombres repetidos, cada uno con un ID distinto.

La nueva playlist aparece inmediatamente con portada generada localmente y
contador de cero canciones. Su detalle vacío muestra instrucciones para añadir
canciones y oculta/desactiva Play playlist. Los menús Add to playlist consultan
el estado al abrirse e incluyen las listas nuevas y originales. Las canciones
se añaden al final, sin duplicados, actualizando contadores y detalle. También
se admiten pistas disponibles únicamente en álbumes o perfiles de artistas.

## Estado y señales

`SessionState` continúa siendo la fuente compartida de estado durante la sesión:

- `albums` referencia el catálogo por ID; `saved_album_ids` mantiene únicamente
  los IDs guardados y su orden. `set_album_saved` ignora IDs desconocidos y
  operaciones repetidas; `saved_albums_changed` actualiza biblioteca y botón.
- `playlists` contiene los metadatos por ID. `playlist_ids` conserva las listas
  ordenadas de IDs de canciones ya utilizadas por el frontend.
- `create_playlist` genera un ID UUID, valida el nombre, registra metadatos y
  contenido vacío, y emite `playlist_created`. La vista incorpora su nueva fila.
- `playlist_changed` sigue actualizando contenido y contadores al añadir canciones.
  El selector utiliza IDs como datos de las acciones, incluso con nombres iguales.

Se reutilizan portadas, filas, menús y el detalle de álbum. La señal adicional
`extra_play_requested` permite seleccionar la primera pista de una playlist nueva
cuando no pertenece a las seis pistas iniciales, conservando las señales previas.
No incorpora reproducción contextual ni cambia el comportamiento de siguiente/anterior.

## Archivos de esta iteración

Modificados:

- `main_window.py`: conexión de la señal de reproducción mock de pistas adicionales.
- `ui/mock_data.py`: álbum no guardado y IDs guardados iniciales explícitos.
- `ui/session.py`: álbumes guardados, metadatos de playlists y creación validada.
- `ui/widgets.py`: selector dinámico y acceso al layout de cabecera compartido.
- `ui/albums.py`: biblioteca filtrada, estado vacío y botón sincronizado.
- `ui/playlists.py`: formulario, filas dinámicas y detalle vacío.
- `ui/style.qss`: botones secundarios y formulario.
- `tests/test_frontend.py`: seis pruebas adicionales y expectativas del catálogo.
- `docs/frontend-v1.md`: enlace a esta guía.

Creados: esta guía, `tests/render_library_management.py` y 17 capturas
`docs/library-*.png`. Los cambios anteriores presentes en el proyecto se conservan.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests/render_library_management.py
```

Resultado: **38 pruebas correctas**, incluidas las 32 anteriores. La suite
bloquea conexiones de red y recoge excepciones en callbacks Qt. Las nuevas
pruebas cubren sincronización y deduplicación de álbumes, biblioteca vacía,
independencia de favoritos y playlists, validación/cancelación/confirmación única,
nombres repetidos con IDs distintos, listas vacías, menús dinámicos, canciones
adicionales, contadores, orden y geometría en los tres tamaños solicitados.

Las capturas se generan con widgets Qt reales y estilo Fusion en 1120 × 760,
1400 × 900 y 1680 × 1050. Se revisaron visualmente cabeceras, formulario,
biblioteca, listas con canciones y estados vacíos. Ejemplos:

- [Save album, 1120 × 760](library-save-album-1120x760.png)
- [Álbum guardado, 1120 × 760](library-saved-album-1120x760.png)
- [Formulario, 1120 × 760](library-new-playlist-form-1120x760.png)
- [Biblioteca con playlist nueva, 1400 × 900](library-new-playlist-1400x900.png)
- [Playlist con canciones, 1680 × 1050](library-playlist-songs-1680x1050.png)
- [Playlist vacía](library-empty-playlist.png)
- [Álbumes vacíos](library-empty-albums.png)

## Límites de la demo

El catálogo, guardado, creación de playlists, cola y controles de reproducción
siguen siendo mock y locales. No hay audio real, persistencia entre ejecuciones,
peticiones HTTP, OAuth ni confirmaciones de éxito de Spotify.

La futura integración deberá cargar IDs y colecciones reales, comprobar permisos
de edición de playlists, resolver paginación y manejar operaciones asíncronas y
errores antes de confirmar cambios. La lógica de mutación está concentrada en
`SessionState` para facilitar esa sustitución. No se han implementado esas capas,
ni edición, eliminación o renombrado de playlists.

`auth.py`, `spotify_api.py`, `.env` y `token_cache.json` permanecen intactos.
No se añadieron dependencias ni se realizaron commits o pushes.
