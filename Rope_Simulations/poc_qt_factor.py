"""
PRUEBA DE CONCEPTO (completa) — Factor de caída en PyQt5.

Port fiel del módulo pygame `sims/factor_de_caida.py`, con TODAS sus funciones:
  • Animación de la caída (caída libre → impacto → oscilación amortiguada).
  • Estela del escalador y etiqueta de velocidad durante la caída.
  • Gráfico de TENSIÓN en tiempo real (curva amortiguada, líneas mg/UIAA/pico).
  • Fuerza de impacto DINÁMICA y ESTÁTICA simultáneas (+ kg equivalentes).
  • Velocidad de impacto, distancia y aceleración de frenado, fuerzas-G.
  • Dos barras de fuerza vs MBS con marcas UIAA/rotura.
  • Semáforo de seguridad y texto narrativo del estado.
  • Tabla comparativa de los 4 escenarios (FF 0.25 / 0.5 / 1 / 2).
  • Presets FF, Soltar, Reiniciar, Cámara lenta, Pausa.
Reutiliza physics/config sin tocar el núcleo. Controles NATIVOS de Qt.

Correr:  python3 poc_qt_factor.py
"""

import math
import sys

from PyQt5.QtCore import Qt, QTimer, QPointF, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPolygonF
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel,
    QSlider, QDoubleSpinBox, QPushButton, QCheckBox, QFrame, QSizePolicy,
    QButtonGroup)

from config import COLORS, G, UIAA_MAX_IMPACT, ROPE_STATIC_MBS

EPS_DYN, EPS_STA = 0.35, 0.03
GRAPH_SECONDS = 5.0
MAX_TRAIL = 90
SCENARIOS = [(0.25, 'FF 0.25 — Caída corta'), (0.5, 'FF 0.50 — Caída moderada'),
             (1.0, 'FF 1.0 — Nivel del anclaje'), (2.0, 'FF 2.0 — Factor máximo')]


def C(key):
    return QColor(COLORS[key])


def fall_results(mass, rope, ff):
    """Toda la física del impacto (igual que el original), como dict."""
    fall = ff * rope
    mg = mass * G / 1000.0
    return {
        'fall': fall, 'mg': mg,
        'speed': math.sqrt(2 * G * fall),
        'f_dyn': mass * G * (1 + ff / EPS_DYN) / 1000.0,
        'f_sta': mass * G * (1 + ff / EPS_STA) / 1000.0,
        'g_dyn': 1 + ff / EPS_DYN,
        'g_sta': 1 + ff / EPS_STA,
        'a_dyn': G * ff / EPS_DYN,
        'a_sta': G * ff / EPS_STA,
        'bd_dyn': EPS_DYN * rope,
        'bd_sta': EPS_STA * rope,
    }


# ══════════════════════════════════════════════════════════════════════
#  Control nativo: etiqueta + slider + casilla editable (enlazados)
# ══════════════════════════════════════════════════════════════════════

class Control(QWidget):
    changed = pyqtSignal()

    def __init__(self, label, lo, hi, init, step, decimals=1, color='primary'):
        super().__init__()
        self._step, self._lo = step, lo
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lab = QLabel(label)
        lab.setMinimumWidth(110)
        lab.setStyleSheet(f'color:{COLORS[color]}; font-weight:bold;')
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, round((hi - lo) / step))
        self.slider.setValue(round((init - lo) / step))
        self.spin = QDoubleSpinBox()
        self.spin.setRange(lo, hi)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(decimals)
        self.spin.setValue(init)
        self.spin.setFixedWidth(78)
        lay.addWidget(lab)
        lay.addWidget(self.slider, 1)
        lay.addWidget(self.spin)
        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect(self._from_spin)

    def _from_slider(self, v):
        self.spin.blockSignals(True)
        self.spin.setValue(self._lo + v * self._step)
        self.spin.blockSignals(False)
        self.changed.emit()

    def _from_spin(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(round((v - self._lo) / self._step))
        self.slider.blockSignals(False)
        self.changed.emit()

    def value(self):
        return self.spin.value()


# ══════════════════════════════════════════════════════════════════════
#  Escena (QPainter): caída, estela, cuerda, escalador, marcadores
# ══════════════════════════════════════════════════════════════════════

class Scene(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(440, 430)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.s = None        # estado del controlador

    def paintEvent(self, _):
        st = self.s
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), C('bg'))
        if st is None:
            return

        H = self.height()
        wall_x, climber_x = 120, 190
        top_m = min(st['start_m'], 0.0) - 0.4
        bot_m = st['end_m'] + 0.8
        scale = max(8.0, (H - 90) / max(bot_m - top_m, 0.5))
        y0 = 55

        def ypx(m):
            return int(y0 + (m - top_m) * scale)

        # pared
        p.fillRect(wall_x - 32, ypx(top_m), 32, H, QColor(20, 34, 20))
        p.setPen(QPen(C('anchor'), 1))
        for yy in range(ypx(top_m), H, 22):
            p.drawLine(wall_x - 32, yy, wall_x, yy)

        # anclaje (m = 0)
        anc = QPointF(wall_x, ypx(0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(C('anchor')))
        p.drawEllipse(anc, 11, 11)
        p.setBrush(QBrush(C('warning')))
        p.drawEllipse(anc, 5, 5)
        p.setPen(QPen(C('anchor'), 1))
        p.setFont(QFont('monospace', 9))
        p.drawText(wall_x - 28, ypx(0) - 16, 'ANCLAJE')

        # estela
        n = len(st['trail'])
        for i, m in enumerate(st['trail']):
            r = i / max(n - 1, 1)
            col = QColor(int(50 + r * (C('rope').red() - 50)),
                         int(30 + r * (C('rope').green() - 30)),
                         int(8 + r * (C('rope').blue() - 8)))
            p.setBrush(QBrush(col))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(climber_x, ypx(m)), max(1, r * 3), max(1, r * 3))

        # cuerda (color por intensidad de impacto)
        cy = ypx(st['climber_m'])
        climber = QPointF(climber_x, cy)
        if st['impact']:
            it = st['intensity']
            rope_col = QColor(int(255 * it + C('rope').red() * (1 - it)),
                              int(C('rope').green() * (1 - it)),
                              int(C('rope').blue() * (1 - it)))
        else:
            rope_col = C('rope')
        p.setPen(QPen(rope_col, 3))
        p.drawLine(anc, climber)

        # marcadores inicio / fin / distancia y largo de cuerda
        p.setFont(QFont('monospace', 9))
        p.setPen(QPen(C('accent'), 1))
        p.drawLine(climber_x + 24, ypx(st['start_m']), climber_x + 54, ypx(st['start_m']))
        p.drawText(climber_x + 58, ypx(st['start_m']) + 4, 'inicio')
        p.setPen(QPen(C('danger'), 1))
        p.drawLine(climber_x + 24, ypx(st['end_m']), climber_x + 54, ypx(st['end_m']))
        p.drawText(climber_x + 58, ypx(st['end_m']) + 4, 'fin de caída')
        # flecha de distancia de caída
        ax = climber_x + 110
        p.setPen(QPen(C('warning'), 2))
        p.drawLine(ax, ypx(st['start_m']), ax, ypx(st['end_m']))
        p.drawText(ax + 8, (ypx(st['start_m']) + ypx(st['end_m'])) // 2,
                   f"d = {st['fall']:.1f} m")
        # largo de cuerda L (de anclaje a fin)
        lx = wall_x - 52
        p.setPen(QPen(C('info'), 2))
        p.drawLine(lx, ypx(0), lx, ypx(st['end_m']))
        p.drawText(lx - 4, ypx(st['end_m']) + 16, f"L={st['rope']:.1f}m")

        # escalador
        col = C('primary') if not st['impact'] else C('warning')
        p.setPen(QPen(col, 3))
        p.setBrush(QBrush(col))
        p.drawEllipse(QPointF(climber_x, cy - 24), 9, 9)
        p.drawLine(climber_x, cy - 15, climber_x, cy + 10)
        p.drawLine(climber_x - 14, cy - 6, climber_x + 14, cy - 6)
        p.drawLine(climber_x, cy + 10, climber_x - 10, cy + 28)
        p.drawLine(climber_x, cy + 10, climber_x + 10, cy + 28)

        # velocidad durante la caída
        if st['falling'] and not st['impact'] and st['velocity'] > 0.5:
            p.setPen(QPen(C('danger'), 1))
            p.setFont(QFont('monospace', 10, QFont.Bold))
            p.drawText(climber_x + 22, cy,
                       f"↓ {st['velocity']:.1f} m/s ({st['velocity']*3.6:.0f} km/h)")


# ══════════════════════════════════════════════════════════════════════
#  Gráfico de tensión en tiempo real
# ══════════════════════════════════════════════════════════════════════

class TensionGraph(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(185)
        self.hist = []
        self.peak = 0.0
        self.mg = 1.0

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(10, 16, 12))
        p.setPen(QPen(C('grid'), 1))
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        p.setFont(QFont('monospace', 9))
        p.setPen(QPen(C('primary'), 1))
        p.drawText(48, 16, 'Tensión de la cuerda (kN) — tiempo real')

        pad_l, pad_r, pad_t, pad_b = 44, 12, 24, 22
        x0, x1 = pad_l, self.width() - pad_r
        y0, y1 = pad_t, self.height() - pad_b
        pw, ph = x1 - x0, y1 - y0
        max_y = max(self.peak * 1.15, self.mg * 2.5, 3.0)

        def sy(kn):
            return int(y1 - kn / max_y * ph)

        for kn in [0, self.mg, 6.0, 9.0, 12.0]:
            if kn > max_y:
                continue
            col = (C('danger') if kn == 12.0 else
                   C('accent') if abs(kn - self.mg) < 0.05 else C('grid'))
            p.setPen(QPen(col, 1))
            p.drawLine(x0, sy(kn), x1, sy(kn))
            p.setPen(QPen(C('anchor') if kn != 12.0 else C('danger'), 1))
            p.drawText(4, sy(kn) + 4, f'{kn:.1f}')
        if max_y >= 12.0:
            p.setPen(QPen(C('danger'), 1))
            p.drawText(x1 - 64, sy(12.0) - 4, 'UIAA 12')

        if len(self.hist) >= 2:
            t_min, t_max = self.hist[0][0], self.hist[-1][0]
            span = max(t_max - t_min, 1e-3)

            def sx(t):
                return int(x0 + (t - t_min) / span * pw)
            for i in range(len(self.hist) - 1):
                kn = self.hist[i + 1][1]
                col = (C('accent') if kn < 6 else C('warning') if kn < 9 else C('danger'))
                p.setPen(QPen(col, 2))
                p.drawLine(sx(self.hist[i][0]), max(y0, min(y1, sy(self.hist[i][1]))),
                           sx(self.hist[i + 1][0]), max(y0, min(y1, sy(self.hist[i + 1][1]))))
            t, kn = self.hist[-1]
            col = (C('accent') if kn < 6 else C('warning') if kn < 9 else C('danger'))
            p.setBrush(QBrush(col))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(sx(t), max(y0, min(y1, sy(kn)))), 4, 4)
        if self.peak > 0:
            p.setPen(QPen(QColor(150, 150, 180), 1))
            p.drawLine(x0, sy(min(self.peak, max_y)), x1, sy(min(self.peak, max_y)))
            p.setPen(QPen(QColor(180, 180, 210), 1))
            p.drawText(x0 + 4, sy(min(self.peak, max_y)) - 3, f'pico {self.peak:.1f} kN')
        p.setPen(QPen(C('text'), 1))
        p.drawText(x0 + pw // 2 - 40, y1 + 16, f'últimos {GRAPH_SECONDS:.0f} s →')


# ══════════════════════════════════════════════════════════════════════
#  Semáforo
# ══════════════════════════════════════════════════════════════════════

class Semaforo(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(96, 150)
        self.state = None

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx = self.width() // 2
        p.setBrush(QBrush(QColor(25, 25, 35)))
        p.setPen(QPen(C('grid'), 1))
        p.drawRoundedRect(cx - 17, 0, 34, 116, 6, 6)
        lights = [('red', 22, C('danger'), QColor(70, 15, 15)),
                  ('yellow', 56, C('warning'), QColor(55, 45, 8)),
                  ('green', 90, C('accent'), QColor(12, 45, 15))]
        for name, cy, bright, dim in lights:
            p.setBrush(QBrush(bright if self.state == name else dim))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx, cy), 13, 13)
        labels = {'green': ('SEGURO', C('accent')), 'yellow': ('PRECAUCIÓN', C('warning')),
                  'red': ('PELIGROSO', C('danger')), None: ('EN ESPERA', C('grid'))}
        txt, col = labels[self.state]
        p.setPen(QPen(col, 1))
        p.setFont(QFont('monospace', 8, QFont.Bold))
        p.drawText(0, 132, self.width(), 16, Qt.AlignCenter, txt)


# ══════════════════════════════════════════════════════════════════════
#  Barra de fuerza (0..MBS) con marcas UIAA/rotura
# ══════════════════════════════════════════════════════════════════════

class ForceBar(QWidget):
    def __init__(self, tag):
        super().__init__()
        self.setFixedHeight(26)
        self.tag, self.val = tag, 0.0

    def set(self, v):
        self.val = v
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(30, 40, 30))
        frac = min(self.val / ROPE_STATIC_MBS, 1.0)
        col = (C('accent') if self.val < 6 else
               C('warning') if self.val < UIAA_MAX_IMPACT else C('danger'))
        p.fillRect(0, 0, int(self.width() * frac), self.height(), col)
        p.setPen(QPen(C('text'), 1))
        p.setFont(QFont('monospace', 9, QFont.Bold))
        p.drawText(6, 17, f'{self.tag}: {self.val:.1f} kN')
        p.setPen(QPen(QColor(150, 150, 150), 1))
        for kn in (UIAA_MAX_IMPACT, ROPE_STATIC_MBS):
            x = int(self.width() * kn / ROPE_STATIC_MBS)
            p.drawLine(x, 0, x, self.height())


# ══════════════════════════════════════════════════════════════════════
#  Ventana principal / controlador
# ══════════════════════════════════════════════════════════════════════

class FallSim(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Factor de caída  —  PoC PyQt (completa)')
        self.resize(1320, 880)
        self.setStyleSheet(QSS)

        self.ff = 1.0
        self.scenario_label = SCENARIOS[2][1]
        self._reset_state()

        self.scene = Scene()
        self.graph = TensionGraph()
        left = QVBoxLayout()
        left.addWidget(self.scene, 1)
        left.addWidget(self.graph)

        root = QHBoxLayout(self)
        root.addLayout(left, 1)
        root.addWidget(self._build_panel())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)
        self._recompute()

    def _reset_state(self):
        rope = self.c_rope.value() if hasattr(self, 'c_rope') else 2.0
        self.rope = rope
        self.fall = self.ff * rope
        self.start_m = rope - self.fall
        self.end_m = rope
        self.climber_m = self.start_m
        self.velocity = 0.0
        self.falling = False
        self.impact = False
        self.t_impact = 0.0
        self.bounce_phase = 0.0
        self.sim_time = 0.0
        self.trail = []
        self.hist = []

    # ── panel ─────────────────────────────────────────────────────────
    def _build_panel(self):
        panel = QFrame()
        panel.setObjectName('panel')
        panel.setFixedWidth(440)
        v = QVBoxLayout(panel)
        v.setSpacing(7)

        self.lbl_scn = QLabel(self.scenario_label)
        self.lbl_scn.setStyleSheet(f'color:{COLORS["primary"]}; font-size:19px; font-weight:bold;')
        v.addWidget(self.lbl_scn)

        self.c_mass = Control('Peso (kg)', 20, 200, 100, 1, 0, 'primary')
        self.c_rope = Control('Cuerda (m)', 1, 8, 2, 0.5, 1, 'rope')
        for c in (self.c_mass, self.c_rope):
            c.changed.connect(self._on_control)
            v.addWidget(c)

        # presets de factor de caída
        row = QHBoxLayout()
        row.addWidget(QLabel('Escenario:'))
        self.scn_group = QButtonGroup(self)
        self.scn_buttons = []
        for i, (ff, _) in enumerate(SCENARIOS):
            b = QPushButton(f'FF {ff:g}')
            b.setCheckable(True)
            b.setChecked(abs(ff - self.ff) < 1e-3)
            b.clicked.connect(lambda _c, f=ff: self._set_ff(f))
            self.scn_group.addButton(b)
            self.scn_buttons.append(b)
            row.addWidget(b)
        v.addLayout(row)

        act = QHBoxLayout()
        self.b_drop = QPushButton('▶  Soltar')
        self.b_drop.setObjectName('primary')
        self.b_reset = QPushButton('Reiniciar')
        self.b_drop.clicked.connect(self._drop)
        self.b_reset.clicked.connect(self._reset)
        act.addWidget(self.b_drop)
        act.addWidget(self.b_reset)
        v.addLayout(act)
        chk = QHBoxLayout()
        self.chk_slow = QCheckBox('Cámara lenta')
        self.chk_pause = QCheckBox('Pausa')
        chk.addWidget(self.chk_slow)
        chk.addWidget(self.chk_pause)
        v.addLayout(chk)

        self.lbl_narr = QLabel()
        self.lbl_narr.setStyleSheet('font-weight:bold;')
        v.addWidget(self.lbl_narr)

        # bloque de resultados + semáforo
        mid = QHBoxLayout()
        self.stats = QLabel()
        self.stats.setTextFormat(Qt.RichText)
        self.stats.setWordWrap(True)
        self.stats.setAlignment(Qt.AlignTop)
        mid.addWidget(self.stats, 1)
        self.sem = Semaforo()
        mid.addWidget(self.sem)
        v.addLayout(mid)

        self.bar_dyn = ForceBar('Dinámica')
        self.bar_sta = ForceBar('Estática')
        v.addWidget(self.bar_dyn)
        v.addWidget(self.bar_sta)

        # tabla comparativa
        v.addWidget(self._sep('COMPARATIVA DE ESCENARIOS'))
        self.table = QGridLayout()
        self.table.setHorizontalSpacing(8)
        heads = ['Escenario', 'FF', 'v(km/h)', 'Din', 'Est', 'Estado']
        for j, h in enumerate(heads):
            lab = QLabel(h)
            lab.setStyleSheet(f'color:{COLORS["anchor"]};')
            self.table.addWidget(lab, 0, j)
        self.table_cells = []
        for i in range(len(SCENARIOS)):
            rowc = []
            for j in range(6):
                lab = QLabel('')
                self.table.addWidget(lab, i + 1, j)
                rowc.append(lab)
            self.table_cells.append(rowc)
        v.addLayout(self.table)
        v.addStretch(1)
        return panel

    def _sep(self, text):
        lab = QLabel(text)
        lab.setStyleSheet(f'color:{COLORS["primary"]}; font-weight:bold; '
                          f'border-top:1px solid {COLORS["grid"]}; padding-top:4px;')
        return lab

    # ── interacción ───────────────────────────────────────────────────
    def _set_ff(self, ff):
        self.ff = ff
        self.scenario_label = next(l for f, l in SCENARIOS if abs(f - ff) < 1e-3)
        for b, (f, _) in zip(self.scn_buttons, SCENARIOS):
            b.setChecked(abs(f - ff) < 1e-3)
        self._reset()

    def _on_control(self):
        if not self.falling:
            self._reset_state()
        self._recompute()

    def _drop(self):
        self._reset_state()
        self.falling = True

    def _reset(self):
        self._reset_state()
        self._recompute()

    # ── física (igual que el original pygame) ─────────────────────────
    def _tension(self):
        if not self.impact:
            return 0.0
        r = fall_results(self.c_mass.value(), self.rope, self.ff)
        mg = r['mg']
        T = mg + (r['f_dyn'] - mg) * math.exp(-3 * self.t_impact) * math.cos(8 * self.t_impact)
        return max(0.0, T)

    def _tick(self):
        if self.chk_pause.isChecked():
            return
        dt = 0.016
        eff = dt * 0.2 if (self.chk_slow.isChecked() and self.falling and not self.impact) else dt
        self.sim_time += eff
        self.hist.append((self.sim_time, self._tension()))
        while self.hist and self.hist[0][0] < self.sim_time - GRAPH_SECONDS:
            self.hist.pop(0)

        if not self.falling or self.impact:
            if self.impact:
                self.t_impact += eff
                self.bounce_phase += eff * 8
                bounce = math.exp(-self.t_impact * 3) * math.sin(self.bounce_phase) * 0.3
                self.climber_m = self.end_m + bounce
        else:
            self.velocity += G * eff
            self.climber_m += self.velocity * eff
            self.trail.append(self.climber_m)
            if len(self.trail) > MAX_TRAIL:
                self.trail.pop(0)
            if self.climber_m >= self.end_m:
                self.climber_m = self.end_m
                self.impact = True
                self.t_impact = 0.0
        self._refresh()

    # ── refresco de vista ─────────────────────────────────────────────
    def _recompute(self):
        self.lbl_scn.setText(self.scenario_label)
        self._refresh()

    def _refresh(self):
        mass, rope, ff = self.c_mass.value(), self.rope, self.ff
        r = fall_results(mass, rope, ff)

        # escena
        intensity = math.exp(-self.t_impact * 2) if self.impact else 0.0
        self.scene.s = {
            'start_m': self.start_m, 'end_m': self.end_m, 'climber_m': self.climber_m,
            'fall': r['fall'], 'rope': rope, 'velocity': self.velocity,
            'falling': self.falling, 'impact': self.impact,
            'intensity': min(1.0, intensity), 'trail': list(self.trail)}
        self.scene.update()

        # gráfico
        self.graph.hist = list(self.hist)
        self.graph.peak = r['f_dyn'] if self.impact else 0.0
        self.graph.mg = r['mg']
        self.graph.update()

        # narrativa
        if not self.falling and not self.impact:
            narr, col = 'Elegí un escenario y pulsá ▶ Soltar', COLORS['warning']
        elif self.falling and not self.impact:
            narr = (f'Caída libre ↓ {self.velocity:.1f} m/s — ¡acelerando!'
                    if self.velocity >= 2 else 'Caída libre ↓ comenzando…')
            col = COLORS['danger'] if self.velocity >= 2 else COLORS['rope']
        elif self.t_impact < 0.5:
            narr, col = '¡CUERDA TENSA! — absorbiendo el impacto…', COLORS['danger']
        else:
            narr, col = 'Impacto absorbido — oscilando', COLORS['warning']
        self.lbl_narr.setText(narr)
        self.lbl_narr.setStyleSheet(f'color:{col}; font-weight:bold;')

        # semáforo
        self.sem.state = (None if not self.impact else
                          'green' if r['f_dyn'] < 6 else
                          'yellow' if r['f_dyn'] < 9 else 'red')
        self.sem.update()

        # estadísticas (texto enriquecido)
        kg_dyn, kg_sta = r['f_dyn'] * 1000 / G, r['f_sta'] * 1000 / G
        sta_warn = (f' ← SUPERA MBS ({ROPE_STATIC_MBS:.0f}) ¡CEDERÍA!'
                    if r['f_sta'] > ROPE_STATIC_MBS else f' ({kg_sta:.0f} kg eq.)')
        a_col = (COLORS['accent'] if r['a_dyn'] < 30 else
                 COLORS['warning'] if r['a_dyn'] < 80 else COLORS['danger'])
        g_col = (COLORS['accent'] if r['g_dyn'] < 5 else
                 COLORS['warning'] if r['g_dyn'] < 10 else COLORS['danger'])
        T, t, d = COLORS['text'], COLORS['info'], COLORS['danger']
        self.stats.setText(
            f"FF = caída/cuerda = {r['fall']:.1f}/{rope:.1f} = <b>{ff:.2f}</b><br>"
            f"<span style='color:{t}'>Velocidad de impacto: "
            f"{r['speed']:.1f} m/s ({r['speed']*3.6:.0f} km/h)</span><br>"
            f"Dist. frenado: din {r['bd_dyn']*100:.0f} cm | est {r['bd_sta']*100:.0f} cm<br>"
            f"<span style='color:{a_col}'>Acel. frenado: din {r['a_dyn']:.0f} m/s² "
            f"({r['a_dyn']/G:.0f} g) | est {r['a_sta']:.0f} m/s² ({r['a_sta']/G:.0f} g)</span><br>"
            f"<span style='color:{COLORS['accent']}'>Cuerda DINÁMICA: "
            f"<b>{r['f_dyn']:.1f} kN</b> ({kg_dyn:.0f} kg eq.)</span><br>"
            f"<span style='color:{d}'>Cuerda ESTÁTICA: <b>{r['f_sta']:.1f} kN</b>{sta_warn}</span><br>"
            f"<span style='color:{g_col}'>Fuerzas G: din {r['g_dyn']:.1f} g | "
            f"est {r['g_sta']:.1f} g [lesión grave &gt; ~20 g]</span>")

        self.bar_dyn.set(r['f_dyn'])
        self.bar_sta.set(r['f_sta'])

        # tabla comparativa (con el peso/cuerda actuales)
        for i, (sff, _) in enumerate(SCENARIOS):
            rr = fall_results(mass, rope, sff)
            cur = abs(sff - ff) < 1e-3
            if rr['f_sta'] > ROPE_STATIC_MBS:
                estado, ec = 'ROMPE', COLORS['danger']
            elif rr['f_sta'] > UIAA_MAX_IMPACT:
                estado, ec = 'UIAA!', COLORS['danger']
            else:
                estado, ec = 'OK', COLORS['accent']
            dc = (COLORS['accent'] if rr['f_dyn'] < 6 else
                  COLORS['warning'] if rr['f_dyn'] < 9 else COLORS['danger'])
            rowcol = COLORS['warning'] if cur else COLORS['text']
            vals = [('→ ' if cur else '  ') + f'FF {sff:g}', f'{sff:.2f}',
                    f"{rr['speed']*3.6:.0f}", f"{rr['f_dyn']:.1f}", f"{rr['f_sta']:.1f}", estado]
            cols = [rowcol, rowcol, rowcol, dc, ec, ec]
            for j, (txt2, cc) in enumerate(zip(vals, cols)):
                self.table_cells[i][j].setText(txt2)
                self.table_cells[i][j].setStyleSheet(
                    f'color:{cc};' + ('font-weight:bold;' if cur else ''))


QSS = f"""
QWidget {{ background-color: {COLORS['bg']}; color: {COLORS['text']};
           font-family: monospace; font-size: 12px; }}
QFrame#panel {{ background-color: {COLORS['panel']}; border-radius: 10px; }}
QSlider::groove:horizontal {{ height: 6px; background: #2a3a2a; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {COLORS['primary']}; width: 14px;
           margin: -5px 0; border-radius: 7px; }}
QSlider::sub-page:horizontal {{ background: {COLORS['primary']}; border-radius: 3px; }}
QDoubleSpinBox {{ background: {COLORS['bg']}; border: 1px solid {COLORS['grid']};
           border-radius: 4px; padding: 2px; color: {COLORS['text']}; }}
QPushButton {{ background: #16241a; border: 1px solid {COLORS['grid']};
           border-radius: 6px; padding: 5px 8px; }}
QPushButton:hover {{ border-color: {COLORS['primary']}; }}
QPushButton:checked {{ background: {COLORS['accent']}; color: {COLORS['bg']}; font-weight: bold; }}
QPushButton#primary {{ background: {COLORS['primary']}; color: {COLORS['bg']}; font-weight: bold; }}
QCheckBox::indicator:checked {{ background: {COLORS['accent']}; }}
"""


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    w = FallSim()
    w.show()
    app.exec_()


if __name__ == '__main__':
    main()
