"""
Módulo 21 · Sistema English Reeve (PyQt5).

Tirolesa de rescate controlada. Visualización del montaje real (polea de
travesía → placa de reparto → bagas absorbedoras en V → mosquetón máster →
víctima) con QPainter antialiased y extremos redondeados, y panel nativo con
los números esenciales (tensiones, VM, cargas). Reutiliza physics.py.

Anclajes a nivel (Vano A–B); controles: posición, carga, vano, flecha,
cuelgue, y la ventaja mecánica (VM) horizontal y vertical.
"""

import sys

from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPainterPath
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider,
    QDoubleSpinBox, QPushButton, QFrame, QSizePolicy, QButtonGroup)

import math
from config import COLORS, G
from physics import rope_length_for_sag, solve_load_y, tyrolean_forces, weight_kn
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
        lab = QLabel(label); lab.setMinimumWidth(118)
        lab.setStyleSheet(f'color:{COLORS[color]}; font-weight:bold;')
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, round((hi - lo) / step))
        self.slider.setValue(round((init - lo) / step))
        self.spin = QDoubleSpinBox(); self.spin.setRange(lo, hi)
        self.spin.setSingleStep(step); self.spin.setDecimals(decimals)
        self.spin.setValue(init); self.spin.setFixedWidth(72)
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


# ── Escena (QPainter) ─────────────────────────────────────────────────
class Scene(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(560, 520)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.s = None

    def paintEvent(self, _):
        st = self.s
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), C('bg'))
        if st is None:
            return
        W_px, H_px = self.width(), self.height()
        span, hA, yP, drop = st['span'], st['hA'], st['yP'], st['drop']

        # Encuadre fijo (no depende de la posición de la carga)
        top_m = max(hA, 0.0) + 1.0
        bot_m = (hA / 2.0 - st['d']) - drop - 1.5
        Lx, Rx = 70, W_px - 70
        Ty, By = 70, H_px - 70
        ppm = min((Rx - Lx) / max(span, 1.0), (By - Ty) / max(top_m - bot_m, 1.0))

        def X(m):
            return Lx + m * ppm

        def Y(m):
            return Ty + (top_m - m) * ppm

        ax, ay = X(0), Y(hA)
        bx, by = X(span), Y(0.0)
        cx, cy = X(st['x']), Y(yP)
        master_y = cy + 30
        vic_y = Y(yP - drop)

        # ── Acantilados ───────────────────────────────────────────────
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(26, 38, 28)))
        p.drawRect(0, int(ay) + 8, int(ax) + 30, H_px)
        p.drawRect(int(bx) - 30, int(by) + 8, W_px, H_px)
        p.setPen(QPen(QColor(60, 90, 60), 2))
        p.drawLine(0, int(ay) + 8, int(ax) + 30, int(ay) + 8)
        p.drawLine(int(bx) - 30, int(by) + 8, W_px, int(by) + 8)
        # abismo
        p.setPen(QPen(QColor(40, 60, 40), 1))
        for hx in range(0, W_px, 26):
            p.drawLine(hx, By + 8, hx + 16, By + 20)
        p.setFont(QFont('monospace', 8))
        p.setPen(QPen(C('anchor'), 1))
        p.drawText(W_px // 2 - 40, By + 24, 'CAÑÓN / ABISMO')

        # ── Belay (independiente, verde) ──────────────────────────────
        belay = QColor(C('accent')); belay.setAlpha(200)
        p.setPen(QPen(belay, 3, Qt.SolidLine, Qt.RoundCap))
        path = QPainterPath(QPointF(ax + 6, ay))
        path.lineTo(cx - 16, cy - 4)
        path.lineTo(cx - 16, vic_y)
        p.drawPath(path)

        # ── Highline (A → carro → B), tensa = recta, extremos redondos ─
        p.setPen(QPen(C('rope'), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline(QPointF(ax, ay), QPointF(cx, cy), QPointF(bx, by))

        # ── Línea de control / haul (azul) hacia B ────────────────────
        p.setPen(QPen(C('info'), 2.5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx, cy), QPointF(bx + 6, by - 26))
        self._pulley(p, bx + 6, by - 26, 6, C('info'))

        # ── Anclajes ──────────────────────────────────────────────────
        self._anchor(p, ax, ay, 'A', C('warning'))
        self._anchor(p, bx, by, 'B', C('info'))

        # ── Carro: polea → placa → bagas en V → máster ────────────────
        self._carriage(p, cx, cy, master_y)

        # ── Línea vertical de izado (dorada) al máster/víctima ────────
        p.setPen(QPen(QColor(GOLD), 4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx, master_y), QPointF(cx, vic_y))

        # ── Víctima en camilla ────────────────────────────────────────
        self._victim(p, cx, vic_y, st['load_kg'])

        # ── Flecha de peso ────────────────────────────────────────────
        p.setPen(QPen(C('danger'), 3, Qt.SolidLine, Qt.RoundCap))
        wy = vic_y + 34
        p.drawLine(QPointF(cx, wy), QPointF(cx, wy + 26))
        self._arrowhead(p, cx, wy + 26, 0, 1, C('danger'))
        p.setFont(QFont('monospace', 9, QFont.Bold))
        p.setPen(QPen(C('danger'), 1))
        p.drawText(int(cx) + 8, int(wy) + 20, f"{st['W']:.2f} kN")

    # ── piezas de rigging ─────────────────────────────────────────────
    def _pulley(self, p, x, y, r, col):
        p.setPen(QPen(col, 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(x, y), r, r)
        p.setBrush(QBrush(col))
        p.drawEllipse(QPointF(x, y), 2, 2)

    def _anchor(self, p, x, y, letra, col):
        p.setPen(QPen(C('text'), 2))
        p.setBrush(QBrush(col))
        d = 11
        p.drawPolygon(QPointF(x, y - d), QPointF(x + d, y),
                      QPointF(x, y + d), QPointF(x - d, y))
        p.setPen(QPen(C('bg'), 1))
        p.setFont(QFont('monospace', 10, QFont.Bold))
        p.drawText(QRectF(x - d, y - d, 2 * d, 2 * d), Qt.AlignCenter, letra)
        p.setPen(QPen(col, 1))
        p.setFont(QFont('monospace', 9, QFont.Bold))
        p.drawText(int(x) - 30, int(y) - 18, f'Anclaje {letra}')

    def _carriage(self, p, cx, cy, master_y):
        prim = C('primary')
        # polea de travesía (rueda con surco)
        p.setPen(QPen(prim, 3)); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 11, 11)
        p.setBrush(QBrush(prim)); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), 3, 3)
        # enlace a la placa
        plate_y = cy + 16
        p.setPen(QPen(prim, 2))
        p.drawLine(QPointF(cx, cy + 11), QPointF(cx, plate_y - 4))
        # placa de reparto (naranja, con orificios)
        p.setBrush(QBrush(C('secondary'))); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(cx - 12, plate_y - 5, 24, 11), 4, 4)
        p.setBrush(QBrush(C('bg')))
        for ddx in (-6, 0, 6):
            p.drawEllipse(QPointF(cx + ddx, plate_y), 2, 2)
        # bagas absorbedoras en V (doradas, gruesas, redondeadas)
        p.setPen(QPen(QColor(GOLD), 5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx - 8, plate_y + 6), QPointF(cx, master_y))
        p.drawLine(QPointF(cx + 8, plate_y + 6), QPointF(cx, master_y))
        # mosquetón máster (argolla)
        p.setPen(QPen(prim, 2)); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, master_y), 5, 5)

    def _victim(self, p, cx, top_y, kg):
        w, h = 78, 30
        # camilla
        p.setPen(QPen(C('danger'), 2)); p.setBrush(QBrush(QColor(70, 22, 22)))
        p.drawRoundedRect(QRectF(cx - w / 2, top_y, w, h), 7, 7)
        # persona (cabeza + cuerpo) recostada
        p.setBrush(QBrush(C('text'))); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx - w / 2 + 13, top_y + h / 2), 6, 6)
        p.setPen(QPen(C('text'), 5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx - w / 2 + 19, top_y + h / 2),
                   QPointF(cx + w / 2 - 12, top_y + h / 2))
        # peso
        p.setPen(QPen(C('warning'), 1))
        p.setFont(QFont('monospace', 9))
        p.drawText(int(cx) - 18, int(top_y) + h + 14, f'{kg:.0f} kg')

    def _arrowhead(self, p, x, y, ux, uy, col):
        p.setBrush(QBrush(col)); p.setPen(Qt.NoPen)
        px, py = -uy, ux
        p.drawPolygon(QPointF(x, y),
                      QPointF(x - ux * 9 + px * 5, y - uy * 9 + py * 5),
                      QPointF(x - ux * 9 - px * 5, y - uy * 9 - py * 5))


# ── Ventana principal ─────────────────────────────────────────────────
class ReeveSim(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('English Reeve  —  PoC PyQt')
        self.resize(1320, 760)
        self.setStyleSheet(QSS)
        self.ma_h = 4
        self.ma_v = 3

        self.scene = Scene()
        root = QHBoxLayout(self)
        root.addWidget(self.scene, 1)
        root.addWidget(self._build_panel())
        self._recompute()

    def _build_panel(self):
        panel = QFrame(); panel.setObjectName('panel'); panel.setFixedWidth(400)
        v = QVBoxLayout(panel); v.setSpacing(8)
        t = QLabel('English Reeve'); t.setStyleSheet(
            f'color:{COLORS["primary"]}; font-size:20px; font-weight:bold;')
        v.addWidget(t)

        self.c_pos  = Control('Posición (%)', 2, 98, 50, 1, 0, 'info')
        self.c_load = Control('Carga (kg)', 40, 300, 120, 5, 0, 'danger')
        self.c_span = Control('Vano A–B (m)', 15, 80, 40, 1, 0, 'primary')
        self.c_sag  = Control('Flecha (%)', 1, 12, 5, 0.5, 1, 'secondary')
        self.c_drop = Control('Cuelgue (m)', 0, 15, 8, 0.5, 1)
        for c in (self.c_pos, self.c_load, self.c_span, self.c_sag,
                  self.c_drop):
            c.changed.connect(self._recompute); v.addWidget(c)

        # VM (botones)
        for txt, opts, attr in [('VM horizontal:', (3, 4, 6), 'ma_h'),
                                 ('VM vertical:', (2, 3, 4), 'ma_v')]:
            row = QHBoxLayout(); row.addWidget(QLabel(txt))
            grp = QButtonGroup(self)
            for o in opts:
                b = QPushButton(f'{o}:1'); b.setCheckable(True)
                b.setChecked(getattr(self, attr) == o)
                b.clicked.connect(lambda _c, a=attr, val=o: self._set_ma(a, val))
                grp.addButton(b); row.addWidget(b)
            v.addLayout(row)

        v.addSpacing(6)
        self.out = QLabel(); self.out.setTextFormat(Qt.RichText)
        self.out.setAlignment(Qt.AlignTop)
        v.addWidget(self.out)
        v.addStretch(1)
        return panel

    def _set_ma(self, attr, val):
        setattr(self, attr, val)
        # actualizar checks del grupo
        for b in self.findChildren(QPushButton):
            pass
        self._recompute()

    def _recompute(self):
        span = self.c_span.value(); hA = 0.0   # anclajes a nivel
        load = self.c_load.value(); drop = self.c_drop.value()
        d = self.c_sag.value() / 100.0 * span
        S = rope_length_for_sag(span, hA, 0.0, d)
        x = self.c_pos.value() / 100.0 * span
        yP = solve_load_y(x, span, hA, 0.0, S)
        W = weight_kn(load)
        f = tyrolean_forces(x, span, hA, 0.0, yP, W)
        v = f['v_angle']
        F_haul = W * math.sin(math.radians(abs(f['alpha_B']))) / self.ma_h
        F_vert = W / self.ma_v

        self.scene.s = {'span': span, 'hA': hA, 'x': x, 'yP': yP, 'd': d,
                        'drop': drop, 'load_kg': load, 'W': W}
        self.scene.update()

        v_col = (COLORS['accent'] if v < 120 else
                 COLORS['warning'] if v < 150 else COLORS['danger'])
        warn = COLORS['warning']
        self.out.setText(
            f"<b style='color:{COLORS['primary']}'>Tensiones highline</b><br>"
            f"T_A (A→carro): <b style='color:{warn}'>{f['T_A']:.2f} kN</b><br>"
            f"T_B (carro→B): <b style='color:{warn}'>{f['T_B']:.2f} kN</b><br>"
            f"Ángulo V: <b style='color:{v_col}'>{v:.0f}°</b><br><br>"
            f"<b style='color:{COLORS['primary']}'>Fuerza para operar</b><br>"
            f"Tirar (horiz.): <b style='color:{COLORS['info']}'>{F_haul:.2f} kN "
            f"({F_haul*1000/G:.0f} kg)</b><br>"
            f"Izar (vert.): <b style='color:{GOLD}'>{F_vert:.2f} kN "
            f"({F_vert*1000/G:.0f} kg)</b><br><br>"
            f"<b style='color:{COLORS['primary']}'>Cargas en anclajes</b><br>"
            f"Anclaje A: <b style='color:{warn}'>{f['T_A']:.2f} kN</b><br>"
            f"Anclaje B: <b style='color:{warn}'>{f['T_B']:.2f} kN</b><br>"
            f"Belay: <b style='color:{COLORS['accent']}'>{W:.2f} kN</b>")


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
           border-radius: 6px; padding: 4px 8px; }}
QPushButton:checked {{ background: {COLORS['accent']}; color: {COLORS['bg']};
           font-weight: bold; }}
"""


@simulation(backend='qt', order=9,
            title='Sistema English Reeve (Qt)',
            description='Tirolesa de rescate controlada: carro, VM y cargas.')
def main():
    app = QApplication.instance() or QApplication(sys.argv)
    w = ReeveSim()
    w.show()
    app.exec_()


if __name__ == '__main__':
    main()
