# RetroPlayer · Frontend V1

Esta versión abre una interfaz de escritorio de PySide6 sin importar `auth.py`
ni `spotify_api.py`. No necesita cuenta de Spotify, `.env`, tokens ni conexión.

La ampliación actual incorpora **Liked Songs** y los menús de gestión de canciones.
[La guía del prompt 4](song-management.md) detalla el estado compartido, acciones,
pruebas y capturas. Las capturas originales de V1 muestran la versión anterior.

Search permite ahora [explorar álbumes y perfiles de artistas](search-navigation.md)
con navegación de vuelta y conservación de la búsqueda. Los detalles de álbum
reutilizan la vista existente de Your Albums.

La [guía de gestión de biblioteca](library-management.md) documenta Save album,
Remove from library y la creación de playlists durante la sesión (prompt 7).

## Ejecutar

Desde la raíz del proyecto, con el entorno virtual activado:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

También se puede ejecutar directamente con `.\.venv\Scripts\python.exe main.py`.
La dependencia nueva es PySide6; el dibujo y los recursos no necesitan paquetes
adicionales. La versión declarada es la instalada durante la implementación.

## Organización

- `main.py`: crea QApplication, aplica el estilo Fusion y abre la ventana.
- `main_window.py`: layouts, panel lateral, controles y estado de la demo.
- `ui/widgets.py`: tocadiscos escalable, iconos, portadas originales generadas
  localmente y filas de resultados accesibles con teclado.
- `ui/mock_data.py`: catálogo ficticio tipado y formato de tiempos.
- `ui/playlists.py`: biblioteca y detalle de playlists dentro del panel derecho.
- `ui/albums.py`: cuadrícula de álbumes y detalle con pistas numeradas.
- `ui/session.py`: favoritos, playlists y adiciones a Queue mediante IDs estables.
- `ui/liked.py`: canciones guardadas y estado vacío.
- `ui/style.qss`: colores, tipografía, espaciado y estados de los controles.
- `tests/test_frontend.py`: pruebas de arranque, interacción y renderizado.

Se conservan los módulos originales del backend sin modificaciones. No hay
recursos remotos, descargas, fuentes externas ni lectura de credenciales.
Las portadas se generan una vez por combinación de colores y se cachean en memoria.

## Alcance de la demo

El vinilo, el brazo y la posición inicial de reproducción son estáticos. No hay
audio, temporizadores de reproducción ni animaciones. Play/Pause cambia el estado
visual; Previous/Next y las filas seleccionan canciones ficticias. Los sliders
actualizan únicamente los valores de ejemplo. El buscador filtra el catálogo local.

Search muestra resultados de canción, álbum y artista, más seis canciones;
Playlists muestra una biblioteca de cinco playlists con navegación al detalle
([guía de Playlists](playlists.md)); Albums muestra una biblioteca de cinco álbumes
con canciones propias ([guía de Albums](albums.md)); Queue muestra las siguientes
canciones del catálogo circular, excluyendo la actual, seguidas de las adiciones
del usuario. Los cambios se conservan durante la sesión y se descartan al cerrar.

La ventana emite `playback_toggled(bool)`, `track_selected(Track)`,
`seek_requested(int)` (segundos) y `volume_changed(int)` (0–100), preparados para
un futuro controlador. La conexión real, los identificadores de Spotify y la
actualización desde el backend quedan para una fase posterior. Estas señales
no están conectadas a servicios y no amplían las funciones del backend existente.

## Diseño y límites

Tamaño inicial solicitado: 1400 × 900 píxeles lógicos. Tamaño mínimo: 1120 × 760.
Windows puede reducir el tamaño inicial para ajustarlo al área disponible del
monitor. Los layouts se adaptan y la lista tiene scroll cuando no cabe completa.
Los controles permanecen accesibles en el tamaño mínimo. Se utiliza Segoe UI y
Georgia, con las sustituciones que Qt encuentre si no están instaladas.

El diseño sigue la imagen «Reproductor retro de vinilo moderno.png» facilitada
durante la implementación: gran vinilo con etiqueta roja, base de madera,
superficie azul marino, brazo dorado, controles dentro de la base y panel oscuro
con pestañas superiores y búsqueda. La imagen no es una dependencia en ejecución.

El tocadiscos es una ilustración vectorial con textura local, no una reproducción
fotográfica del material original. Las portadas y los artistas son ficticios.
Se mantiene el marco nativo de Windows para mover, minimizar, maximizar y cerrar.
Los controles secundarios de favoritos, aleatorio y repetición de la referencia
no se implementan en esta V1; se priorizan los controles exigidos en el encargo.
No se reproduce el fondo beige exterior de la imagen: pertenece al entorno de
presentación de la referencia, no al contenido de la aplicación.

## Verificación reproducible

```powershell
python -m unittest discover -s tests -v
```

En Windows se debe utilizar el renderizador nativo de Qt para evaluar las fuentes.
El plugin `offscreen` puede producir glifos vacíos en este entorno. Las pruebas
bloquean conexiones de socket y detectan excepciones en callbacks de Qt. Cubren
selección, navegación, búsqueda vacía, controles con teclado, señales, cierre y
renderizado a 1120 × 760, 1400 × 900 y 1680 × 1050.

Las capturas `frontend-v1.png` y `frontend-v1-small.png` muestran los tamaños
principal y mínimo. No se verifica reproducción real, OAuth ni llamadas a Spotify:
no forman parte de esta versión. Tampoco se ha validado en macOS, Linux ni en
todos los factores de escala de Windows.
