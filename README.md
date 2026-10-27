# lefAI
Clasificación manual del estado acrosómico (sin IA en esta versión).

    python -m venv .venv && .venv\Scripts\activate
    pip install -r requirements-dev.txt
    python main.py          # ejecutar
    pytest                  # pruebas
    pyinstaller --noconsole --name lefAI main.py   # .exe en dist/

Archivos: `N.1.tiff` = BF, `N.3.tiff` = G, `N.4.tiff` = B (también `.tif`). Sin subcarpetas.
Teclas: 1 Intacto · 2 Reaccionado · 3 Parcial/duda · 4 Error de imagen · ←/→ · Supr.
El progreso se autoguarda en `~/.lefai/` y se reanuda al reabrir la misma carpeta.
"Descargar CSV" exporta en cualquier momento. Los TIFF nunca se modifican.
