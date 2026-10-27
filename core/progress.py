"""Guardado atómico y lectura del CSV de progreso (una fila por muestra)."""
import csv, os
from pathlib import Path

COLUMNS = ["sample_id", "file_bf", "file_g", "file_b", "label", "missing_channels"]
LABELS = {"1": "Intacto", "2": "Reaccionado", "3": "Parcial / en duda", "4": "Error de imagen"}


def save(path, samples):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for s in samples:
            w.writerow([s.id] + [s.files[c].name if c in s.files else "" for c in ("BF", "G", "B")]
                       + [s.label, ";".join(s.missing)])
    os.replace(tmp, path)


def load(path):
    """Devuelve {sample_id: label}. Lanza ValueError si el formato no es válido."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or not {"sample_id", "label"} <= set(r.fieldnames):
            raise ValueError("El CSV no tiene las columnas 'sample_id' y 'label'.")
        return {int(row["sample_id"]): row["label"] for row in r if row["sample_id"].strip().isdigit()}
