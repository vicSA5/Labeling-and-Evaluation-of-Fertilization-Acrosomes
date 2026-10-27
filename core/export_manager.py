import tempfile, zipfile
from datetime import date
from pathlib import Path
from core import progress


def folder_name(label):
    return label.replace(" / ", "_").replace(" ", "_")   # p. ej. Parcial_en_duda


def export_zip(path, samples):
    """ZIP con una carpeta por categoría + clasificaciones.csv. Devuelve nº de pendientes excluidas."""
    root = f"clasificacion_{date.today():%Y-%m-%d}"
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with tempfile.TemporaryDirectory() as d:
        csv_path = Path(d) / "clasificaciones.csv"
        progress.save(csv_path, samples)
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:   # los TIFF ya van comprimidos
            for s in samples:
                if s.label:
                    for p in s.files.values():
                        z.write(p, f"{root}/{folder_name(s.label)}/{p.name}")
            z.write(csv_path, f"{root}/clasificaciones.csv")
    tmp.replace(path)
    return sum(1 for s in samples if not s.label)