import os
import json
import requests
import pypdf
from PyQt6.QtCore import QThread, pyqtSignal

# List of models supported by DuckDuckGo Chat:
# - gpt-4o-mini
# - meta-llama/Llama-3-70b-instruct
# - mistralai/Mixtral-8x7B-Instruct-v0.1
# - claude-3-haiku

class DDGChatClient:
    def __init__(self, model="gpt-4o-mini"):
        self.model = model
        self.vqd = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*"
        })

    def get_vqd(self):
        """Fetches a fresh VQD token from the DuckDuckGo status endpoint."""
        try:
            headers = {"x-vqd-4": "1"}
            resp = self.session.get("https://duckduckgo.com/duckchat/v1/status", headers=headers, timeout=10)
            if resp.status_code == 200:
                vqd = resp.headers.get("x-vqd-4")
                if vqd:
                    self.vqd = vqd
                    return vqd
            raise Exception(f"Failed to fetch VQD. Status: {resp.status_code}")
        except Exception as e:
            print(f"Error fetching VQD: {e}")
            return None

    def send_message_stream(self, prompt, history=None, system_context=""):
        """
        Sends a message and yields chunks of the response.
        If it fails, it falls back to a high-quality offline rule-based advisory response.
        """
        if not self.vqd:
            self.get_vqd()
            
        if not self.vqd:
            # No network or blocked - yield offline fallback
            yield from self._get_offline_fallback(prompt, system_context)
            return

        url = "https://duckduckgo.com/duckchat/v1/chat"
        headers = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "x-vqd-4": self.vqd
        }
        
        # Build messages
        messages = []
        if system_context:
            messages.append({"role": "system", "content": system_context})
            
        if history:
            for h in history:
                # Map role to what DDG expects: 'user' or 'assistant'
                role = "user" if h.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": h.get("content", "")})
                
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages
        }
        
        try:
            resp = self.session.post(url, headers=headers, json=payload, stream=True, timeout=15)
            if resp.status_code == 200:
                # Update VQD token for subsequent requests in this conversation
                new_vqd = resp.headers.get("x-vqd-4")
                if new_vqd:
                    self.vqd = new_vqd
                
                full_text = ""
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data:"):
                        data_content = line_str[5:].strip()
                        if data_content == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_content)
                            chunk = data_json.get("message", "")
                            if chunk:
                                full_text += chunk
                                yield chunk
                        except json.JSONDecodeError:
                            continue
                return
            else:
                print(f"DDG Chat API returned status {resp.status_code}: {resp.text}")
                # Fallback on HTTP error
                yield from self._get_offline_fallback(prompt, system_context)
        except Exception as e:
            print(f"DDG Chat Exception: {e}")
            # Fallback on network/other exception
            yield from self._get_offline_fallback(prompt, system_context)

    def _get_offline_fallback(self, prompt, system_context):
        """Generates a rich, context-aware local advisory response for offline mode."""
        prompt_lower = prompt.lower()
        
        # Extract company details from system context if possible
        company_info = "your business"
        if "Company Name" in system_context:
            try:
                for line in system_context.split("\n"):
                    if "Company Name" in line:
                        company_info = line.split(":")[-1].strip()
                        break
            except Exception:
                pass

        yield f"⚠️ **[OFFLINE MODE]** *Notice: Unable to connect to the online AI engine (rate-limited or offline). Providing localized baseline advisory guidance for {company_info}:*\n\n"
        
        if "tax" in prompt_lower or "soliq" in prompt_lower:
            yield "### 📊 Uzbekistan Tax Framework Guidelines:\n"
            yield "- **Turnover Tax (Aylanmadan olinadigan soliq)**: Default rate is 4% for most sectors. If your turnover is under 1 billion UZS annually, this is highly recommended for simplicity.\n"
            yield "- **General Tax Regime**: If annual turnover exceeds 1 billion UZS, you transition to General Taxes: VAT (QQS) at 12%, Profit Tax (Foyda solig'i) at 15% (7.5% for certain sectors), and Property Tax at 1.5%.\n"
            yield "- **IT-Park Incentives**: If you register in IT-Park, you get 0% Corporate Income Tax, 0% VAT, and a reduced Social Tax of 7.5% (instead of 12%).\n\n"
            yield "*Recommendation: Monitor your gross revenues monthly to avoid unplanned VAT transitions.*"
        elif "register" in prompt_lower or "mchj" in prompt_lower or "incorporate" in prompt_lower or "llc" in prompt_lower:
            yield "### 🏢 Steps to Incorporate an LLC (MChJ) in Uzbekistan:\n"
            yield "1. **Name Reservation**: Check and reserve a unique name online via `my.gov.uz`.\n"
            yield "2. **Statutory Fund**: Formulate the Statutory Fund (Ustav Fondi). There is no longer a strict legal minimum for general LLCs, but having a realistic amount (e.g., 10-20 million UZS) helps build trust with banks.\n"
            yield "3. **Founding Documents**: Draft the Founding Agreement (Ta'sis shartnomasi) and Charter (Ustav).\n"
            yield "4. **Online Registration**: Register online via `fo.birdarcha.uz` using the founders' E-Signatures (ERI).\n"
            yield "5. **Bank Account & Seal**: Open a commercial bank account (e.g., Kapitalbank, Hamkorbank) and obtain an official stamp.\n"
        elif "loan" in prompt_lower or "credit" in prompt_lower or "capital" in prompt_lower or "moliya" in prompt_lower:
            yield "### 💰 Financing & Microloans in Uzbekistan:\n"
            yield "- **Microloans**: Available for small businesses up to 300 million UZS without complex collateral, often backed by the State Entrepreneurship Support Fund.\n"
            yield "- **Interest Rates**: Typically range from 18% to 26% annually for national currency (UZS) commercial loans.\n"
            yield "- **Collateral Requirements**: Real estate, vehicles, or guarantees from third parties are standard. Look into credit guarantee programs if collateral is insufficient.\n"
        else:
            yield "### 💡 Business Advisory Outline:\n"
            yield f"For a business operating in the context of: *{system_context.replace(chr(10), ' | ')}*:\n\n"
            yield "1. **Compliance Check**: Verify that your activity is permitted under your selected OKED (classification of economic activities).\n"
            yield "2. **Statutory Capital**: Ensure your 'Ustav Fondi' is officially logged in your Charter. You can track this in our **Financial Calculator** tab.\n"
            yield "3. **Tax Optimization**: For service and consulting sectors, check if a turnover-based tax system is more efficient than the general tax system.\n"
            yield "4. **Digitalization**: Remember that all invoices in Uzbekistan must be issued electronically (E-Faktura) and all retail operations must use virtual cash registers (Virtual Kassa).\n"


class AIChatWorker(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str, str)  # (full_response, updated_vqd)
    error_occurred = pyqtSignal(str)

    def __init__(self, prompt, history, system_context, model="gpt-4o-mini", vqd=None):
        super().__init__()
        self.prompt = prompt
        self.history = history
        self.system_context = system_context
        self.model = model
        self.vqd = vqd

    def run(self):
        try:
            client = DDGChatClient(model=self.model)
            if self.vqd:
                client.vqd = self.vqd
            
            full_response = ""
            for chunk in client.send_message_stream(
                self.prompt, 
                history=self.history, 
                system_context=self.system_context
            ):
                full_response += chunk
                self.chunk_received.emit(chunk)
            
            self.finished.emit(full_response, client.vqd or "")
        except Exception as e:
            self.error_occurred.emit(str(e))


def extract_text_from_pdf(file_path):
    """Extracts raw text from a PDF file using pypdf."""
    try:
        reader = pypdf.PdfReader(file_path)
        text = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text.append(f"--- Page {i+1} ---\n{page_text}")
        return "\n".join(text)
    except Exception as e:
        return f"[PDF Extraction Error: {str(e)}]"
