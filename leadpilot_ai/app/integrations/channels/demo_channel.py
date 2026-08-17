"""Demo channel adapter: simulates realistic Uzbek/Russian customer traffic.

Used whenever no real credentials are configured so every flow of the product
remains fully testable offline.
"""

from __future__ import annotations

import itertools
import random
from collections import deque

from app.integrations.base import AdapterResult, IncomingMessage
from app.integrations.channels.base_channel import ChannelAdapter
from app.models.enums import Channel
from app.utils.dates import now

#: Scripted first messages used when simulating a brand new lead.
DEMO_FIRST_MESSAGES: list[tuple[str, str, str]] = [
    ("uz", Channel.TELEGRAM, "Assalomu alaykum, dermatolog qabuliga yozilmoqchi edim."),
    ("uz", Channel.TELEGRAM, "Salom, lazer epilyatsiya narxi qancha?"),
    ("ru", Channel.INSTAGRAM, "Здравствуйте, сколько стоит УЗИ?"),
    ("ru", Channel.WHATSAPP, "Добрый день! Можно записаться к стоматологу на завтра?"),
    ("uz", Channel.WEBSITE, "Stomatologiya bo'yicha bugun bo'sh vaqt bormi?"),
    ("uz", Channel.INSTAGRAM, "Narxlaringizni yuboring iltimos"),
    ("ru", Channel.TELEGRAM, "Хочу проконсультироваться, у вас есть скидки?"),
]

#: Scripted follow-up replies used when simulating an ongoing dialogue.
DEMO_FOLLOWUPS: dict[str, list[str]] = {
    "uz": [
        "Ha, bugun kelsam bo'ladimi?",
        "Narxi menga qimmatroq tuyuldi, chegirma bormi?",
        "Telefon raqamim +998901234567",
        "Rahmat, ertaga soat 15:00 ga yozing",
        "Menga operator bilan gaplashish kerak",
        "Yaxshi, kelaman",
    ],
    "ru": [
        "А можно сегодня?",
        "Дороговато, есть скидка?",
        "Мой номер +998935554433",
        "Хорошо, запишите на завтра в 15:00",
        "Соедините меня с оператором, пожалуйста",
        "Спасибо, приду",
    ],
}

DEMO_NAMES_UZ = ["Nodira Karimova", "Sardor Umarov", "Gulnora Sattorova", "Bekzod Rasulov"]
DEMO_NAMES_RU = ["Ольга Петрова", "Игорь Ким", "Анна Смирнова", "Дмитрий Ли"]


class DemoChannelAdapter(ChannelAdapter):
    """In-memory channel that never touches the network."""

    provider = "demo_channel"
    title = "Demo kanal"
    is_demo = True

    _counter = itertools.count(1)

    def __init__(self, channel: str = Channel.DEMO, seed: int | None = None) -> None:
        super().__init__()
        self.channel = channel
        self._queue: deque[IncomingMessage] = deque()
        self._sent: list[dict[str, str]] = []
        self._random = random.Random(seed)

    # ------------------------------------------------------------------ #
    # ChannelAdapter contract
    # ------------------------------------------------------------------ #
    def test_connection(self) -> AdapterResult:
        """The demo adapter is always available."""
        self.last_sync_at = now()
        return AdapterResult.success("Demo rejim faol")

    def send_message(
        self, chat_id: str, text: str, attachments: list[str] | None = None
    ) -> AdapterResult:
        """Pretend to deliver a message and remember it for inspection."""
        self._sent.append({"chat_id": chat_id, "text": text})
        self.last_sync_at = now()
        return AdapterResult.success(
            "Demo yuborildi", external_id=f"demo-{next(self._counter)}", chat_id=chat_id
        )

    def poll(self) -> list[IncomingMessage]:
        """Drain the queue of simulated inbound messages."""
        drained = list(self._queue)
        self._queue.clear()
        self.last_sync_at = now()
        return drained

    # ------------------------------------------------------------------ #
    # Simulation helpers used by the UI ("Simulate incoming message")
    # ------------------------------------------------------------------ #
    def enqueue(self, message: IncomingMessage) -> None:
        """Push a prepared message into the inbound queue."""
        self._queue.append(message)

    def simulate_new_lead(self, channel: str | None = None) -> IncomingMessage:
        """Create a brand new customer with a scripted first message."""
        lang, default_channel, text = self._random.choice(DEMO_FIRST_MESSAGES)
        used_channel = channel or default_channel
        name = self._random.choice(DEMO_NAMES_UZ if lang == "uz" else DEMO_NAMES_RU)
        chat_id = f"demo-{used_channel}-{self._random.randint(100000, 999999)}"
        message = IncomingMessage(
            channel=used_channel,
            external_chat_id=chat_id,
            text=text,
            sender_name=name,
            sender_username=name.split()[0].lower(),
            phone=None,
            external_message_id=f"demo-msg-{next(self._counter)}",
            utm={
                "utm_source": self._random.choice(
                    ["instagram", "google", "telegram", "instagram_organic"]
                ),
                "utm_medium": self._random.choice(["cpc", "social", "organic"]),
                "utm_campaign": self._random.choice(
                    ["avgust_aksiya", "brand_search", "kanal_post", ""]
                ),
            },
        )
        self.enqueue(message)
        return message

    def simulate_reply(self, chat_id: str, channel: str, language: str = "uz") -> IncomingMessage:
        """Create a scripted follow-up message for an existing conversation."""
        pool = DEMO_FOLLOWUPS.get(language, DEMO_FOLLOWUPS["uz"])
        message = IncomingMessage(
            channel=channel,
            external_chat_id=chat_id,
            text=self._random.choice(pool),
            external_message_id=f"demo-msg-{next(self._counter)}",
        )
        self.enqueue(message)
        return message

    def simulate_custom(self, chat_id: str, channel: str, text: str) -> IncomingMessage:
        """Create an arbitrary inbound message (used by the simulator dialog)."""
        message = IncomingMessage(
            channel=channel,
            external_chat_id=chat_id,
            text=text,
            external_message_id=f"demo-msg-{next(self._counter)}",
        )
        self.enqueue(message)
        return message

    @property
    def sent_messages(self) -> list[dict[str, str]]:
        """All messages this adapter 'delivered' (for tests and debugging)."""
        return list(self._sent)
