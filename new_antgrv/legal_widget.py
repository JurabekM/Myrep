from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QTextBrowser, 
    QSplitter, QGroupBox, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from scraper import LexScraperWorker

class LegalWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title_lbl = QLabel("Legal & Compliance Integration")
        title_lbl.setObjectName("title-lbl")
        main_layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Query the Uzbekistan National Database of Legislation (lex.uz) in real-time "
            "or explore high-priority local legal frameworks offline. Use this to audit "
            "licensing, tax requirements, and compliance milestones."
        )
        desc_lbl.setWordWrap(True)
        main_layout.addWidget(desc_lbl)

        # Quick Links Panel
        quick_group = QGroupBox("Quick-Access Reference Frameworks")
        quick_layout = QHBoxLayout(quick_group)
        quick_layout.setSpacing(10)
        
        btn_itpark = QPushButton("IT-Park Exemptions")
        btn_itpark.clicked.connect(lambda: self.run_quick_search("IT-Park"))
        quick_layout.addWidget(btn_itpark)

        btn_llc = QPushButton("LLC Incorporation")
        btn_llc.clicked.connect(lambda: self.run_quick_search("LLC MChJ"))
        quick_layout.addWidget(btn_llc)

        btn_tax = QPushButton("Taxation Regimes")
        btn_tax.clicked.connect(lambda: self.run_quick_search("Taxation Soliq"))
        quick_layout.addWidget(btn_tax)

        btn_loans = QPushButton("Microloan Rules")
        btn_loans.clicked.connect(lambda: self.run_quick_search("Microloan Kredit"))
        quick_layout.addWidget(btn_loans)

        main_layout.addWidget(quick_group)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter legal keywords (e.g. soliq, IT-Park, ustav, patent)...")
        self.search_input.returnPressed.connect(self.perform_search)
        search_layout.addWidget(self.search_input, 4)

        self.search_btn = QPushButton("Search Database")
        self.search_btn.setObjectName("accent-btn")
        self.search_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_btn, 1)

        main_layout.addLayout(search_layout)

        # Progress / Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate spinner styling
        self.progress_bar.setVisible(False)
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #00f0ff; font-style: italic;")
        
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.progress_bar)
        status_layout.addWidget(self.status_lbl)
        main_layout.addLayout(status_layout)

        # Splitter for list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Search results list
        list_group = QGroupBox("Search Results")
        list_layout = QVBoxLayout(list_group)
        self.results_list = QListWidget()
        self.results_list.itemSelectionChanged.connect(self.display_selected_result)
        list_layout.addWidget(self.results_list)
        splitter.addWidget(list_group)

        # Right: Result details browser
        detail_group = QGroupBox("Document Insight & Context")
        detail_layout = QVBoxLayout(detail_group)
        self.detail_browser = QTextBrowser()
        self.detail_browser.setOpenExternalLinks(True)
        detail_layout.addWidget(self.detail_browser)
        splitter.addWidget(detail_group)

        # Set sizes (ratio 40% list, 60% detail)
        splitter.setSizes([250, 400])
        main_layout.addWidget(splitter)

    def run_quick_search(self, query):
        self.search_input.setText(query)
        self.perform_search()

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        # UI State: Disable search and start progress
        self.search_btn.setEnabled(False)
        self.search_input.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_lbl.setText(f"Searching Lex.uz & local indices for '{query}'...")
        self.results_list.clear()
        self.detail_browser.clear()

        # Instantiate background worker
        self.worker = LexScraperWorker(query)
        self.worker.finished.connect(self.on_search_finished)
        self.worker.error_occurred.connect(self.on_search_error)
        self.worker.start()

    def on_search_finished(self, results):
        # Reset UI controls
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_lbl.setText(f"Found {len(results)} legislative matches.")

        if not results:
            self.detail_browser.setHtml(
                "<div style='color:#ff1744; font-weight:bold; margin-top:20px; text-align:center;'>"
                "No documents matched your query.<br>Try broader terms like 'soliq', 'kredit', or 'MChJ'."
                "</div>"
            )
            return

        # Store complete dictionary context in user data role of list items
        for r in results:
            item = QListWidgetItem()
            source_tag = "[LOCAL]" if r["source"].startswith("Local") else "[LIVE]"
            item.setText(f"{source_tag} {r['title']}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.results_list.addItem(item)

        # Auto-select the first item
        self.results_list.setCurrentRow(0)

    def on_search_error(self, err_msg):
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_lbl.setText("Search completed with errors.")
        QMessageBox.critical(self, "Search Error", f"Search routine failed: {err_msg}")

    def display_selected_result(self):
        selected_items = self.results_list.selectedItems()
        if not selected_items:
            self.detail_browser.clear()
            return

        item = selected_items[0]
        data = item.data(Qt.ItemDataRole.UserRole)
        
        # Build HTML content for details pane
        title = data["title"]
        source = data["source"]
        summary = data["summary"]
        details = data["details"]
        link = data["link"]

        html = f"""
        <html>
        <head>
            <style>
                body {{
                    background-color: #1e1e1e;
                    color: #b3b3b3;
                    font-family: Arial, sans-serif;
                    line-height: 1.5;
                    margin: 15px;
                }}
                h2 {{
                    color: #00f0ff;
                    font-size: 16px;
                    border-bottom: 1px solid #2d2d2d;
                    padding-bottom: 6px;
                    margin-top: 0;
                }}
                .meta-box {{
                    background-color: #252525;
                    border-left: 3px solid #00f0ff;
                    padding: 8px 12px;
                    margin-bottom: 15px;
                }}
                .meta-label {{
                    font-weight: bold;
                    color: #ffffff;
                }}
                .desc-box {{
                    margin-bottom: 20px;
                }}
                .detail-title {{
                    font-weight: bold;
                    color: #ffffff;
                    margin-bottom: 8px;
                }}
                .link-btn {{
                    display: inline-block;
                    background-color: #1a1a1a;
                    color: #00f0ff;
                    border: 1px solid #00f0ff;
                    padding: 6px 12px;
                    border-radius: 4px;
                    text-decoration: none;
                    font-weight: bold;
                    margin-top: 10px;
                }}
                .link-btn:hover {{
                    background-color: #00f0ff;
                    color: #121212;
                }}
            </style>
        </head>
        <body>
            <h2>{title}</h2>
            <div class="meta-box">
                <span class="meta-label">Data Source:</span> {source}<br/>
                <span class="meta-label">Reference Path:</span> {link}
            </div>
            
            <div class="desc-box">
                <div class="detail-title">Regulation Summary:</div>
                <div>{summary}</div>
            </div>
            
            <div class="desc-box">
                <div class="detail-title">Operational Details & Scope:</div>
                <div>{details.replace(chr(10), '<br/>')}</div>
            </div>
        """
        
        if link and link.startswith("http"):
            html += f"""
            <div style="margin-top: 25px;">
                <a href="{link}" class="link-btn">Open Official Document on Lex.uz</a>
            </div>
            """
            
        html += """
        </body>
        </html>
        """
        self.detail_browser.setHtml(html)
