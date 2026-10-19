# Albums · Biblioteca y detalle

**Albums → Your Albums → Álbum → Canciones.** Todo ocurre en el panel derecho.
Cada pulsación de Albums abre la biblioteca desde arriba. Las cinco tarjetas se
distribuyen en dos columnas; portada cuadrada, nombre, artista y año son visibles,
con hover, foco de teclado y selección. Los textos largos se abrevian con puntos
suspensivos; el tooltip mantiene la información completa. La biblioteca tiene scroll.

Pulsar una tarjeta abre su detalle **sin seleccionar ni reproducir una canción**.
La cabecera muestra portada, nombre, artista, año, cantidad de canciones y
**Play album**. Debajo aparecen sus canciones en orden, numeradas, con título,
artista y duración. El scroll de pistas mantiene la cabecera y el regreso accesibles.
La flecha devuelve a la biblioteca conservando posición, selección y foco.

Seleccionar una pista reutiliza la lógica del reproductor y conserva el estado
de pausa. Play album selecciona la primera canción, reinicia el progreso y activa
visualmente la reproducción. No hay audio, persistencia, OAuth ni red.

## Datos y componentes

- `ui/mock_data.py`: modelo `Album`, colección `ALBUMS`, lookup `ALBUMS_BY_ID` y
  `Track.album_id`. Las pistas se asocian por identificador local y cada álbum
  contiene su secuencia ordenada. Hay cinco álbumes y 34 canciones en total,
  con cantidades de 12, 5, 7, 4 y 6 pistas. Artistas, años y portadas son ficticios.
- `ui/albums.py` (nuevo): `AlbumCard` y `AlbumBrowser`, biblioteca y detalle.
  Las filas se reutilizan en cada visita; no se acumulan widgets ni conexiones.
- `ui/widgets.py`: cabecera `CollectionHeader` y helper `scroll_area` compartidos;
  `TrackRow` admite números de pista sin alterar su presentación predeterminada.
- `ui/playlists.py`: utiliza la cabecera y el scroll extraídos, conservando su
  navegación, señales, atributos y aspecto anterior.
- `main_window.py`: integra Albums y concentra la selección de canciones y el
  inicio de reproducción de ambas colecciones en las mismas funciones.
- `tests/test_frontend.py`: regresiones existentes y pruebas específicas de Albums.
- `docs/frontend-v1.md`: descripción de la nueva biblioteca.

Se reutilizan las portadas locales `cover_art`, iconos, estilos de Playlists,
filas `TrackRow` y la lógica central de selección. No se añaden dependencias ni
se modifica el dibujo del tocadiscos o los controles inferiores.

## Compatibilidad y límites

El catálogo global `TRACKS` conserva sus seis canciones originales. Search,
Playlists y Queue mantienen esos datos y comportamientos. Las pistas adicionales
se encuentran únicamente en Albums durante esta fase.

La canción actual se guarda como `Track`; `current_index` es su índice en el
catálogo original, o `None` si es una canción exclusiva de Albums. Esto evita
marcar por error una canción distinta en Search o Playlists.

Previous/Next siguen recorriendo el catálogo global, sin reproducción contextual:
desde una canción exclusiva de Albums, Next vuelve a la primera canción global
y Previous a la última. En ese estado Queue muestra las seis canciones originales,
pues ninguna coincide con la actual. La cola no se sustituye por el contenido del álbum.

Las señales públicas conservan su significado: `track_selected(Track)` por selección,
`playback_toggled(bool)` solo al cambiar reproducción/pausa, `seek_requested(int)`
por cambio manual de progreso y `volume_changed(int)` por cambio de volumen.
Abrir un álbum no emite señales de reproducción ni altera el progreso.

## Ejecutar y verificar

```powershell
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Se verificaron 16 pruebas: navegación, retorno, pertenencia y orden de pistas,
numeración, selección, Play album, significado de señales, sincronización entre
colecciones, controles existentes y visitas repetidas sin duplicación. Las pruebas
bloquean conexiones de socket y detectan excepciones en callbacks de Qt.

Se revisó la biblioteca y el detalle a **1120 × 760**, **1400 × 900** y **1680 × 1050**,
incluido el ajuste de tarjetas cuadradas, la ausencia de solapamientos y el scroll
de álbumes largos. Las capturas son `albums-library-{small,initial,large}.png` y
`albums-detail-{small,initial,large}.png`, en esta carpeta.

La comparación de capturas a 1400 × 900 confirmó que el área del reproductor y
el detalle de Playlists permanecen visualmente idénticos. Se comprobó el arranque
y cierre nativo de `main.py`. No se validaron macOS, Linux ni todos los factores
de escala de Windows. El backend y los archivos de credenciales se verificaron
sin cambios mediante hashes SHA-256. No se hicieron commits ni pushes.
