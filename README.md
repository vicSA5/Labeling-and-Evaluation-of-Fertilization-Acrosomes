# LEFA

**Labeling and Evaluation of Fertilization Acrosomes**

Aplicación de escritorio para Windows que permite revisar imágenes de microscopía multicanal y clasificar manualmente el estado acrosómico de espermatozoides. Esta versión **no incluye clasificación automática por IA**.

## Qué hace

- Carga una carpeta de TIFF y agrupa los canales de cada muestra (una clasificación por muestra, no por archivo).
- Muestra un canal cada vez (BF, G o B), con zoom, desplazamiento y contraste ajustable. Los archivos originales nunca se modifican.
- Avisa de los canales que faltan y de los archivos que no reconoce, sin detener el trabajo.
- Clasifica con teclado o botones y avanza sola a la siguiente muestra pendiente.
- Autoguarda el progreso y lo recupera al reabrir la misma carpeta.
- Exporta un CSV y un ZIP con los archivos organizados por categoría.
- Funciona sin conexión: no envía imágenes ni datos a ningún servicio externo.

## Formato de entrada

Una carpeta (sin subcarpetas) con archivos `.tif` o `.tiff` nombrados `N.canal.tiff`:

| Archivo   | Canal                  |
|-----------|------------------------|
| `8.1.tiff` | G (acrosoma)          |
| `8.3.tiff` | B (núcleo)            |
| `8.4.tiff` | BF (campo claro)      |

Los TIFF pueden ser en escala de grises o RGB, y estar comprimidos (LZW, etc.).

## Categorías y atajos

| Tecla | Acción                         |
|-------|--------------------------------|
| `1`   | Intacto                        |
| `2`   | Reaccionado                    |
| `3`   | Parcial / en duda              |
| `4`   | Error de imagen                |
| `Supr`| Quitar etiqueta (o repetir la tecla de la etiqueta actual) |
| `←` `→` | Muestra anterior / siguiente |
| `,` `.` | Cambiar de canal             |
| `↑` `↓` | Aumentar / disminuir contraste |
| `R`   | Restablecer contraste          |
| `A`   | Ajustar vista                  |

## Instalación y uso

Requiere Python 3.12 o superior.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python main.py
```

Para ejecutar las pruebas: `pytest`.

## Crear el ejecutable

```bash
pyinstaller --noconsole --collect-all imagecodecs --icon resources/logo_all.ico --add-data "resources;resources" --name LEFA main.py
```

El resultado queda en `dist/LEFA/`. La carpeta completa es la aplicación: para distribuirla, comprímela entera.

## Progreso y exportación

- El progreso se guarda automáticamente en `C:\Users\<usuario>\.lefai\`, un CSV por carpeta de imágenes. Si mueves o renombras la carpeta, LEFA no encontrará el progreso anterior.
- **Descargar CSV** guarda una copia donde elijas, con una fila por muestra: ID, archivos de cada canal, etiqueta y canales ausentes.
- **Descargar ZIP** crea una carpeta por categoría con los archivos originales de las muestras clasificadas, más `clasificaciones.csv`. Las muestras pendientes no se incluyen en las carpetas.

## Estructura

```
main.py                 punto de entrada
core/channel_manager.py escaneo y agrupación de canales
core/progress.py        CSV de progreso
core/export_manager.py  exportación ZIP
ui/main_window.py       interfaz (PySide6)
tests/                  pruebas
resources/              iconos
```

## Limitaciones conocidas

- Solo imágenes 2D (grises o RGB); no admite TIFF multipágina.
- Sin selector de idioma: la interfaz está en español.
- Al reanudar, no avisa de muestras nuevas o ausentes respecto al CSV anterior.
- Las imágenes se leen en el momento de mostrarlas, sin precarga.

## Autor

Hecho por Víctor Sánchez Auñón en sus prácticas en RoViT.
