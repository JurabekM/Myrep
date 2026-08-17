import g4f
from g4f.client import Client
from core.logger import app_logger
from domain.schemas import ChatRequest, ChatResponse

# Initialize g4f client
client = Client()

class AIService:
    """
    Service for interacting with AI using g4f (free API without keys).
    Implements a fallback mechanism across providers.
    """
    
    def __init__(self):
        self.system_prompt = (
            "Siz 'AI Business Advisor Uzbekistan' - O'zbekiston bozoridagi "
            "kichik va o'rta bizneslar uchun maxsus professional biznes maslahatchisiz. "
            "Javoblaringiz aniq, professional, Markdown formatida bo'lishi kerak. "
            "Huquqiy yoki moliyaviy maslahatlar berganingizda, albatta yurist yoki "
            "buxgalter bilan maslahatlashish zarurligini eslatib o'ting."
        )

    def generate_response(self, request: ChatRequest) -> ChatResponse:
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if request.context:
            messages.append({
                "role": "user",
                "content": f"Kontekst ma'lumotlari:\n{request.context}\n\nFoydalanuvchi savoli: {request.message}"
            })
        else:
            messages.append({"role": "user", "content": request.message})

        try:
            # Using g4f to get a free AI response
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # It will map to available free models
                messages=messages,
                # providers can be specified if needed, but client auto-routes
            )
            
            content = response.choices[0].message.content
            
            return ChatResponse(
                message=content,
                confidence_score=0.85, # Base confidence, can be dynamic
                sources=[]
            )
        except Exception as e:
            app_logger.error(f"AI Service error: {e}")
            return ChatResponse(
                message="Kechirasiz, sun'iy intellekt xizmati bilan ulanishda xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring.",
                confidence_score=0.0
            )

ai_service = AIService()
