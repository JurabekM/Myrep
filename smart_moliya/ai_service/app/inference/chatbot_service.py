"""AI Chatbot - intent-based, uz/ru/en.

Hozircha kalit so'z asosidagi deterministik javob beruvchi baseline (LLM API kaliti
talab qilinmaydi). Kelgusida haqiqiy LLM (RAG bilan foydalanuvchi tranzaksiya
kontekstidan foydalangan holda) ulanishi mumkin - shu interfeys (`ChatbotService.reply`)
o'zgarmasdan qoladi, faqat implementatsiya almashtiriladi.
"""

INTENT_KEYWORDS: dict[str, list[str]] = {
    "balance": ["balans", "qancha pul", "баланс", "сколько денег", "balance", "how much money"],
    "spending_summary": ["sarfladim", "xarajat qildim", "потратил", "spent", "spending"],
    "save_advice": ["tejash", "qanday tejayman", "экономить", "save money", "saving"],
    "debt_advice": ["qarz", "kredit", "долг", "кредит", "debt", "loan"],
    "greeting": ["salom", "assalomu", "привет", "hello", "hi"],
}

RESPONSES: dict[str, dict[str, str]] = {
    "balance": {
        "uz": "Joriy balansingizni Bosh sahifa bo'limida ko'rishingiz mumkin. Aniq raqamni so'rasangiz, hamyonlaringizni tekshirib chiqaman.",
        "ru": "Текущий баланс можно увидеть на главном экране. Уточните, какой именно кошелёк вас интересует.",
        "en": "You can see your current balance on the Dashboard. Let me know which wallet you'd like details on.",
    },
    "spending_summary": {
        "uz": "Bu oy xarajatlaringizni Hisobotlar bo'limida kategoriya bo'yicha ko'rishingiz mumkin.",
        "ru": "Расходы за этот месяц по категориям доступны в разделе Отчёты.",
        "en": "You can see this month's spending broken down by category in the Reports section.",
    },
    "save_advice": {
        "uz": "Eng samarali usul - '50/30/20' qoidasi: daromadning 50% zaruriy ehtiyojlarga, 30% istaklarga, 20% tejashga. Byudjet bo'limida limit belgilab, avtomatik nazorat qilishingiz mumkin.",
        "ru": "Эффективный метод - правило '50/30/20': 50% дохода на необходимое, 30% на желания, 20% на сбережения. Установите лимит в разделе Бюджет для автоматического контроля.",
        "en": "A proven method is the 50/30/20 rule: 50% of income on needs, 30% on wants, 20% on savings. Set a limit in the Budget section for automatic tracking.",
    },
    "debt_advice": {
        "uz": "Qarzlaringizni 'Qarz Manager' bo'limida ro'yxatga oling va eng yuqori foizli qarzni birinchi navbatda yoping (avalanche usuli) - bu umumiy foiz to'lovlarini kamaytiradi.",
        "ru": "Занесите все долги в раздел 'Управление долгами' и в первую очередь закрывайте долг с наибольшей процентной ставкой (метод лавины) - это снизит переплату.",
        "en": "List your debts in the Loan Manager and pay off the highest-interest debt first (avalanche method) - this minimizes total interest paid.",
    },
    "greeting": {
        "uz": "Salom! Men Smart Moliya AI yordamchisiman. Byudjet, tejash yoki qarzlaringiz haqida so'rashingiz mumkin.",
        "ru": "Здравствуйте! Я AI-помощник Smart Moliya. Спросите меня о бюджете, накоплениях или долгах.",
        "en": "Hello! I'm your Smart Moliya AI assistant. Ask me about your budget, savings, or debts.",
    },
    "unknown": {
        "uz": "Kechirasiz, buni tushunmadim. Balans, xarajatlar, tejash yoki qarzlar haqida so'rab ko'ring.",
        "ru": "Извините, я не понял вопрос. Попробуйте спросить о балансе, расходах, накоплениях или долгах.",
        "en": "Sorry, I didn't understand that. Try asking about your balance, spending, savings, or debts.",
    },
}


class ChatbotService:
    def detect_intent(self, message: str) -> str:
        lowered = message.lower()
        for intent, keywords in INTENT_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return intent
        return "unknown"

    def reply(self, message: str, language: str = "uz") -> dict:
        intent = self.detect_intent(message)
        lang = language if language in ("uz", "ru", "en") else "uz"
        return {"intent": intent, "reply": RESPONSES[intent][lang]}


_chatbot_service: ChatbotService | None = None


def get_chatbot_service() -> ChatbotService:
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service
