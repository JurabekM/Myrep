import os
import re
import uuid
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QScrollArea, QFrame, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ai_client import AIChatWorker, extract_text_from_pdf
import database

class ChatBubble(QFrame):
    def __init__(self, role, text, parent=None):
        super().__init__(parent)
        self.role = role
        self.raw_text = text
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        self.sender_lbl = QLabel()
        self.sender_lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
        
        self.body_lbl = QLabel()
        self.body_lbl.setWordWrap(True)
        self.body_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        layout.addWidget(self.sender_lbl)
        layout.addWidget(self.body_lbl)
        
        # Apply distinct styles for user vs advisor bubbles
        if self.role == "user":
            self.sender_lbl.setText("YOU")
            self.sender_lbl.setStyleSheet("font-weight: bold; font-size: 11px; color: #00f0ff;")
            self.body_lbl.setStyleSheet("color: #ffffff;")
            self.setStyleSheet("""
                ChatBubble {
                    background-color: rgba(0, 240, 255, 0.08);
                    border: 1px solid #00f0ff;
                    border-radius: 8px;
                }
            """)
        else:
            self.sender_lbl.setText("VIRTUAL ADVISOR")
            self.sender_lbl.setStyleSheet("font-weight: bold; font-size: 11px; color: #00e676;")
            self.body_lbl.setStyleSheet("color: #e0e0e0;")
            self.setStyleSheet("""
                ChatBubble {
                    background-color: #1e1e1e;
                    border: 1px solid #2d2d2d;
                    border-radius: 8px;
                }
            """)
        
        self.update_content(self.raw_text)

    def update_content(self, text):
        self.raw_text = text
        
        # Escape simple HTML brackets to prevent QLabel rendering glitches
        html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Convert code blocks: ```code```
        # Use a temporary replacement token to avoid regex conflicts
        code_blocks = []
        def code_block_sub(match):
            code_blocks.append(match.group(1))
            return f"__CODE_BLOCK_{len(code_blocks)-1}__"
            
        html = re.sub(r'```(.*?)```', code_block_sub, html, flags=re.DOTALL)
        
        # Format bold tags: **bold**
        html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html)
        
        # Format bullet points at the start of a line
        html_lines = []
        for line in html.split("\n"):
            stripped = line.strip()
            if stripped.startswith("* ") or stripped.startswith("- "):
                html_lines.append(f"• {stripped[2:]}")
            else:
                html_lines.append(line)
        html = "<br>".join(html_lines)
        
        # Re-inject and format code blocks
        for idx, cb_text in enumerate(code_blocks):
            formatted_cb = (
                f'<pre style="background-color:#121212; color:#00f0ff; '
                f'font-family:Consolas, monospace; padding:8px; border-radius:4px;">'
                f'{cb_text.strip()}</pre>'
            )
            html = html.replace(f"__CODE_BLOCK_{idx}__", formatted_cb)
            
        self.body_lbl.setText(html)

    def append_chunk(self, chunk):
        self.update_content(self.raw_text + chunk)


class ChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_id = str(uuid.uuid4())
        self.vqd_token = None
        
        self.attached_name = None
        self.attached_text = None
        
        self.init_ui()
        self.setAcceptDrops(True)
        self.load_session_history()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header bar
        header_layout = QHBoxLayout()
        title_lbl = QLabel("AI Virtual Advisor")
        title_lbl.setObjectName("title-lbl")
        header_layout.addWidget(title_lbl)

        header_layout.addStretch()
        
        self.new_chat_btn = QPushButton("New Session")
        self.new_chat_btn.clicked.connect(self.start_new_session)
        header_layout.addWidget(self.new_chat_btn)

        main_layout.addLayout(header_layout)

        # Scroll Area for Chat Viewport
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #2d2d2d; border-radius: 6px; }")
        
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(15, 15, 15, 15)
        self.scroll_layout.setSpacing(12)
        self.scroll_layout.addStretch()  # Forces bubbles to align at top/bottom
        
        self.scroll_area.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scroll_area)
        
        # Connect vertical scroll bar to auto scroll down
        self.scroll_area.verticalScrollBar().rangeChanged.connect(self.auto_scroll_down)

        # Attachment Banner (Hidden by default)
        self.attach_banner = QFrame()
        self.attach_banner.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 240, 255, 0.1);
                border: 1px solid #00f0ff;
                border-radius: 4px;
                padding: 5px;
            }
            QLabel {
                color: #00f0ff;
                font-weight: bold;
            }
        """)
        attach_layout = QHBoxLayout(self.attach_banner)
        attach_layout.setContentsMargins(8, 4, 8, 4)
        
        self.attach_lbl = QLabel("📄 Attached File: None")
        attach_layout.addWidget(self.attach_lbl)
        
        attach_layout.addStretch()
        
        remove_attach_btn = QPushButton("Remove")
        remove_attach_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #ff1744;
                color: #ff1744;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #ff1744;
                color: #ffffff;
            }
        """)
        remove_attach_btn.clicked.connect(self.clear_attachment)
        attach_layout.addWidget(remove_attach_btn)
        
        self.attach_banner.setVisible(False)
        main_layout.addWidget(self.attach_banner)

        # Drop instruction overlay guide label
        self.drop_guide = QLabel("💡 Drag-and-drop a PDF/TXT document here to inject its context into the advisor.")
        self.drop_guide.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_guide.setStyleSheet("color: #666666; font-size: 11px;")
        main_layout.addWidget(self.drop_guide)

        # Input Area Panel
        input_layout = QHBoxLayout()
        
        self.attach_btn = QPushButton("📎 Attach")
        self.attach_btn.setToolTip("Upload text/PDF files locally to query context")
        self.attach_btn.clicked.connect(self.open_file_dialog)
        input_layout.addWidget(self.attach_btn)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask a question about tax compliance, registration, or business finance...")
        self.input_field.returnPressed.connect(self.send_user_message)
        input_layout.addWidget(self.input_field, 5)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("accent-btn")
        self.send_btn.clicked.connect(self.send_user_message)
        input_layout.addWidget(self.send_btn)

        main_layout.addLayout(input_layout)

    # --- History Loader ---
    def load_session_history(self):
        # Clear bubbles in layout (keep the stretch at the bottom)
        for i in reversed(range(self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
                
        history = database.get_chat_history(self.session_id)
        for msg in history:
            bubble = ChatBubble(msg["role"], msg["content"])
            # Insert widget before the stretch at the end
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, bubble)

    def start_new_session(self):
        self.session_id = str(uuid.uuid4())
        self.vqd_token = None
        self.clear_attachment()
        self.load_session_history()
        
        # Insert introductory greeting from Virtual Advisor
        intro = (
            "Hello! I am your AI Business Advisor. I can assist you with:\n"
            "- Tax optimizations (Turnover vs. General vs. IT-Park)\n"
            "- Incorporating an LLC (MChJ) and legal procedures\n"
            "- Local finance, microloan structures, and statutory logs\n"
            "\n"
            "Drop any business plan, text draft, or compliance document PDF/TXT here to begin context auditing."
        )
        intro_bubble = ChatBubble("assistant", intro)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, intro_bubble)

    def auto_scroll_down(self, min_val, max_val):
        self.scroll_area.verticalScrollBar().setValue(max_val)

    # --- Drag & Drop Core handlers ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("border: 1px solid #00f0ff;") # cyan highlight focus
            
    def dragLeaveEvent(self, event):
        self.setStyleSheet("") # Reset stylesheet

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.setStyleSheet("")
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                self.process_attached_file(file_path)
                event.acceptProposedAction()

    # --- File Handlers ---
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Attach Business Document", "", "Supported Files (*.pdf *.txt)"
        )
        if file_path:
            self.process_attached_file(file_path)

    def process_attached_file(self, file_path):
        name = os.path.basename(file_path)
        ext = os.path.splitext(name)[1].lower()
        
        # Check size limit
        try:
            sz_mb = os.path.getsize(file_path) / (1024 * 1024)
            if sz_mb > 15.0:
                QMessageBox.warning(self, "Limit Exceeded", f"File '{name}' exceeds the 15MB parse limit.")
                return
        except Exception as e:
            QMessageBox.critical(self, "Access Error", f"Unable to read file size: {e}")
            return

        # Parse file text contents
        text_content = ""
        if ext == ".pdf":
            self.status_lbl.setText("Extracting PDF contents locally...")
            text_content = extract_text_from_pdf(file_path)
            self.status_lbl.setText("")
        elif ext == ".txt" or ext == ".md":
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text_content = f.read()
            except Exception as e:
                QMessageBox.critical(self, "Parse Error", f"Failed to read TXT file: {e}")
                return
        else:
            QMessageBox.warning(self, "Unsupported Format", "Only PDF and standard TXT/MD files are supported.")
            return

        if text_content.startswith("[PDF Extraction Error"):
            QMessageBox.critical(self, "Extraction Failed", text_content)
            return

        self.attached_name = name
        self.attached_text = text_content
        self.attach_lbl.setText(f"📄 Attached Context: {name} ({len(text_content)} chars)")
        self.attach_banner.setVisible(True)

    def clear_attachment(self):
        self.attached_name = None
        self.attached_text = None
        self.attach_banner.setVisible(False)

    # --- Messaging ---
    def send_user_message(self):
        query = self.input_field.text().strip()
        if not query:
            return

        self.input_field.clear()
        
        # Append attachment context to prompt if available
        full_prompt = ""
        if self.attached_text:
            full_prompt += (
                f"### ATTACHED LOCAL BUSINESS DOCUMENT: {self.attached_name} ###\n"
                f"{self.attached_text}\n"
                f"### END OF DOCUMENT CONTEXT ###\n\n"
                f"Question about the document or general business: "
            )
            
        full_prompt += query
        
        # User message display
        user_bubble = ChatBubble("user", query)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, user_bubble)
        
        # Persist to database
        database.add_chat_message(self.session_id, "user", query)

        # Clear attachment state after prepending to query
        self.clear_attachment()

        # Build System Prompt Context from Company profile
        settings = database.get_settings()
        sys_context = (
            f"You are the senior Virtual Advisor for the following small business in Uzbekistan:\n"
            f"- Company Name: {settings.get('company_name')}\n"
            f"- Industry Sector: {settings.get('industry')}\n"
            f"- Declared Capital: {settings.get('capital'):,.2f} UZS\n"
            f"- Staff Size: {settings.get('employees')} employees\n"
            f"- Base Region: {settings.get('region')}\n\n"
            f"Rule 1: Give professional, compliant, and highly structured advice tailored to the startup profile.\n"
            f"Rule 2: Anchor answers with references to Uzbek regulatory realities (Soliq, LLC/MChJ codes, BHM rates, IT-Park rules).\n"
            f"Rule 3: Keep calculations clear. Use UZS currency details where appropriate."
        )

        # Load history for the DDG client context
        history_rows = database.get_chat_history(self.session_id)
        # Avoid including the current message in the history parameter since it's passed as the main prompt
        history_payload = history_rows[:-1] if len(history_rows) > 0 else []

        # Disable inputs during generation
        self.input_field.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.new_chat_btn.setEnabled(False)
        self.attach_btn.setEnabled(False)

        # Create response bubble placeholder
        self.advisor_bubble = ChatBubble("assistant", "")
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, self.advisor_bubble)

        # Instantiate background thread worker
        self.worker = AIChatWorker(
            prompt=full_prompt, 
            history=history_payload, 
            system_context=sys_context,
            model="gpt-4o-mini",
            vqd=self.vqd_token
        )
        self.worker.chunk_received.connect(self.on_chunk_received)
        self.worker.finished.connect(self.on_chat_finished)
        self.worker.error_occurred.connect(self.on_chat_error)
        self.worker.start()

    def on_chunk_received(self, chunk):
        self.advisor_bubble.append_chunk(chunk)

    def on_chat_finished(self, full_response, updated_vqd):
        self.vqd_token = updated_vqd
        
        # Save complete AI response to SQLite history
        database.add_chat_message(self.session_id, "assistant", full_response)
        
        # Re-enable inputs
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.new_chat_btn.setEnabled(True)
        self.attach_btn.setEnabled(True)
        self.input_field.setFocus()

    def on_chat_error(self, err_msg):
        self.advisor_bubble.append_chunk(f"\n\n❌ [Chat Error: {err_msg}]")
        
        # Re-enable inputs
        self.input_field.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.new_chat_btn.setEnabled(True)
        self.attach_btn.setEnabled(True)
        self.input_field.setFocus()
