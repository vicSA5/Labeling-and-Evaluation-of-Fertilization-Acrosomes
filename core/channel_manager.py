"""Escaneo de carpeta y agrupación de canales por muestra lógica (sin subcarpetas)."""
import re
from dataclasses import dataclass, field
from pathlib import Path

CHANNELS = {"1": "G", "3": "B", "4": "BF"}  # sufijo -> canal
PATTERN = re.compile(r"^(\d+)\.(\d+)\.tiff?$", re.IGNORECASE)


@dataclass
class Sample:
    id: int
    files: dict = field(default_factory=dict)  # canal -> Path
    label: str = ""

    @property
    def missing(self):
        return [c for c in CHANNELS.values() if c not in self.files]


def scan(folder):
    """Devuelve (muestras ordenadas numéricamente, archivos no reconocidos/duplicados)."""
    samples, unknown = {}, []
    for p in Path(folder).iterdir():
        if not p.is_file() or p.suffix.lower() not in (".tif", ".tiff"):
            continue
        m = PATTERN.match(p.name)
        if not m or m.group(2) not in CHANNELS:
            unknown.append(p.name)
            continue
        s = samples.setdefault(int(m.group(1)), Sample(int(m.group(1))))
        ch = CHANNELS[m.group(2)]
        if ch in s.files:  # p. ej. 8.1.tif y 8.1.tiff: no se elige por conjetura
            unknown.append(p.name)
        else:
            s.files[ch] = p
    return [samples[k] for k in sorted(samples)], sorted(unknown)
