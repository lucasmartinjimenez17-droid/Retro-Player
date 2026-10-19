# Gestión de canciones y Liked Songs — fase 2, prompts 4 y 5

Ejecutar desde la raíz: `.venv\Scripts\python.exe main.py`.

## Uso

- Las canciones de Search (incluido el resultado destacado), Playlists, Albums,
  Queue y Liked tienen un botón `···`. Los resultados de tipo álbum o artista no
  muestran acciones de canción.
- El menú ofrece **Like / Unlike** para guardar/quitar favoritos, añadir a una de las cinco playlists
  y añadir al final de Queue. Abrirlo o ejecutar una acción no selecciona ni
  reproduce la canción. El corazón dorado junto al título indica que está guardada.
- Liked abre **Liked Songs**, inicialmente vacío. Tiene contador, portadas,
  duración, selección y scroll. Quitar una canción actualiza la lista inmediatamente.
- Las playlists muestran el contenido y el contador actualizados durante la
  sesión. Las opciones que ya contienen la canción aparecen deshabilitadas con
  “Added”. Los favoritos también evitan duplicados.
- Queue conserva la lista mock circular anterior y muestra después las adiciones
  del usuario, en orden. Estas adiciones permiten duplicados, incluso de la canción
  seleccionada, y no desaparecen al navegar o usar Previous/Next. El buscador solo
  aparece y filtra en Search; Queue muestra toda la cola. Al volver a Search se
  recupera el texto de búsqueda anterior.
- Teclado: Tab hasta `···`, Espacio para abrir, flechas para recorrer el menú y
  el submenú, Enter para actuar y Escape para cerrar. Sobre una fila también
  funcionan la tecla Menú y Shift+F10. Qt ajusta los menús al área de pantalla.

## Estado y componentes

`SessionState`, propiedad de `MainWindow`, contiene listas ordenadas de IDs para
favoritos, contenido de cada playlist y adiciones a Queue. Los métodos de mutación
emiten señales Qt específicas. Las vistas escuchan esos cambios; no mantienen
copias independientes de las colecciones.

Las 34 canciones tienen IDs literales estables en el catálogo. `TRACKS_BY_ID`
resuelve esos IDs, incluidas las canciones exclusivas de Albums. Las posiciones
originales de las playlists solo se usan para inicializar sus IDs de sesión.

Se reutilizan `TrackRow`, las portadas locales, `scroll_area`, `CollectionHeader`
y los navegadores existentes. `TrackRow` concentra las acciones del menú y usa un
botón hijo que no activa el botón de selección de la fila. Las listas reutilizan
filas; sus conjuntos de widgets solo crecen cuando hace falta mostrar más canciones.
Los menús capturan el ID al abrirse para evitar actuar sobre otra canción cuando
una eliminación reasigna las filas de Liked.

Las señales públicas de `MainWindow` conservan su firma y significado. Las señales
de índices originales de `PlaylistBrowser` también se mantienen; la señal adicional
`extra_track_requested(Track)` transporta canciones que no están en el catálogo
original de seis canciones. El tocadiscos y los controles inferiores no se rediseñan.

## Archivos de esta iteración

- Creados: `ui/session.py`, `ui/liked.py`, `tests/render_song_management.py`,
  este documento y las siete capturas indicadas abajo.
- Modificados: `main_window.py`, `ui/mock_data.py`, `ui/widgets.py`,
  `ui/playlists.py`, `ui/albums.py`, `ui/style.qss`, `tests/test_frontend.py`,
  `docs/frontend-v1.md` y `README.md`.
- Los cambios de fases anteriores se conservan; no se ha hecho commit ni push.

## Verificación

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tests/render_song_management.py
```

25 pruebas: las 22 de gestión musical y 3 regresiones visuales del prompt 5.
Las comprobaciones de gestión musical agrupan apertura de menús
sin selección, teclado y submenús, guardado/eliminación, sincronización, duplicados,
conteos y contenido, orden de Queue, canciones exclusivas de Albums, aislamiento
entre sesiones, cinco pestañas, scroll y geometría en los tres tamaños. Las pruebas
bloquean conexiones de sockets y detectan excepciones en callbacks de Qt.

Capturas revisadas con fuentes nativas de Windows:

- `liked-1120x760.png`, `liked-1400x900.png`, `liked-1680x1050.png`.
- `liked-empty.png`.
- `song-options.png`: ventana con la captura real del QMenu superpuesta, ya que
  Qt dibuja los menús en ventanas nativas separadas.
- `song-options-menu.png`, `playlist-selector.png`: widgets de menú por separado.

## Límites

Solo datos mock en memoria; cerrar la app descarta los cambios. No hay audio,
motor secuencial de cola, base de datos, creación/edición/eliminación de playlists,
conexión a Spotify ni OAuth. Previous/Next mantienen el catálogo circular original.
No se han añadido dependencias. Validación visual en Windows; otros sistemas y
factores de escala quedan fuera de esta comprobación.

Los SHA-256 de `auth.py`, `spotify_api.py`, `.env` y `token_cache.json` coinciden
con los valores previos a esta iteración. No se ha modificado su contenido.

## Correcciones visuales y UX — prompt 5

Cambios localizados en `ui/widgets.py` y `main_window.py`:

- Los textos del menú compartido son `Like` y `Unlike`; el estado y las acciones
  de favoritos mantienen su funcionamiento.
- `TrackRow` reserva 18 píxeles del área del título (corazón de 12 + separación
  de 6), trunca el texto y mide el resultado con las métricas de la fuente. El
  corazón se dibuja justo después de ese texto, centrado en la misma línea.
  La altura de la fila y las columnas de duración y opciones permanecen iguales.
  La señal existente de favoritos provoca el repintado inmediato al hacer Unlike.
- La causa de las duraciones ausentes era una condición de dibujo que sustituía
  el tiempo por el indicador de reproducción en filas seleccionadas y en marcha.
  Ahora toda duración disponible se dibuja siempre; el indicador solo puede
  aparecer cuando falta la duración. Álbumes y artistas no muestran tiempos de canción.
- Queue oculta el contenedor completo del buscador, recuperando su espacio en el
  layout, e ignora la consulta de Search. Conserva scroll, selección y adiciones.

Se actualizó `tests/test_frontend.py`: las 22 pruebas previas pasan con los nuevos
textos y las 3 nuevas verifican el dibujo real de duraciones, la posición del
corazón con títulos cortos/largos en las cinco secciones, y la navegación
Search/Queue sin filtros ocultos. Resultado: **25 pruebas aprobadas**.

Capturas reproducibles con `.venv\Scripts\python.exe tests/render_visual_fixes.py`:
`ux-search-1120x760.png`, `ux-search-1400x900.png`, `ux-search-1680x1050.png`,
las tres equivalentes `ux-queue-*.png`, `ux-liked-long-title.png`,
`ux-album-detail.png`, `ux-like-menu.png` y `ux-unlike-menu.png`.
Las diez capturas están en `docs/` y se han revisado con fuentes nativas de Windows.

Archivos modificados en el prompt 5: `ui/widgets.py`, `main_window.py`,
`tests/test_frontend.py` y este documento. Añadidos: `tests/render_visual_fixes.py`
y las diez capturas. Sin cambios de arquitectura, dependencias, tocadiscos ni
archivos del backend; sin conexiones a Spotify, OAuth, commits ni pushes.
