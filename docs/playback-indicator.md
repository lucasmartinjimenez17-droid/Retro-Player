# Indicador de reproducción · Prompt 8

Las filas comparten un `PlaybackIndicator` de 18 × 18 píxeles. QPainter dibuja
cuatro barras doradas, con alturas de 4 a 14 píxeles. Una `QVariantAnimation`
recorre un ciclo de 2,4 segundos; funciones seno con distintas fases y armónicos
enteros producen un movimiento suave, también al enlazar ciclos.

Cada indicador tiene una única animación hija, creada con el widget y reutilizada.
Qt gestiona las animaciones mediante su controlador compartido: no se añaden
QTimers por fila. Solo el pequeño widget solicita repintado en cada fotograma.

`TrackRow` conecta su selección y la propiedad `playing` existentes al indicador:

- La fila activa y visible se anima durante Play.
- Pause congela las barras; Play reanuda desde esa posición.
- Cambiar de canción oculta y detiene el indicador anterior.
- Ocultar una fila, una sección o la ventana detiene su animación. Volver a
  mostrarla reinicia el ciclo si continúa activa y reproduciéndose.
- Al destruir la fila se destruyen automáticamente el indicador y su animación.

La ventana conserva el estado mock y las señales Qt anteriores. Search identifica
la selección por ID, igual que las colecciones. Su canción en Top Results refleja
ahora el mismo estado que en Songs. Si una pista tiene varias representaciones
visibles, todas muestran el mismo estado de reproducción; las fases de sus barras
pueden diferir según cuándo se mostraron.

Se reserva una columna independiente antes de la duración: 18 píxeles y un espacio
de 8 píxeles. La altura de las filas, las portadas y las posiciones de duración y
menú permanecen iguales. Los títulos conservan el truncado y espacio para el corazón.
Se retiraron las desactivaciones del indicador en las vistas de colecciones.

## Archivos

Nuevos: `ui/playback_indicator.py`, `tests/render_playback_indicator.py`, esta guía
y cinco capturas `docs/playback-*.png`.

Modificados: `ui/widgets.py`, `main_window.py`, `ui/albums.py`, `ui/playlists.py`,
`ui/liked.py`, `ui/artists.py`, `tests/test_frontend.py` y `README.md`.
El README también integra el estado y roadmap remoto con la documentación local,
conservando las explicaciones del backend y los planes pendientes.

## Verificación reproducible

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests/render_playback_indicator.py
```

Las 38 pruebas anteriores se mantienen. Cinco pruebas adicionales comprueban:

Resultado final: **43 pruebas correctas** en 53,140 segundos. El generador de
capturas también finaliza correctamente; la suite bloquea conexiones de red.

1. Cambios reales entre fotogramas, pausa estable, reanudación, Previous y Next.
2. Selección y estado por ID en Search, Albums, Playlists, Liked, artistas y Queue.
3. Navegación repetida sin acumular animaciones ni timers, detención al ocultar
   vistas y ejecución de callbacks de interfaz mientras las barras se mueven.
4. Destrucción de widgets y liberación de la animación Qt.
5. Títulos largos, corazón, duración y menú separados en los tres tamaños.

Capturas revisadas visualmente:

- [1120 × 760](playback-search-1120x760.png)
- [1400 × 900](playback-search-1400x900.png)
- [1680 × 1050](playback-search-1680x1050.png)
- [Detalle de álbum](playback-album.png)
- [Cinco fotogramas en movimiento y uno pausado](playback-frames.png)

Es una animación decorativa del estado mock: no analiza frecuencias, reproduce
audio ni conecta Spotify. La reproducción contextual y las animaciones del vinilo
y brazo siguen pendientes. No se modifican los módulos de backend, credenciales,
tokens ni dependencias.
