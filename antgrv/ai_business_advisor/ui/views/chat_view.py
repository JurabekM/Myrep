from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLineEdit, QPushButton, QLabel, QScrollArea, QFrame,
    QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from domain.schemas import ChatRequest
from services.ai_service import ai_service
from services.document_service import document_service

class WorkerThread(QThread):
    result_ready = pyqtSignal(str)
    
    def __init__(self, request: ChatRequest):
        super().__init__()
        self.request = request

    def run(self):
        response = ai_service.generate_response(self.request)
        self.result_ready.emit(response.message)

class ChatBubble(QFrame):
    def __init__(self, text: str, is_user: bool = True):
        super().__init__()
        self.setObjectName("UserBubble" if is_user else "AIBubble")
        layout = QVBoxLayout(self)
        
        # We can use Markdown parsing here if needed. 
        # QTextEdit supports basic HTML/Rich Text which works for simple markdown
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        layout.addWidget(label)

class ChatView(QWidget):
    def __init__(self, session_id: str = "default_session"):
        super().__init__()
        self.session_id = session_id
        self.context = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("AI Konsultant")
        header.setObjectName("HeaderLabel")
        layout.addWidget(header)

        # Context Info (if document uploaded)
        self.context_label = QLabel("Hujjat biriktirilmagan")
        self.context_label.setObjectName("SubHeaderLabel")
        layout.addWidget(self.context_label)

        # Chat Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.chat_layout = QVBoxLayout(self.scroll_content)
        self.chat_layout.addStretch() # Push messages to top
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        # Input Area
        input_layout = QHBoxLayout()
        
        self.btn_attach = QPushButton("📎")
        self.btn_attach.setFixedWidth(50)
        self.btn_attach.clicked.connect(self.attach_file)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Biznesingiz haqida savol bering...")
        self.input_field.returnPressed.connect(self.send_message)
        
        self.btn_send = QPushButton("Yuborish")
        self.btn_send.setObjectName("PrimaryButton")
        self.btn_send.clicked.connect(self.send_message)

        input_layout.addWidget(self.btn_attach)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.btn_send)

        layout.addLayout(input_layout)

    def attach_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Hujjat tanlang", "", 
            "All Files (*);;PDF (*.pdf);;Word (*.docx);;Excel (*.xlsx);;Images (*.png *.jpg)"
        )
        if file_path:
            self.context_label.setText(f"Hujjat o'qilmoqda: {file_path.split('/')[-1]}...")
            text = document_service.extract_text(file_path)
            if text:
                # Limit context size for free AI to prevent context length errors
                self.context = text[:15000] 
                self.context_label.setText(f"Context biriktirildi: {file_path.split('/')[-1]}")
            else:
                self.context_label.setText("Hujjatdan matn o'qib bo'lmadi.")

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.input_field.clear()
        self.add_message_bubble(text, True)

        req = ChatRequest(
            session_id=self.session_id,
            message=text,
            context=self.context if self.context else None
        )
        
        # Clear context after one use to save tokens
        self.context = ""
        self.context_label.setText("Hujjat biriktirilmagan")

        self.btn_send.setEnabled(False)
        self.input_field.setPlaceholderText("AI javob bermoqda...")
        
        self.worker = WorkerThread(req)
        self.worker.result_ready.connect(self.handle_response)
        self.worker.start()

    def handle_response(self, response_text: str):
        self.add_message_bubble(response_text, False)
        self.btn_send.setEnabled(True)
        self.input_field.setPlaceholderText("Biznesingiz haqida savol bering...")

    def add_message_bubble(self, text: str, is_user: bool):
        bubble = ChatBubble(text, is_user)
        # Insert before the stretch
        count = self.chat_layout.count()
        self.chat_layout.insertWidget(count - 1, bubble)
        
        # Scroll to bottom
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
