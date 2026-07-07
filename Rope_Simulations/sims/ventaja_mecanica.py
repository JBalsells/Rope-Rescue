"""
Módulo · Ventaja mecánica simple (poleas) — PyQt5.

Muestra UN sistema de polea a la vez (1:1, 2:1, 3:1, 4:1 … como la lámina
clásica) y deja configurar la carga, la eficiencia y la altura a subir.
Calcula el esfuerzo (tensión en la cuerda) y cuánta cuerda hay que tirar.

  F_esfuerzo = carga / (n · eficiencia)      s = n · h   (conservación del trabajo)

Reutiliza physics.py. Anclaje (techo) fijo arriba; la carga cuelga del aparejo.
"""

import sys

from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPolygonF
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider,
    QDoubleSpinBox, QPushButton, QFrame, QSizePolicy, QButtonGroup)

from config import COLORS, G
from physics import weight_kn, pulley_effort, pulley_haul_distance
from registry import simulation

GOLD = '#f0c337'


def C(key):
    return QColor(COLORS[key])


# ── Control nativo (slider + casilla) ─────────────────────────────────
class Control(QWidget):
    changed = pyqtSignal()

    def __init__(self, label, lo, hi, init, step, decimals=0, color='primary'):
        super().__init__()
        self._step, self._lo = step, lo
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        lab = QLabel(label); lab.setMinimumWidth(122)
        lab.setStyleSheet(f'color:{COLORS[color]}; font-weight:bold;')
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, round((hi - lo) / step))
        self.slider.setValue(round((init - lo) / step))
        self.spin = QDoubleSpinBox(); self.spin.setRange(lo, hi)
        self.spin.setSingleStep(step); self.spin.setDecimals(decimals)
        self.spin.setValue(init); self.spin.setFixedWidth(74)
        lay.addWidget(lab); lay.addWidget(self.slider, 1); lay.addWidget(self.spin)
        self.slider.valueChanged.connect(self._fs)
        self.spin.valueChanged.connect(self._fp)

    def _fs(self, v):
        self.spin.blockSignals(True); self.spin.setValue(self._lo + v * self._step)
        self.spin.blockSignals(False); self.changed.emit()

    def _fp(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(round((v - self._lo) / self._step))
        self.slider.blockSignals(False); self.changed.emit()

    def value(self):
        return self.spin.value()


# ── Escena (QPainter): aparejo n:1 ────────────────────────────────────
class Scene(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(520, 520)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.s = None

    def paintEvent(self, _):
        st = self.s
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), C('bg'))
        if st is None:
            return
        n = st['ma']
        W, H = self.width(), self.height()
        rope = C('rope'); prim = C('primary')

        cx = W * 0.42
        y_ceil = 46
        y_fix = y_ceil + 34            # fila de poleas fijas
        lift = H * 0.34
        y_mov = y_fix + lift           # bloque móvil / poleas móviles
        span = 0 if n == 1 else min(30 * (n - 1), W * 0.40)
        xL = cx - span / 2.0
        xs = [cx] if n == 1 else [xL + i * span / (n - 1) for i in range(n)]
        xR = xs[-1]

        # ── Techo (viga rayada) ───────────────────────────────────────
        beam_l, beam_r = min(xs) - 36, max(xR + 80, xs[-1] + 36)
        p.setPen(QPen(C('anchor'), 3))
        p.drawLine(int(beam_l), y_ceil, int(beam_r), y_ceil)
        p.setPen(QPen(QColor(90, 110, 90), 1))
        for hx in range(int(beam_l), int(beam_r), 12):
            p.drawLine(hx, y_ceil - 10, hx + 8, y_ceil)

        # ── Poleas fijas (cuelgan del techo) ──────────────────────────
        for x in xs:
            p.setPen(QPen(prim, 2))
            p.drawLine(QPointF(x, y_ceil), QPointF(x, y_fix - 9))
            self._pulley(p, x, y_fix, 9, prim)

        # ── Strands (los n tramos que sostienen la carga) ─────────────
        p.setPen(QPen(rope, 4, Qt.SolidLine, Qt.RoundCap))
        if n == 1:
            # un solo cambio de dirección: carga a la izq, esfuerzo a la der
            load_x = cx - 18
            eff_x = cx + 18
            p.drawLine(QPointF(load_x, y_fix), QPointF(load_x, y_mov + 40))
            p.drawLine(QPointF(eff_x, y_fix), QPointF(eff_x, y_mov + 18))
            load_cx, load_top = load_x, y_mov + 40
            eff_x_final, eff_y_final = eff_x, y_mov + 18
        else:
            for x in xs:
                p.drawLine(QPointF(x, y_fix + 9), QPointF(x, y_mov))
            # bloque móvil
            p.setPen(QPen(prim, 2)); p.setBrush(QBrush(C('panel')))
            p.drawRoundedRect(QRectF(xL - 6, y_mov, span + 12, 14), 5, 5)
            for x in xs:
                self._pulley(p, x, y_mov + 7, 7, prim)
            # rope sale del tramo derecho hacia el esfuerzo (a la derecha)
            eff_x_final = xR + 70
            eff_y_final = y_fix + 70
            p.setPen(QPen(rope, 4, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(xR, y_fix), QPointF(eff_x_final, y_fix))
            p.drawLine(QPointF(eff_x_final, y_fix), QPointF(eff_x_final, eff_y_final))
            load_cx, load_top = cx, y_mov + 14

        # ── Carga (peso) ──────────────────────────────────────────────
        self._weight(p, load_cx, load_top + 18, st['load_kg'])
        # flecha F1 (carga, azul hacia abajo)
        self._force(p, load_cx, load_top + 78, +1, C('info'),
                    f"F₁ = {st['F1']:.2f} kN")

        # ── Esfuerzo F2 (rojo, tirás hacia abajo) ─────────────────────
        self._force(p, eff_x_final, eff_y_final, +1, C('danger'),
                    f"F₂ = {st['F2']:.2f} kN")

        # ── Cotas de distancia: h (carga) y s (cuerda a tirar) ────────
        p.setFont(QFont('monospace', 9))
        # h: lo que sube la carga
        hx = load_cx - (60 if n == 1 else span / 2 + 26)
        self._dim(p, hx, load_top + 4, hx, load_top + 4 + 34, C('info'),
                  f"h={st['h_cm']:.0f} cm")
        # s: lo que tirás (n·h) — proporcional, a la derecha del esfuerzo
        s_len = min(34 * n, H * 0.42)
        self._dim(p, eff_x_final + 26, eff_y_final - s_len,
                  eff_x_final + 26, eff_y_final, QColor(GOLD),
                  f"s={st['s_cm']:.0f} cm")

        # ── Rótulo del tipo ───────────────────────────────────────────
        p.setFont(QFont('monospace', 22, QFont.Bold))
        p.setPen(QPen(prim, 1))
        p.drawText(20, 40, f'{n}:1')

    # ── piezas ────────────────────────────────────────────────────────
    def _pulley(self, p, x, y, r, col):
        p.setPen(QPen(col, 2)); p.setBrush(QBrush(C('bg')))
        p.drawEllipse(QPointF(x, y), r, r)
        p.setBrush(QBrush(col)); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(x, y), 2.5, 2.5)

    def _weight(self, p, cx, top, kg):
        w, h = 46, 34
        poly = QPolygonF([QPointF(cx - w * 0.32, top), QPointF(cx + w * 0.32, top),
                          QPointF(cx + w * 0.5, top + h), QPointF(cx - w * 0.5, top + h)])
        p.setPen(QPen(C('text'), 2)); p.setBrush(QBrush(QColor(40, 40, 48)))
        p.drawPolygon(poly)
        # gancho
        p.setPen(QPen(C('warning'), 2)); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, top - 4), 4, 4)
        p.setFont(QFont('monospace', 9))
        p.setPen(QPen(C('text'), 1))
        p.drawText(int(cx) - 20, int(top) + h + 14, f'{kg:.0f} kg')

    def _force(self, p, x, y, sign, col, label):
        p.setPen(QPen(col, 3, Qt.SolidLine, Qt.RoundCap))
        y2 = y + sign * 30
        p.drawLine(QPointF(x, y), QPointF(x, y2))
        p.setBrush(QBrush(col)); p.setPen(Qt.NoPen)
        p.drawPolygon(QPointF(x, y2 + sign * 6), QPointF(x - 5, y2),
                      QPointF(x + 5, y2))
        p.setFont(QFont('monospace', 10, QFont.Bold)); p.setPen(QPen(col, 1))
        p.drawText(int(x) + 8, int(y) + 18, label)

    def _dim(self, p, x1, y1, x2, y2, col, label):
        p.setPen(QPen(col, 1, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        for yy in (y1, y2):
            p.drawLine(QPointF(x1 - 4, yy), QPointF(x1 + 4, yy))
        p.setFont(QFont('monospace', 9)); p.setPen(QPen(col, 1))
        p.drawText(int(x1) + 7, int((y1 + y2) / 2) + 4, label)


# ── Ventana principal ─────────────────────────────────────────────────
class VentajaSim(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Ventaja mecánica (poleas)  —  PyQt')
        self.resize(1180, 700)
        self.setStyleSheet(QSS)
        self.ma = 2
        self.scene = Scene()
        root = QHBoxLayout(self)
        root.addWidget(self.scene, 1)
        root.addWidget(self._build_panel())
        self._recompute()

    def _build_panel(self):
        panel = QFrame(); panel.setObjectName('panel'); panel.setFixedWidth(380)
        v = QVBoxLayout(panel); v.setSpacing(9)
        t = QLabel('Ventaja mecánica'); t.setStyleSheet(
            f'color:{COLORS["primary"]}; font-size:20px; font-weight:bold;')
        v.addWidget(t)

        # Tipo de VM (botones)
        row = QVBoxLayout()
        row.addWidget(QLabel('Tipo de aparejo:'))
        bl = QHBoxLayout()
        self.grp = QButtonGroup(self); self.btns = []
        for n in (1, 2, 3, 4, 5, 6):
            b = QPushButton(f'{n}:1'); b.setCheckable(True)
            b.setChecked(n == self.ma)
            b.clicked.connect(lambda _c, val=n: self._set_ma(val))
            self.grp.addButton(b); self.btns.append((n, b)); bl.addWidget(b)
        row.addLayout(bl); v.addLayout(row)

        self.c_load = Control('Carga (kg)', 10, 500, 100, 5, 0, 'info')
        self.c_eff  = Control('Eficiencia (%)', 50, 100, 100, 1, 0, 'accent')
        self.c_h    = Control('Subir carga (cm)', 5, 100, 10, 1, 0, 'secondary')
        for c in (self.c_load, self.c_eff, self.c_h):
            c.changed.connect(self._recompute); v.addWidget(c)

        v.addSpacing(6)
        self.out = QLabel(); self.out.setTextFormat(Qt.RichText)
        self.out.setAlignment(Qt.AlignTop)
        v.addWidget(self.out)
        v.addStretch(1)
        return panel

    def _set_ma(self, n):
        self.ma = n
        for val, b in self.btns:
            b.setChecked(val == n)
        self._recompute()

    def _recompute(self):
        n = self.ma
        kg = self.c_load.value(); eff = self.c_eff.value() / 100.0
        h_cm = self.c_h.value()
        F1 = weight_kn(kg)
        F2 = pulley_effort(F1, n, eff)
        s_cm = pulley_haul_distance(h_cm, n)

        self.scene.s = {'ma': n, 'load_kg': kg, 'F1': F1, 'F2': F2,
                        'h_cm': h_cm, 's_cm': s_cm}
        self.scene.update()

        prim, info, dang = COLORS['primary'], COLORS['info'], COLORS['danger']
        gain = F1 / F2 if F2 > 0 else 0
        self.out.setText(
            f"<b style='color:{prim}'>Aparejo {n}:1</b><br>"
            f"Tramos que sostienen la carga: <b>{n}</b><br><br>"
            f"<b style='color:{prim}'>Fuerzas</b><br>"
            f"Carga (F₁): <b style='color:{info}'>{F1:.2f} kN</b> ({kg:.0f} kg)<br>"
            f"Esfuerzo (F₂): <b style='color:{dang}'>{F2:.2f} kN</b> "
            f"({F2*1000/G:.0f} kg)<br>"
            f"Reduce la fuerza <b>×{gain:.1f}</b><br><br>"
            f"<b style='color:{prim}'>Distancias (se conserva el trabajo)</b><br>"
            f"Para subir la carga <b>{h_cm:.0f} cm</b><br>"
            f"tenés que tirar <b style='color:{GOLD}'>{s_cm:.0f} cm</b> de cuerda<br><br>"
            f"<b style='color:{prim}'>Eficiencia</b><br>"
            f"{self.c_eff.value():.0f}% "
            f"{'(ideal, sin fricción)' if eff >= 0.999 else '(con fricción)'}")


QSS = f"""
QWidget {{ background-color: {COLORS['bg']}; color: {COLORS['text']};
           font-family: monospace; font-size: 13px; }}
QFrame#panel {{ background-color: {COLORS['panel']}; border-radius: 10px; }}
QSlider::groove:horizontal {{ height: 6px; background: #2a3a2a; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {COLORS['primary']}; width: 13px;
           margin: -5px 0; border-radius: 6px; }}
QSlider::sub-page:horizontal {{ background: {COLORS['primary']}; border-radius: 3px; }}
QDoubleSpinBox {{ background: {COLORS['bg']}; border: 1px solid {COLORS['grid']};
           border-radius: 4px; padding: 1px; color: {COLORS['text']}; }}
QPushButton {{ background: #16241a; border: 1px solid {COLORS['grid']};
           border-radius: 6px; padding: 5px 6px; }}
QPushButton:checked {{ background: {COLORS['accent']}; color: {COLORS['bg']};
           font-weight: bold; }}
"""


@simulation(backend='qt', order=10,
            title='Ventaja mecánica (poleas)',
            description='Aparejos 1:1, 2:1, 3:1… esfuerzo y distancia.')
def main():
    app = QApplication.instance() or QApplication(sys.argv)
    w = VentajaSim()
    w.show()
    app.exec_()


if __name__ == '__main__':
    main()
