import hashlib
from pathlib import Path
import numpy as np
import tifffile
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QPainter, QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QGraphicsScene, QGraphicsView, QHBoxLayout,
                               QLabel, QMessageBox, QPushButton, QSlider, QStackedWidget, QVBoxLayout, QWidget)
from core import progress
from core.channel_manager import scan
from core import export_manager

class Viewer(QGraphicsView):
    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.item = self._scene.addPixmap(QPixmap())
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

    def show_array(self, a8, fit=False):
        a8 = np.ascontiguousarray(a8)
        h, w = a8.shape[:2]
        if a8.ndim == 2:
            img = QImage(a8.data, w, h, w, QImage.Format_Grayscale8)
        else:
            img = QImage(a8.data, w, h, w * 3, QImage.Format_RGB888)
        self.item.setPixmap(QPixmap.fromImage(img.copy()))
        self.setSceneRect(self.item.boundingRect())
        if fit:
            self.fitInView(self.item, Qt.KeepAspectRatio)

    def clear(self):
        self.item.setPixmap(QPixmap())

    def wheelEvent(self, e):
        k = 1.25 if e.angleDelta().y() > 0 else 0.8
        self.scale(k, k)


def normalize(raw):
    """Muestra los valores reales del archivo (sin autocontraste), como el explorador."""
    if raw.dtype == np.uint8:
        return raw.astype(np.float32)
    if raw.dtype == np.uint16:
        return raw.astype(np.float32) / 257.0   # 0-65535 -> 0-255
    a = raw.astype(np.float32)                   # otros tipos: ajuste por min-max
    lo, hi = a.min(), a.max()
    return (a - lo) / ((hi - lo) or 1.0) * 255


def apply_contrast(n, c):
    f = 1 + c / 100 if c < 0 else 1 + c / 25
    return np.clip((n - 128) * f + 128, 0, 255).astype(np.uint8)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LEFA — Labeling and Evaluation of Fertilization Acrosomes")
        self.resize(1200, 800)
        self.samples, self.idx, self.ch, self.csv_path, self.norm = [], 0, "BF", None, None
        self.stack = QStackedWidget()
        QVBoxLayout(self).addWidget(self.stack)
        self.stack.addWidget(self._load_page())
        self.stack.addWidget(self._classify_page())
        for k in "1234":
            QShortcut(QKeySequence(k), self, activated=lambda k=k: self.set_label(progress.LABELS[k]))
        QShortcut(QKeySequence(Qt.Key_Left), self, activated=lambda: self.goto(self.idx - 1))
        QShortcut(QKeySequence(Qt.Key_Right), self, activated=lambda: self.goto(self.idx + 1))
        QShortcut(QKeySequence(Qt.Key_Delete), self, activated=lambda: self.set_label("", advance=False))
        QShortcut(QKeySequence(Qt.Key_Up), self, activated=lambda: self.slider.setValue(self.slider.value() + 10))
        QShortcut(QKeySequence(Qt.Key_Down), self, activated=lambda: self.slider.setValue(self.slider.value() - 10))
        QShortcut(QKeySequence(Qt.Key_Comma), self, activated=lambda: self.cycle_channel(-1))
        QShortcut(QKeySequence(Qt.Key_Period), self, activated=lambda: self.cycle_channel(1))
        QShortcut(QKeySequence(Qt.Key_R), self, activated=lambda: self.slider.setValue(0))
        QShortcut(QKeySequence(Qt.Key_A), self, activated=lambda: self.stack.currentIndex() == 1 and self.render(fit=True))

    # ---------- pantallas ----------
    def _load_page(self):
        w = QWidget(); l = QVBoxLayout(w)
        
        def key(k):
            return (f"<span style='background-color:#3b3b3b; color:#ffffff; font-weight:bold; "
                    f"font-family:Consolas;'>&nbsp;{k}&nbsp;</span>")

        t = QLabel(
            "<h1 style='font-size:48px;'>LEFA</h1>"
            "<p style='font-size:20px;'>Revisión y clasificación de imágenes de acrosomas.</p>"
            "<p style='font-size:18px;'>Nombres esperados: "
            "<b>N.1.tiff</b> (G) · <b>N.3.tiff</b> (B) · <b>N.4.tiff</b> (BF)</p>"
            "<table cellpadding='6' style='font-size:18px;'>"
            f"<tr><td>{key('1')}</td><td><b>Intacto</b></td></tr>"
            f"<tr><td>{key('2')}</td><td><b>Reaccionado</b></td></tr>"
            f"<tr><td>{key('3')}</td><td><b>Parcial / en duda</b></td></tr>"
            f"<tr><td>{key('4')}</td><td><b>Error de imagen</b></td></tr>"
            f"<tr><td>{key('←')} {key('→')}</td><td>Anterior / Siguiente</td></tr>"
            f"<tr><td>{key('Supr')}</td><td>Quitar etiqueta</td></tr>"
            f"<tr><td>{key(',')} {key('.')}</td><td>Cambiar canal</td></tr>"
            f"<tr><td>{key('↑')} {key('↓')}</td><td>Aumentar / disminuir contraste</td></tr>"
            f"<tr><td>{key('R')}</td><td>Restablecer contraste</td></tr>"
            f"<tr><td>{key('A')}</td><td>Ajustar vista</td></tr>"
            "</table>"
        )
        
        t.setAlignment(Qt.AlignCenter)
        b = QPushButton("Seleccionar carpeta"); b.clicked.connect(self.open_folder)
        self.load_msg = QLabel(""); self.load_msg.setAlignment(Qt.AlignCenter)
        foot = QLabel("Hecho por Víctor Sánchez Auñón durante sus prácticas en RoViT")
        foot.setAlignment(Qt.AlignCenter)
        foot.setStyleSheet("color:#8a8a8a; font-size:12px;")

        l.addStretch()
        for x in (t, b, self.load_msg):
            l.addWidget(x, alignment=Qt.AlignCenter)
        l.addStretch()
        l.addWidget(foot)
        return w

    def _classify_page(self):
        w = QWidget(); root = QHBoxLayout(w)
        left = QVBoxLayout(); root.addLayout(left, 4)
        bar = QHBoxLayout(); left.addLayout(bar)
        self.ch_btns = {}
        for c in ("BF", "G", "B"):
            b = QPushButton(c); b.setCheckable(True); b.clicked.connect(lambda _, c=c: self.set_channel(c))
            self.ch_btns[c] = b; bar.addWidget(b)
        bar.addStretch()
        self.viewer = Viewer(); left.addWidget(self.viewer, 1)
        row = QHBoxLayout(); left.addLayout(row)
        row.addWidget(QLabel("Contraste"))
        self.slider = QSlider(Qt.Horizontal); self.slider.setRange(-100, 100)
        self.slider.valueChanged.connect(lambda: self.render())
        row.addWidget(self.slider)
        r = QPushButton("Restablecer"); r.clicked.connect(lambda: self.slider.setValue(0)); row.addWidget(r)
        f = QPushButton("Ajustar vista"); f.clicked.connect(lambda: self.render(fit=True)); row.addWidget(f)

        right = QVBoxLayout(); root.addLayout(right, 1)
        self.info = QLabel(); self.info.setWordWrap(True); right.addWidget(self.info)
        self.warn = QLabel(); self.warn.setStyleSheet("color:#b45309;font-weight:bold"); self.warn.setWordWrap(True)
        right.addWidget(self.warn)
        self.lab_btns = {}
        for k in "1234":
            b = QPushButton(f"{k} — {progress.LABELS[k]}"); b.setMinimumHeight(48)
            b.clicked.connect(lambda _, k=k: self.set_label(progress.LABELS[k])); right.addWidget(b)
            self.lab_btns[progress.LABELS[k]] = b
        nav = QHBoxLayout(); right.addLayout(nav)
        for txt, d in (("← Anterior", -1), ("Siguiente →", 1)):
            b = QPushButton(txt); b.clicked.connect(lambda _, d=d: self.goto(self.idx + d)); nav.addWidget(b)
        p = QPushButton("Ir a primera pendiente"); p.clicked.connect(self.first_pending); right.addWidget(p)
        d = QPushButton("Descargar CSV"); d.clicked.connect(self.download_csv); right.addWidget(d)
        z = QPushButton("Descargar ZIP"); z.clicked.connect(self.download_zip); right.addWidget(z)
        right.addStretch()
        return w

    # ---------- carga ----------
    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Carpeta con imágenes TIFF")
        if not folder:
            return
        self.samples, unknown = scan(folder)
        if not self.samples:
            self.load_msg.setText("No se encontraron archivos válidos en esa carpeta."); return
        key = hashlib.md5(folder.encode()).hexdigest()[:8]
        self.csv_path = Path.home() / ".lefai" / f"{Path(folder).name}_{key}.csv"
        if self.csv_path.exists():  # reanudar
            try:
                saved = progress.load(self.csv_path)
                for s in self.samples:
                    s.label = saved.get(s.id, "")
            except Exception as e:
                QMessageBox.warning(self, "Progreso", f"No se pudo leer el progreso anterior: {e}")
        inc = sum(1 for s in self.samples if s.missing)
        msg = f"{len(self.samples)} muestras · {len(self.samples) - inc} completas · {inc} incompletas"
        if unknown:
            msg += f"\nArchivos no reconocidos ({len(unknown)}): " + ", ".join(unknown[:8])
        QMessageBox.information(self, "Resumen", msg)
        self.stack.setCurrentIndex(1)
        self.first_pending()

    # ---------- visor ----------
    def goto(self, i):
        if 0 <= i < len(self.samples):
            self.idx = i
            s = self.samples[i]
            if self.ch not in s.files:
                self.ch = next(iter(s.files), "BF")
            self.refresh(fit=True, reload=True)

    def set_channel(self, c):
        if c in self.samples[self.idx].files:
            self.ch = c
            self.refresh(reload=True)
        else:
            self.ch_btns[c].setChecked(False)

    def cycle_channel(self, d):
        if self.stack.currentIndex() != 1:
            return
        order = ["BF", "G", "B"]
        avail = [c for c in order if c in self.samples[self.idx].files]
        if avail:
            cur = avail.index(self.ch) if self.ch in avail else -1
            self.set_channel(avail[(cur + d) % len(avail)])

    def refresh(self, fit=False, reload=False):
        s = self.samples[self.idx]
        done = sum(1 for x in self.samples if x.label)
        self.info.setText(f"<b>Muestra {s.id}</b> ({self.idx + 1} / {len(self.samples)})<br>"
                          f"{done} clasificadas, {len(self.samples) - done} pendientes<br>"
                          f"Etiqueta: <b>{s.label or 'pendiente'}</b>")
        self.warn.setText(f"Falta el canal {', '.join(s.missing)}" if s.missing else "")
        for c, b in self.ch_btns.items():
            b.setEnabled(c in s.files); b.setChecked(c == self.ch)
        for lab, b in self.lab_btns.items():
            b.setStyleSheet("font-weight:bold;border:3px solid #2563eb" if lab == s.label else "")
        if reload:
            self.norm = None
            if self.ch in s.files:
                try:
                    a = np.squeeze(tifffile.imread(s.files[self.ch]))
                    if a.ndim == 3 and a.shape[0] in (3, 4) and a.shape[-1] not in (3, 4):
                        a = np.moveaxis(a, 0, -1)      # (3,H,W) -> (H,W,3)
                    if a.ndim == 3 and a.shape[-1] in (3, 4):
                        a = a[..., :3]                  # RGB (se descarta alfa si lo hay)
                    elif a.ndim != 2:
                        raise ValueError(f"forma de imagen no soportada: {a.shape}")
                    self.norm = normalize(a)
                except Exception as e:
                    self.warn.setText(self.warn.text() + f"\nNo se pudo leer {s.files[self.ch].name}: {e}")
        self.render(fit)

    def render(self, fit=False):
        if self.norm is None:
            self.viewer.clear()
        else:
            self.viewer.show_array(apply_contrast(self.norm, self.slider.value()), fit)

    # ---------- clasificación ----------
    def set_label(self, label, advance=True):
        if self.stack.currentIndex() != 1:
            return
        if label and advance and self.samples[self.idx].label == label:
            label, advance = "", False  # quitar etiqueta si ya estaba puesta
        self.samples[self.idx].label = label
        progress.save(self.csv_path, self.samples)  # autoguardado
        if not advance:
            return self.refresh()
        nxt = next((i for i in list(range(self.idx + 1, len(self.samples))) + list(range(self.idx))
                    if not self.samples[i].label), None)
        if nxt is None:
            self.refresh(); self.finish()
        else:
            self.goto(nxt)

    def first_pending(self):
        self.goto(next((i for i, s in enumerate(self.samples) if not s.label), 0))

    def finish(self):
        counts = {}
        for s in self.samples:
            counts[s.label] = counts.get(s.label, 0) + 1
        txt = "\n".join(f"{k}: {v}" for k, v in counts.items())
        box = QMessageBox(self); box.setWindowTitle("Clasificación completada")
        box.setText(f"No quedan muestras pendientes.\n\n{txt}")
        z = box.addButton("Descargar ZIP + CSV", QMessageBox.AcceptRole)
        c = box.addButton("Solo CSV", QMessageBox.AcceptRole)
        box.addButton("Cerrar", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is z:
            self.download_zip()
        elif box.clickedButton() is c:
            self.download_csv()

    def download_csv(self):
        if not self.samples:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", "clasificaciones.csv", "CSV (*.csv)")
        if path:
            progress.save(path, self.samples)

    def download_zip(self):
        if not self.samples:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar ZIP", "clasificacion.zip", "ZIP (*.zip)")
        if not path:
            return
        try:
            pend = export_manager.export_zip(path, self.samples)
            QMessageBox.information(self, "ZIP", "ZIP creado." + (f"\n{pend} muestras pendientes no se han incluido en las carpetas." if pend else ""))
        except Exception as e:
            QMessageBox.warning(self, "ZIP", f"No se pudo crear el ZIP: {e}")


def run():
    app = QApplication([])
    w = MainWindow(); w.show()
    app.exec()
