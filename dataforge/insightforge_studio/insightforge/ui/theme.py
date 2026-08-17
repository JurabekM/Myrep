from ..config import COLORS as C

QSS = f"""
* {{ outline: none; }}
QMainWindow, QWidget {{ background: {C['canvas']}; color: {C['text']}; }}
QLabel#brand {{ font-size: 19px; font-weight: 800; color: {C['text']}; }}
QLabel#brandAccent {{ color: {C['primary2']}; font-size: 10px; font-weight: 700; letter-spacing: 2px; }}
QLabel#pageTitle {{ font-size: 25px; font-weight: 750; }}
QLabel#pageHint, QLabel#muted {{ color: {C['muted']}; }}
QFrame#sidebar {{ background: {C['panel']}; border-right: 1px solid {C['border']}; }}
QFrame#topbar {{ background: {C['panel']}; border-bottom: 1px solid {C['border']}; }}
QFrame#card {{ background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 12px; }}
QFrame#statCard {{ background: {C['raised']}; border: 1px solid {C['border']}; border-radius: 12px; }}
QLabel#statValue {{ font-size: 24px; font-weight: 750; }}
QLabel#statLabel {{ color: {C['muted']}; }}
QPushButton {{ background: {C['raised2']}; border: 1px solid {C['border']}; border-radius: 7px; padding: 8px 13px; font-weight: 600; }}
QPushButton:hover {{ border-color: {C['primary']}; background: #29334A; }}
QPushButton:pressed {{ background: {C['primary']}; }}
QPushButton[primary="true"] {{ background: {C['primary']}; border-color: {C['primary']}; color: white; }}
QPushButton[danger="true"] {{ color: {C['danger']}; }}
QPushButton#nav {{ text-align: left; padding: 11px 16px; border: 0; background: transparent; color: {C['muted']}; }}
QPushButton#nav:hover {{ background: {C['raised']}; color: {C['text']}; }}
QPushButton#nav:checked {{ background: #242040; color: #B8A8FF; border-left: 3px solid {C['primary']}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QListWidget {{ background: {C['raised']}; border: 1px solid {C['border']}; border-radius: 7px; padding: 7px; selection-background-color: {C['primary']}; }}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{ border-color: {C['primary']}; }}
QTableView {{ background: {C['panel']}; alternate-background-color: {C['raised']}; border: 1px solid {C['border']}; border-radius: 8px; gridline-color: {C['border']}; selection-background-color: #3C326D; }}
QHeaderView::section {{ background: {C['raised2']}; color: #C9D3E7; border: 0; border-right: 1px solid {C['border']}; border-bottom: 1px solid {C['border']}; padding: 8px; font-weight: 650; }}
QTabWidget::pane {{ border: 1px solid {C['border']}; border-radius: 8px; }}
QTabBar::tab {{ padding: 9px 15px; color: {C['muted']}; }} QTabBar::tab:selected {{ color: {C['text']}; border-bottom: 2px solid {C['primary']}; }}
QProgressBar {{ background: {C['raised']}; border: 0; border-radius: 4px; height: 8px; text-align:center; }} QProgressBar::chunk {{ background: {C['primary']}; border-radius:4px; }}
QScrollBar:vertical {{ width: 10px; background: transparent; }} QScrollBar::handle:vertical {{ background: {C['border']}; border-radius: 5px; min-height: 25px; }}
QToolTip {{ background: {C['raised2']}; color: {C['text']}; border: 1px solid {C['border']}; padding: 5px; }}
"""

