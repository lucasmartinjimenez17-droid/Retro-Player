# Playlists · Biblioteca y detalle

La pestaña Playlists muestra **Your Library**, con cinco playlists ficticias,
portadas locales, cantidades reales de canciones asociadas y una flecha para abrirlas.
Cada pulsación de la pestaña vuelve a la biblioteca desde arriba, incluso si ya
estaba seleccionada. La última playlist abierta conserva su marca visual.

Al abrir una playlist, su cabecera muestra portada, nombre, cantidad de canciones,
botón **Play playlist** y acceso de regreso. Las filas muestran las canciones en
el orden definido por la playlist, con portada, título, artista y duración.
Los títulos largos se acortan con puntos suspensivos y conservan el texto completo
en el tooltip. El scroll de canciones es independiente de la cabecera.

La flecha **Your Library** conserva la posición de la biblioteca y devuelve el
foco a la entrada que se abrió. Cambiar a Search, Albums o Queue restaura su vista
habitual. La consulta de búsqueda permanece intacta y no filtra las playlists.

## Estado mock y señales

- Seleccionar una canción reutiliza `_show_track`: actualiza tocadiscos, portada,
  título, artista, duración, progreso y selección. Emite `track_selected(Track)`
  una vez; no cambia por sí solo el estado de pausa.
- **Play playlist** selecciona la primera canción y pone la demo en reproducción.
  Si estaba pausada, emite `playback_toggled(True)` una vez. Si ya estaba reproduciendo,
  no emite un cambio de estado redundante. Reiniciar el progreso al seleccionar una
  canción no emite `seek_requested`.
- Previous/Next mantienen el recorrido circular del catálogo global existente.
  Esta fase no introduce una cola de reproducción por playlist ni modifica Queue.
- Volumen, progreso y Play/Pause mantienen sus señales y comportamientos anteriores.

Todo sigue siendo ficticio: no hay audio, persistencia, OAuth ni acceso a Spotify.
Las cinco listas reutilizan el catálogo de seis canciones con distintos órdenes
y cantidades (6, 4, 5, 3 y 2). No se añaden dependencias ni descargas de recursos.

## Archivos y reutilización

- `ui/mock_data.py`: modelo `Playlist` con identificador local, nombre, paleta de
  portada y referencias ordenadas a canciones; colección `PLAYLISTS`.
- `ui/playlists.py` (nuevo): `PlaylistRow` dibuja cada entrada; `PlaylistBrowser`
  contiene las dos vistas y emite intenciones de selección/reproducción.
- `main_window.py`: integra las vistas bajo las pestañas y conserva la propiedad
  del estado de reproducción. El resto del panel utiliza sus componentes anteriores.
- `ui/widgets.py`: `TrackRow` añade una opción para mantener visible la duración
  de la canción seleccionada en Playlists. Su comportamiento predeterminado no cambia.
- `ui/style.qss`: estilos específicos de biblioteca, cabecera, regreso y reproducción.
- `tests/test_frontend.py`: pruebas de navegación, estado, señales y tamaños.
- `docs/frontend-v1.md`: descripción de Playlists actualizada.

Se reutilizan `TrackRow`, `cover_art`, `icon`, el catálogo de canciones y la lógica
de selección/reproducción. Las filas de detalle se crean una sola vez y se actualizan
al abrir otra lista, evitando acumular widgets o conexiones de señales.

## Validación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py
```

Diez pruebas cubren la interfaz anterior y la biblioteca, el detalle de las cinco
playlists, la correspondencia y orden de canciones, selección, regreso, navegación
repetida, teclado, señales y controles mock. Se bloquean conexiones de socket y se
detectan excepciones de callbacks de Qt durante las pruebas.

Se verifica el renderizado a 1120 × 760, 1400 × 900 y 1680 × 1050, incluidos títulos
largos, scroll, visibilidad de botones y fondo oscuro de ambas listas. Las capturas
se guardan como `playlists-library-{small,initial,large}.png` y
`playlists-detail-{small,initial,large}.png` en esta carpeta.

La vista a tamaño mínimo requiere scroll para mostrar todas las canciones de la
playlist más larga. No se han probado macOS, Linux ni todos los factores de escala
de Windows. La integración real y las playlists editables quedan fuera de esta fase.
