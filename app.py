import math
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtGui import QTextDocument


# ----------------------------- CONSTANT DATABASE -----------------------------
# IEC 60228 / practical design reference data
MATERIALS = {
    "Copper": {
        "rho20": 0.0175,  # Ohm*mm^2/m at 20°C
        "alpha": 0.00393,  # 1/°C temperature coefficient
        "k_sc": 115,  # adiabatic short-circuit constant for PVC approx
    },
    "Aluminum": {
        "rho20": 0.0282,
        "alpha": 0.00403,
        "k_sc": 76,
    },
}

INSULATION = {
    "PVC (70°C)": {"max_temp": 70, "corr_ref": 1.0},
    "XLPE (90°C)": {"max_temp": 90, "corr_ref": 1.0},
    "EPR (90°C)": {"max_temp": 90, "corr_ref": 1.0},
}

LAYING_FACTORS = {
    "In air": 1.00,
    "In pipe": 0.90,
    "In ground": 0.85,
}

# Simplified IEC-like typical current capacities (A) for Cu in air reference
CURRENT_CAPACITY_BASE = {
    1.5: 18,
    2.5: 24,
    4: 32,
    6: 41,
    10: 57,
    16: 76,
    25: 101,
    35: 125,
    50: 150,
    70: 192,
    95: 232,
    120: 269,
    150: 309,
    185: 353,
    240: 415,
    300: 477,
    400: 550,
    500: 630,
    630: 720,
}

STANDARD_SECTIONS = sorted(CURRENT_CAPACITY_BASE.keys())

# Typical utilization factors for lighting
UTILIZATION_TABLE = {
    "Office": 0.55,
    "Workshop": 0.50,
    "Warehouse": 0.42,
    "Classroom": 0.60,
    "Hospital": 0.58,
    "Residential": 0.48,
}

# Typical lux norms
LUX_NORMS = {
    "Office": 500,
    "Workshop": 300,
    "Warehouse": 150,
    "Classroom": 300,
    "Hospital": 500,
    "Residential": 150,
}

BREAKER_CURVE_MULTIPLIER = {
    "B": (3, 5),
    "C": (5, 10),
    "D": (10, 20),
}


# ----------------------------- CALCULATION CORE -----------------------------
class ValidationError(Exception):
    pass


class ElectricalMath:
    """Engineering formulas used by UI and reporting."""

    @staticmethod
    def ensure_positive(value: float, name: str):
        if value <= 0:
            raise ValidationError(f"{name} must be > 0")

    @staticmethod
    def parse_float(text: str, name: str) -> float:
        try:
            value = float(text.replace(",", ".").strip())
        except Exception:
            raise ValidationError(f"{name} must be numeric")
        ElectricalMath.ensure_positive(value, name)
        return value

    @staticmethod
    def conductor_resistivity_at_temp(material: str, temp_c: float) -> float:
        # Formula: rho(T) = rho20 * (1 + alpha*(T-20))
        m = MATERIALS[material]
        return m["rho20"] * (1 + m["alpha"] * (temp_c - 20))

    @staticmethod
    def load_current(power_kw: float, voltage_v: float, phases: int, cos_phi: float) -> float:
        if phases == 1:
            # P = U*I*cosφ => I = P/(U*cosφ)
            return (power_kw * 1000) / (voltage_v * cos_phi)
        # P = √3*U*I*cosφ
        return (power_kw * 1000) / (math.sqrt(3) * voltage_v * cos_phi)

    @staticmethod
    def section_by_current(i_load: float, material: str, laying: str, temp_c: float, insulation: str) -> float:
        # Base table is Cu reference; correct for Al by approx factor 0.8
        material_factor = 1.0 if material == "Copper" else 0.8
        # Ambient correction approximation (IEC-like): lower ampacity at higher ambient
        temp_factor = max(0.65, 1 - (temp_c - 30) * 0.005)
        lay_factor = LAYING_FACTORS[laying]
        ins_factor = 1.05 if insulation != "PVC (70°C)" else 1.0
        required_base = i_load / (material_factor * temp_factor * lay_factor * ins_factor)

        for sec in STANDARD_SECTIONS:
            if CURRENT_CAPACITY_BASE[sec] >= required_base:
                return sec
        return STANDARD_SECTIONS[-1]

    @staticmethod
    def voltage_drop_percent(length_m: float, i_a: float, section_mm2: float, material: str,
                             temp_c: float, voltage_v: float, phases: int, cos_phi: float) -> float:
        rho_t = ElectricalMath.conductor_resistivity_at_temp(material, temp_c)
        r_per_m = rho_t / section_mm2
        # Simplified reactance estimate for LV cables (~0.08 mΩ/m)
        x_per_m = 0.00008
        sin_phi = math.sqrt(max(0.0, 1 - cos_phi ** 2))

        if phases == 1:
            # ΔU = 2*I*L*(R*cosφ + X*sinφ)
            du = 2 * i_a * length_m * (r_per_m * cos_phi + x_per_m * sin_phi)
        else:
            # ΔU = √3*I*L*(R*cosφ + X*sinφ)
            du = math.sqrt(3) * i_a * length_m * (r_per_m * cos_phi + x_per_m * sin_phi)
        return du / voltage_v * 100

    @staticmethod
    def short_circuit_current_3ph(voltage_v: float, z_source_ohm: float) -> float:
        # Ik3 = U/(√3 * Z)
        return voltage_v / (math.sqrt(3) * z_source_ohm)

    @staticmethod
    def short_circuit_current_1ph(voltage_v: float, z_loop_ohm: float) -> float:
        # Ik1 = U/Zloop
        return voltage_v / z_loop_ohm

    @staticmethod
    def breaker_trip_band(curve: str, in_a: float) -> Tuple[float, float]:
        low, high = BREAKER_CURVE_MULTIPLIER[curve]
        return in_a * low, in_a * high

    @staticmethod
    def cascading_selectivity(upstream_in: float, downstream_in: float) -> bool:
        # Simple engineering criterion for partial selectivity in LV systems
        return upstream_in >= 1.6 * downstream_in

    @staticmethod
    def earthing_vertical_resistance(rho: float, length_m: float, diameter_m: float) -> float:
        # Rv = (ρ/(2πL)) * (ln(4L/d)-1)
        return (rho / (2 * math.pi * length_m)) * (math.log((4 * length_m) / diameter_m) - 1)

    @staticmethod
    def earthing_horizontal_resistance(rho: float, length_m: float, depth_m: float, width_m: float) -> float:
        # Rh ~= ρ/(2πL) * ln(2L^2/(w*h))
        return (rho / (2 * math.pi * length_m)) * math.log((2 * (length_m ** 2)) / (width_m * depth_m))

    @staticmethod
    def total_earthing_resistance(rv: float, n_vertical: int, rh: float) -> float:
        # Parallel approximation: Rtot = 1 / (n/Rv + 1/Rh)
        return 1 / ((n_vertical / rv) + (1 / rh))

    @staticmethod
    def lighting_lumen_method(area_m2: float, norm_lux: float, uf: float, mf: float, lamp_flux_lm: float) -> float:
        # N = (E*A)/(F*UF*MF)
        return (norm_lux * area_m2) / (lamp_flux_lm * uf * mf)

    @staticmethod
    def reactive_compensation_qc(p_kw: float, cos1: float, cos2: float) -> float:
        # Qc = P*(tanφ1 - tanφ2)
        phi1, phi2 = math.acos(cos1), math.acos(cos2)
        return p_kw * (math.tan(phi1) - math.tan(phi2))

    @staticmethod
    def transformer_load_and_losses(s_nom_kva: float, p_load_kw: float, cos_phi: float,
                                    p0_kw: float, pk_kw: float) -> Tuple[float, float, float]:
        # loading β = Sload/Snom where Sload = P/cosφ
        s_load = p_load_kw / cos_phi
        beta = s_load / s_nom_kva
        # P_loss = P0 + β^2 * Pk
        losses = p0_kw + (beta ** 2) * pk_kw
        efficiency = p_load_kw / (p_load_kw + losses) * 100
        return beta, losses, efficiency

    @staticmethod
    def motor_induction(power_kw: float, voltage_v: float, eff: float, cos_phi: float, phases: int) -> float:
        # I = Pout/(η*U*cosφ) or / (√3*U*cosφ)
        pin = power_kw * 1000 / eff
        if phases == 1:
            return pin / (voltage_v * cos_phi)
        return pin / (math.sqrt(3) * voltage_v * cos_phi)

    @staticmethod
    def motor_dc(power_kw: float, voltage_v: float, eff: float) -> float:
        # I = P/(η*U)
        return power_kw * 1000 / (eff * voltage_v)


@dataclass
class CalcResult:
    title: str
    text: str


# ----------------------------- MINI CAD CANVAS -----------------------------
class ElectricalCanvas(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.scene.setSceneRect(0, 0, 1200, 900)
        self.setBackgroundBrush(QBrush(QColor("#111217")))
        self.nodes: List[QGraphicsRectItem] = []

    def add_component(self, label: str, kind: str = "Generic"):
        x = 60 + (len(self.nodes) % 6) * 180
        y = 60 + (len(self.nodes) // 6) * 140
        rect = QGraphicsRectItem(QRectF(x, y, 130, 70))
        rect.setBrush(QBrush(QColor("#1f2430")))
        rect.setPen(QPen(QColor("#6fa8ff"), 2))
        self.scene.addItem(rect)

        t = QGraphicsSimpleTextItem(f"{kind}\n{label}")
        t.setBrush(QBrush(QColor("#d4d8e1")))
        t.setPos(x + 8, y + 8)
        self.scene.addItem(t)

        # IEC/GOST style indicative terminals
        l_term = QGraphicsEllipseItem(x - 6, y + 31, 12, 12)
        r_term = QGraphicsEllipseItem(x + 124, y + 31, 12, 12)
        for it in (l_term, r_term):
            it.setBrush(QBrush(QColor("#8dd3ff")))
            it.setPen(QPen(QColor("#8dd3ff"), 1))
            self.scene.addItem(it)

        self.nodes.append(rect)

    def connect_last_two(self):
        if len(self.nodes) < 2:
            return
        a = self.nodes[-2].rect()
        b = self.nodes[-1].rect()
        a_pos = self.nodes[-2].pos()
        b_pos = self.nodes[-1].pos()
        p1 = QPointF(a_pos.x() + a.x() + a.width(), a_pos.y() + a.y() + a.height() / 2)
        p2 = QPointF(b_pos.x() + b.x(), b_pos.y() + b.y() + b.height() / 2)
        line = QGraphicsLineItem(p1.x(), p1.y(), p2.x(), p2.y())
        line.setPen(QPen(QColor("#f5f5f5"), 2, Qt.SolidLine))
        self.scene.addItem(line)


# ----------------------------- MAIN APPLICATION -----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Electrical Engineering Suite (Single-File, Ultra Dark)")
        self.resize(1700, 900)

        self.results: List[CalcResult] = []
        self.canvas = ElectricalCanvas()

        root = QWidget()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)

        # Sidebar
        self.sidebar = QListWidget()
        sections = [
            "Cable Calculation",
            "Protection & Automation",
            "Earthing",
            "Lighting",
            "Reactive Compensation",
            "Transformer",
            "Motors",
            "Cable Lines Batch",
            "Report / PDF",
        ]
        for s in sections:
            QListWidgetItem(s, self.sidebar)
        self.sidebar.setMaximumWidth(280)

        # Center area
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_cable_page())
        self.stack.addWidget(self._build_protection_page())
        self.stack.addWidget(self._build_earthing_page())
        self.stack.addWidget(self._build_lighting_page())
        self.stack.addWidget(self._build_reactive_page())
        self.stack.addWidget(self._build_transformer_page())
        self.stack.addWidget(self._build_motor_page())
        self.stack.addWidget(self._build_cable_lines_page())
        self.stack.addWidget(self._build_report_page())

        h.addWidget(self.sidebar, 1)
        h.addWidget(self.stack, 2)
        h.addWidget(self.canvas, 3)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        self.apply_dark_theme()

    def apply_dark_theme(self):
        self.setStyleSheet(
            """
            * { color: #d4d8e1; font-family: Segoe UI; font-size: 12px; }
            QMainWindow, QWidget { background-color: #0b0d12; }
            QLineEdit, QComboBox, QTextEdit, QListWidget, QSpinBox {
                background-color: #151923;
                border: 1px solid #2a3040;
                border-radius: 6px;
                padding: 5px;
                color: #e8ecf5;
            }
            QPushButton {
                background-color: #253048;
                border: 1px solid #3a4a6e;
                border-radius: 6px;
                padding: 7px;
            }
            QPushButton:hover { background-color: #304062; }
            QLabel { color: #c3c8d4; }
            QListWidget::item:selected { background-color: #2f3f61; }
            """
        )

    def show_error(self, e: Exception):
        QMessageBox.critical(self, "Input / Calculation Error", str(e))

    def add_result(self, title: str, text: str):
        self.results.append(CalcResult(title, text))
        self.result_view.append(f"\n=== {title} ===\n{text}\n")

    # ---------- Pages ----------
    def _build_cable_page(self):
        w = QWidget(); f = QFormLayout(w)
        self.cb_power = QLineEdit("45")
        self.cb_voltage = QLineEdit("400")
        self.cb_len = QLineEdit("120")
        self.cb_cos = QLineEdit("0.9")
        self.cb_temp = QLineEdit("35")
        self.cb_phases = QComboBox(); self.cb_phases.addItems(["1", "3"])
        self.cb_material = QComboBox(); self.cb_material.addItems(MATERIALS.keys())
        self.cb_laying = QComboBox(); self.cb_laying.addItems(LAYING_FACTORS.keys())
        self.cb_ins = QComboBox(); self.cb_ins.addItems(INSULATION.keys())
        btn = QPushButton("Calculate Cable")
        btn_add = QPushButton("Add Cable to CAD")

        f.addRow("Power (kW)", self.cb_power)
        f.addRow("Voltage (V)", self.cb_voltage)
        f.addRow("Length (m)", self.cb_len)
        f.addRow("Cos φ", self.cb_cos)
        f.addRow("Ambient temp (°C)", self.cb_temp)
        f.addRow("Phases", self.cb_phases)
        f.addRow("Material", self.cb_material)
        f.addRow("Laying", self.cb_laying)
        f.addRow("Insulation", self.cb_ins)
        f.addRow(btn)
        f.addRow(btn_add)

        def run():
            try:
                p = ElectricalMath.parse_float(self.cb_power.text(), "Power")
                u = ElectricalMath.parse_float(self.cb_voltage.text(), "Voltage")
                l = ElectricalMath.parse_float(self.cb_len.text(), "Length")
                cos = ElectricalMath.parse_float(self.cb_cos.text(), "Cos φ")
                t = ElectricalMath.parse_float(self.cb_temp.text(), "Temperature")
                phases = int(self.cb_phases.currentText())
                mat = self.cb_material.currentText()
                lay = self.cb_laying.currentText()
                ins = self.cb_ins.currentText()

                i = ElectricalMath.load_current(p, u, phases, cos)
                sec = ElectricalMath.section_by_current(i, mat, lay, t, ins)
                du = ElectricalMath.voltage_drop_percent(l, i, sec, mat, t, u, phases, cos)
                text = (
                    f"Load current I = {i:.2f} A\n"
                    f"Selected cross-section S = {sec} mm²\n"
                    f"Voltage drop ΔU = {du:.2f} %\n"
                    f"Compliance: {'OK (<5%)' if du < 5 else 'Check / Increase section'}"
                )
                self.add_result("Complete Cable Calculation", text)
            except Exception as e:
                self.show_error(e)

        btn.clicked.connect(run)
        btn_add.clicked.connect(lambda: (self.canvas.add_component("Cable", "Line"), self.canvas.connect_last_two()))
        return w

    def _build_protection_page(self):
        w = QWidget(); f = QFormLayout(w)
        self.pr_u = QLineEdit("400")
        self.pr_z3 = QLineEdit("0.12")
        self.pr_u1 = QLineEdit("230")
        self.pr_z1 = QLineEdit("0.42")
        self.pr_curve = QComboBox(); self.pr_curve.addItems(["B", "C", "D"])
        self.pr_in = QLineEdit("63")
        self.pr_up = QLineEdit("160")
        self.pr_dn = QLineEdit("63")
        btn = QPushButton("Calculate Protection")
        btn_add = QPushButton("Add Breaker to CAD")

        for n, wdg in [
            ("3φ Voltage (V)", self.pr_u), ("Z source 3φ (Ω)", self.pr_z3),
            ("1φ Voltage (V)", self.pr_u1), ("Z loop 1φ (Ω)", self.pr_z1),
            ("Breaker curve", self.pr_curve), ("Breaker In (A)", self.pr_in),
            ("Upstream In (A)", self.pr_up), ("Downstream In (A)", self.pr_dn),
        ]:
            f.addRow(n, wdg)
        f.addRow(btn); f.addRow(btn_add)

        def run():
            try:
                ik3 = ElectricalMath.short_circuit_current_3ph(
                    ElectricalMath.parse_float(self.pr_u.text(), "3φ voltage"),
                    ElectricalMath.parse_float(self.pr_z3.text(), "Z source"),
                )
                ik1 = ElectricalMath.short_circuit_current_1ph(
                    ElectricalMath.parse_float(self.pr_u1.text(), "1φ voltage"),
                    ElectricalMath.parse_float(self.pr_z1.text(), "Z loop"),
                )
                in_a = ElectricalMath.parse_float(self.pr_in.text(), "In")
                lo, hi = ElectricalMath.breaker_trip_band(self.pr_curve.currentText(), in_a)
                sel = ElectricalMath.cascading_selectivity(
                    ElectricalMath.parse_float(self.pr_up.text(), "Upstream In"),
                    ElectricalMath.parse_float(self.pr_dn.text(), "Downstream In"),
                )
                text = (
                    f"Ik3 = {ik3:.1f} A\n"
                    f"Ik1 = {ik1:.1f} A\n"
                    f"Magnetic instantaneous trip ({self.pr_curve.currentText()}) band ≈ {lo:.0f}..{hi:.0f} A\n"
                    f"Cascade selectivity (simple rule): {'Likely YES' if sel else 'Likely NO'}"
                )
                self.add_result("Protection and Automation", text)
            except Exception as e:
                self.show_error(e)

        btn.clicked.connect(run)
        btn_add.clicked.connect(lambda: (self.canvas.add_component("CB", "Breaker"), self.canvas.connect_last_two()))
        return w

    def _build_earthing_page(self):
        w = QWidget(); f = QFormLayout(w)
        self.e_rho = QLineEdit("100")
        self.e_lv = QLineEdit("3")
        self.e_d = QLineEdit("0.016")
        self.e_n = QSpinBox(); self.e_n.setRange(1, 100); self.e_n.setValue(4)
        self.e_lh = QLineEdit("30")
        self.e_depth = QLineEdit("0.8")
        self.e_w = QLineEdit("0.04")
        btn = QPushButton("Calculate Earthing")

        for n, wdg in [
            ("Soil resistivity ρ (Ω·m)", self.e_rho), ("Vertical electrode length L (m)", self.e_lv),
            ("Vertical electrode diameter d (m)", self.e_d), ("Count of vertical electrodes", self.e_n),
            ("Horizontal length (m)", self.e_lh), ("Horizontal depth (m)", self.e_depth),
            ("Horizontal width (m)", self.e_w),
        ]:
            f.addRow(n, wdg)
        f.addRow(btn)

        def run():
            try:
                rho = ElectricalMath.parse_float(self.e_rho.text(), "ρ")
                lv = ElectricalMath.parse_float(self.e_lv.text(), "Vertical length")
                d = ElectricalMath.parse_float(self.e_d.text(), "Diameter")
                lh = ElectricalMath.parse_float(self.e_lh.text(), "Horizontal length")
                depth = ElectricalMath.parse_float(self.e_depth.text(), "Depth")
                wid = ElectricalMath.parse_float(self.e_w.text(), "Width")
                n = self.e_n.value()
                rv = ElectricalMath.earthing_vertical_resistance(rho, lv, d)
                rh = ElectricalMath.earthing_horizontal_resistance(rho, lh, depth, wid)
                rt = ElectricalMath.total_earthing_resistance(rv, n, rh)
                text = f"Rv = {rv:.2f} Ω\nRh = {rh:.2f} Ω\nRtotal = {rt:.2f} Ω"
                self.add_result("Advanced Earthing", text)
            except Exception as e:
                self.show_error(e)

        btn.clicked.connect(run)
        return w

    def _build_lighting_page(self):
        w = QWidget(); f = QFormLayout(w)
        self.l_room = QComboBox(); self.l_room.addItems(LUX_NORMS.keys())
        self.l_area = QLineEdit("120")
        self.l_flux = QLineEdit("3600")
        self.l_mf = QLineEdit("0.8")
        self.l_rho_c = QLineEdit("0.7")
        self.l_rho_w = QLineEdit("0.5")
        self.l_rho_f = QLineEdit("0.3")
        btn = QPushButton("Calculate Lighting")

        for n, wdg in [
            ("Room type", self.l_room), ("Area (m²)", self.l_area), ("Lamp flux (lm)", self.l_flux),
            ("Maintenance factor MF", self.l_mf), ("Ceiling reflectance", self.l_rho_c),
            ("Wall reflectance", self.l_rho_w), ("Floor reflectance", self.l_rho_f),
        ]:
            f.addRow(n, wdg)
        f.addRow(btn)

        def run():
            try:
                room = self.l_room.currentText()
                area = ElectricalMath.parse_float(self.l_area.text(), "Area")
                flux = ElectricalMath.parse_float(self.l_flux.text(), "Flux")
                mf = ElectricalMath.parse_float(self.l_mf.text(), "MF")
                rc = ElectricalMath.parse_float(self.l_rho_c.text(), "Ceiling reflectance")
                rw = ElectricalMath.parse_float(self.l_rho_w.text(), "Wall reflectance")
                rf = ElectricalMath.parse_float(self.l_rho_f.text(), "Floor reflectance")

                # Simplified adjustment of UF by room reflectance
                uf0 = UTILIZATION_TABLE[room]
                uf = uf0 * (0.8 + 0.2 * ((rc + rw + rf) / 1.5))
                n = ElectricalMath.lighting_lumen_method(area, LUX_NORMS[room], uf, mf, flux)
                text = (
                    f"Standard illuminance E = {LUX_NORMS[room]} lux\n"
                    f"Utilization factor UF = {uf:.2f}\n"
                    f"Required luminaires N = {math.ceil(n)} pcs"
                )
                self.add_result("Lighting (Lumen Method)", text)
            except Exception as e:
                self.show_error(e)

        btn.clicked.connect(run)
        return w

    def _build_reactive_page(self):
        w = QWidget(); f = QFormLayout(w)
        self.r_p = QLineEdit("250")
        self.r_cos1 = QLineEdit("0.74")
        self.r_cos2 = QLineEdit("0.95")
        btn = QPushButton("Calculate Capacitor Bank")
        f.addRow("Active power P (kW)", self.r_p)
        f.addRow("Existing cosφ1", self.r_cos1)
        f.addRow("Target cosφ2", self.r_cos2)
        f.addRow(btn)

        def run():
            try:
                p = ElectricalMath.parse_float(self.r_p.text(), "P")
                c1 = ElectricalMath.parse_float(self.r_cos1.text(), "cosφ1")
                c2 = ElectricalMath.parse_float(self.r_cos2.text(), "cosφ2")
                qc = ElectricalMath.reactive_compensation_qc(p, c1, c2)
                self.add_result("Reactive Power Compensation", f"Required capacitor power Qc = {qc:.2f} kVAr")
            except Exception as e:
                self.show_error(e)

        btn.clicked.connect(run)
        return w

    def _build_transformer_page(self):
        w = QWidget(); f = QFormLayout(w)
        self.t_s = QLineEdit("630")
        self.t_p = QLineEdit("420")
        self.t_cos = QLineEdit("0.9")
        self.t_p0 = QLineEdit("1.2")
        self.t_pk = QLineEdit("7.5")
        btn = QPushButton("Calculate Transformer")
        btn_add = QPushButton("Add Transformer to CAD")
        for n, wdg in [
            ("Nominal S (kVA)", self.t_s), ("Load P (kW)", self.t_p), ("cosφ", self.t_cos),
            ("No-load loss P0 (kW)", self.t_p0), ("Short-circuit loss Pk (kW)", self.t_pk),
        ]:
            f.addRow(n, wdg)
        f.addRow(btn); f.addRow(btn_add)

        def run():
            try:
                beta, loss, eff = ElectricalMath.transformer_load_and_losses(
                    ElectricalMath.parse_float(self.t_s.text(), "Snom"),
                    ElectricalMath.parse_float(self.t_p.text(), "Pload"),
                    ElectricalMath.parse_float(self.t_cos.text(), "cosφ"),
                    ElectricalMath.parse_float(self.t_p0.text(), "P0"),
                    ElectricalMath.parse_float(self.t_pk.text(), "Pk"),
                )
                text = f"Loading β = {beta:.3f} pu\nTotal losses = {loss:.2f} kW\nEfficiency = {eff:.2f} %"
                self.add_result("Transformer Calculation", text)
            except Exception as e:
                self.show_error(e)

        btn.clicked.connect(run)
        btn_add.clicked.connect(lambda: (self.canvas.add_component("TR", "Transformer"), self.canvas.connect_last_two()))
        return w

    def _build_motor_page(self):
        w = QWidget(); f = QFormLayout(w)
        self.m_type = QComboBox(); self.m_type.addItems(["Induction", "Synchronous", "DC"])
        self.m_p = QLineEdit("55")
        self.m_u = QLineEdit("400")
        self.m_eff = QLineEdit("0.93")
        self.m_cos = QLineEdit("0.86")
        self.m_phase = QComboBox(); self.m_phase.addItems(["1", "3"])
        btn = QPushButton("Calculate Motor")
        btn_add = QPushButton("Add Motor to CAD")
        for n, wdg in [
            ("Motor type", self.m_type), ("Rated power (kW)", self.m_p), ("Voltage (V)", self.m_u),
            ("Efficiency η", self.m_eff), ("cosφ (AC)", self.m_cos), ("Phases", self.m_phase),
        ]:
            f.addRow(n, wdg)
        f.addRow(btn); f.addRow(btn_add)

        def run():
            try:
                typ = self.m_type.currentText()
                p = ElectricalMath.parse_float(self.m_p.text(), "Power")
                u = ElectricalMath.parse_float(self.m_u.text(), "Voltage")
                eff = ElectricalMath.parse_float(self.m_eff.text(), "Efficiency")
                phases = int(self.m_phase.currentText())

                if typ in ("Induction", "Synchronous"):
                    c = ElectricalMath.parse_float(self.m_cos.text(), "cosφ")
                    i = ElectricalMath.motor_induction(p, u, eff, c, phases)
                else:
                    i = ElectricalMath.motor_dc(p, u, eff)
                self.add_result("Motor Calculation", f"{typ} motor rated current ≈ {i:.2f} A")
            except Exception as e:
                self.show_error(e)

        btn.clicked.connect(run)
        btn_add.clicked.connect(lambda: (self.canvas.add_component("M", "Motor"), self.canvas.connect_last_two()))
        return w

    def _build_cable_lines_page(self):
        w = QWidget(); f = QFormLayout(w)
        self.cl_data = QTextEdit()
        self.cl_data.setPlaceholderText(
            "Enter lines: power_kW,voltage_V,length_m,phases,cosphi (one per line)\n"
            "Example:\n15,400,75,3,0.9\n4,230,40,1,0.95"
        )
        self.cl_mat = QComboBox(); self.cl_mat.addItems(MATERIALS.keys())
        self.cl_lay = QComboBox(); self.cl_lay.addItems(LAYING_FACTORS.keys())
        self.cl_ins = QComboBox(); self.cl_ins.addItems(INSULATION.keys())
        self.cl_temp = QLineEdit("30")
        btn = QPushButton("Calculate All Cable Lines")
        f.addRow("Input lines", self.cl_data)
        f.addRow("Material", self.cl_mat)
        f.addRow("Laying", self.cl_lay)
        f.addRow("Insulation", self.cl_ins)
        f.addRow("Temperature (°C)", self.cl_temp)
        f.addRow(btn)

        def run():
            try:
                t = ElectricalMath.parse_float(self.cl_temp.text(), "Temperature")
                mat, lay, ins = self.cl_mat.currentText(), self.cl_lay.currentText(), self.cl_ins.currentText()
                lines = [x.strip() for x in self.cl_data.toPlainText().splitlines() if x.strip()]
                if not lines:
                    raise ValidationError("No cable lines entered")

                out = []
                for idx, ln in enumerate(lines, 1):
                    p, u, l, ph, c = [float(v.strip()) for v in ln.split(",")]
                    ElectricalMath.ensure_positive(p, f"line {idx} power")
                    i = ElectricalMath.load_current(p, u, int(ph), c)
                    sec = ElectricalMath.section_by_current(i, mat, lay, t, ins)
                    du = ElectricalMath.voltage_drop_percent(l, i, sec, mat, t, u, int(ph), c)
                    out.append(f"Line {idx}: I={i:.1f}A, S={sec}mm², ΔU={du:.2f}%")

                self.add_result("Cable Lines Batch", "\n".join(out))
            except Exception as e:
                self.show_error(e)

        btn.clicked.connect(run)
        return w

    def _build_report_page(self):
        w = QWidget(); v = QVBoxLayout(w)
        self.result_view = QTextEdit(); self.result_view.setReadOnly(True)
        btn_pdf = QPushButton("Export to PDF (with formulas)")
        btn_component = QPushButton("Add Generic Component to CAD")
        v.addWidget(QLabel("Calculation log / report"))
        v.addWidget(self.result_view)
        v.addWidget(btn_pdf)
        v.addWidget(btn_component)

        def export_pdf():
            if not self.results:
                QMessageBox.information(self, "No data", "Run calculations first.")
                return
            path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "electrical_report.pdf", "PDF Files (*.pdf)")
            if not path:
                return

            formulas = """
<b>Formulas used (IEC/PUE engineering practice):</b><br>
I = P/(U·cosφ) (1φ), I = P/(√3·U·cosφ) (3φ)<br>
ρ(T)=ρ20·(1+α(T−20)); ΔU by R/X cable model<br>
Ik3 = U/(√3·Z), Ik1 = U/Zloop<br>
Earthing: Rv=(ρ/(2πL))(ln(4L/d)-1), parallel reduction<br>
Lumen: N=(E·A)/(F·UF·MF)<br>
Qc = P(tanφ1−tanφ2)<br>
Transformer: β=Sload/Snom, Ploss=P0+β²Pk
"""
            body = "".join([f"<h3>{r.title}</h3><pre>{r.text}</pre>" for r in self.results])
            html = f"<h1>Electrical Engineering Report</h1>{formulas}<hr>{body}"

            doc = QTextDocument()
            doc.setHtml(html)
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            doc.print_(printer)
            QMessageBox.information(self, "Done", f"PDF exported:\n{path}")

        btn_pdf.clicked.connect(export_pdf)
        btn_component.clicked.connect(lambda: (self.canvas.add_component("X", "Generic"), self.canvas.connect_last_two()))
        return w


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
