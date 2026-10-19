# Search navegable y perfiles de artista — fase 2, prompt 6

Ejecutar desde la raíz: `.venv\Scripts\python.exe main.py`.

## Recorridos disponibles

- Buscar el nombre de cualquiera de los cinco álbumes y abrir su resultado.
- Buscar artistas como **The Velvet Hours**, **Nina Shore** o **Arthur Miles**
  y abrir su perfil. Los resultados de álbum se identifican como “Album” y los
  artistas tienen retrato circular y etiqueta “Artist”. Ambos muestran una flecha.
- Desde el perfil, seleccionar canciones o abrir una portada de la cuadrícula
  Albums. La cabecera, canciones y álbumes comparten un único scroll vertical.
- Buscar **The Listening Room** para ver un perfil mock sin canciones ni álbumes,
  con mensajes independientes para cada sección vacía.
- Usar atrás para recorrer Album → Artist → Search o Album → Search. Se conservan
  consulta, resultados, posición del scroll y foco. Abrir de nuevo un perfil desde
  los resultados empieza por su cabecera; volver desde su álbum conserva el scroll.

Abrir álbumes o perfiles no selecciona canciones ni altera la pausa o la posición
del reproductor. Seleccionar una canción actualiza la demo; **Play album** selecciona
la primera canción y reanuda el estado mock. Los menús Like/Unlike, Add to playlist
y Add to queue usan el mismo estado de sesión en todas las pantallas.

## Navegación y reutilización

`MainWindow` mantiene una ruta actual y una pequeña pila de rutas de Search,
acompañadas de scroll y widget enfocado. No hay ventanas nuevas ni un router global.
Un contador de navegación invalida restauraciones de scroll pendientes si se cambia
de pestaña antes de que Qt termine su siguiente paso de layout.

Cambiar de pestaña vacía el historial interno de Search. Al pulsar Search se vuelve
a sus resultados con la consulta conservada; Playlists y Albums siguen abriendo
sus bibliotecas. Queue conserva el comportamiento sin buscador del prompt 5.

Se reutiliza **la misma instancia de `AlbumBrowser` y su página de detalle** para
Your Albums, Search y los perfiles. El parámetro opcional `back_label` configura
el destino de vuelta. La nueva señal `back_requested` devuelve el control a Search;
sin ese parámetro, el botón vuelve a Your Albums como antes. Las señales anteriores
conservan sus firmas y significado.

`ArtistProfile` reutiliza `TrackRow`, `AlbumCard`, el scroll y los estilos existentes.
Las filas crecen solo cuando hacen falta; las tarjetas de álbum se reutilizan al
cambiar de artista. `SearchResultRow` representa un álbum o artista real del modelo,
sin inventar una canción auxiliar ni exponer acciones o duraciones de canción.
Los retratos son pequeños dibujos circulares generados localmente con QPainter.

## Relaciones del catálogo

El nuevo modelo `Artist` contiene un ID estable, nombre, paleta para el retrato,
IDs de álbumes e IDs de canciones. Los álbumes se relacionan explícitamente por ID;
los IDs de sus canciones se obtienen de los álbumes existentes y se resuelven con
`TRACKS_BY_ID`. No se crean copias de canciones ni se usan nombres como identidad.

Se conservan los cinco álbumes y las 34 canciones. Hay cinco artistas con un álbum
cada uno y un perfil vacío adicional. La cuadrícula admite dos columnas y listas
de varios álbumes; el catálogo actual solo dispone de uno por artista publicado.

Search conserva el catálogo original de seis canciones y su selección. Cuando hay
consulta, filtra los cinco álbumes y los seis artistas; sin consulta mantiene un
álbum y un artista destacados. Las otras canciones se descubren en perfiles y
álbumes, manteniendo su identidad en favoritos, playlists y Queue.

## Archivos

Modificados en esta iteración:

- `main_window.py`: resultados tipados, perfil, sincronización e historial local.
- `ui/albums.py`: destino de vuelta configurable, sin duplicar el detalle.
- `ui/mock_data.py`: artistas y relaciones mediante IDs.
- `tests/test_frontend.py`: adaptación a los nuevos resultados y siete pruebas de exploración.
- `docs/frontend-v1.md`: referencia a esta ampliación.

Creados:

- `ui/artists.py`: retrato local y perfil reutilizable.
- `ui/search.py`: entradas navegables de álbum y artista.
- `tests/render_search_navigation.py`: capturas reproducibles.
- Este documento y catorce capturas en `docs/`.

## Validación

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe tests/render_search_navigation.py
```

32 pruebas: las 25 anteriores y 7 nuevas. Cubren apertura de los cinco álbumes y
seis artistas, ausencia de reproducción automática, canciones y relaciones,
selección/Play album, menús y estado compartido, historial, foco, scroll, vacíos,
teclado, reutilización de widgets y cambios repetidos entre las cinco pestañas.
Las pruebas bloquean conexiones de socket y recogen excepciones de callbacks Qt.

Capturas a 1120 × 760, 1400 × 900 y 1680 × 1050:

- `search-results-{ancho}x{alto}.png`.
- `search-album-{ancho}x{alto}.png`.
- `artist-profile-{ancho}x{alto}.png`.
- `artist-album-{ancho}x{alto}.png`.
- Adicionales: `artist-profile-albums-small.png` y `artist-profile-empty.png`.

## Límites y archivos protegidos

Todo sigue siendo mock, local y temporal. No hay reproducción real, HTTP, Spotify,
OAuth, persistencia ni nuevas dependencias. Los retratos son ilustraciones, no
fotografías; no hay biografías ni estadísticas inventadas. No se han rediseñado
el tocadiscos, los controles inferiores, Playlists, Queue ni Liked Songs.

Los SHA-256 de `auth.py`, `spotify_api.py`, `.env` y `token_cache.json` permanecen
iguales. No se ha realizado commit ni push.
