"""Demo data seeding: MedLine Clinic with realistic Uzbek/Russian traffic."""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.models.crm import (
    Lead,
    LeadActivity,
    MarketingCampaign,
    MarketingSource,
    RevenueRecord,
    Tag,
)
from app.models.enums import (
    AIInteractionStatus,
    AIState,
    BookingPurpose,
    BookingStatus,
    CallDirection,
    CallOutcome,
    Channel,
    ConversationStatus,
    IntentLevel,
    KBItemType,
    LeadStatus,
    LossReason,
    MarketingSourceType,
    MessageDirection,
    MessageSender,
    MessageStatus,
    NotificationLevel,
    RoleName,
    Sentiment,
    TaskPriority,
    TaskStatus,
    TaskType,
    ToneOfVoice,
)
from app.models.intelligence import AIInteraction, AIProfile, KnowledgeBaseItem
from app.models.messaging import Conversation, Message, QuickReply
from app.models.operations import (
    Booking,
    Call,
    CallAnalysis,
    CallTranscript,
    Notification,
    ScheduleSlot,
    Task,
)
from app.models.organization import Branch, Company, Role, Service, User
from app.services import auth_service, lead_service
from app.utils.dates import now
from app.utils.security import hash_password

logger = logging.getLogger(__name__)

DEMO_COMPANY = "MedLine Clinic"


def is_seeded(session: Session) -> bool:
    """Whether demo data already exists."""
    count = session.execute(select(func.count(Company.id))).scalar_one()
    return int(count) > 0


def seed_all(force: bool = False) -> bool:
    """Create the whole demo dataset. Returns ``True`` when data was written."""
    with session_scope() as session:
        auth_service.ensure_roles(session)
        if is_seeded(session) and not force:
            return False

        company = _seed_company(session)
        branches = _seed_branches(session, company)
        services = _seed_services(session, company, branches)
        users = _seed_users(session, company, branches)
        sources, campaigns = _seed_marketing(session)
        tags = _seed_tags(session)
        _seed_quick_replies(session)
        _seed_ai_profile(session, company)
        _seed_knowledge(session, company, services, branches)
        _seed_schedule(session, branches)
        lead_service.ensure_scoring_rules(session)
        leads = _seed_leads(session, company, services, branches, users, sources, campaigns, tags)
        _seed_conversations(session, leads, users)
        _seed_bookings(session, leads, services, branches, users)
        _seed_calls(session, leads, users)
        _seed_tasks(session, leads, users)
        _seed_notifications(session, leads, users)
        logger.info("Demo data seeded for %s", company.name)
        return True


# --------------------------------------------------------------------------- #
def _seed_company(session: Session) -> Company:
    """Create the demo clinic."""
    company = Company(
        name=DEMO_COMPANY,
        legal_name='MCHJ "MedLine Clinic"',
        industry="Klinika",
        phone="+998712001010",
        email="info@medline.uz",
        address="Toshkent sh., Amir Temur ko'chasi 12",
        default_language="uz",
        timezone="Asia/Tashkent",
        work_start="09:00",
        work_end="19:00",
        work_days="1,2,3,4,5,6",
        currency="so'm",
    )
    session.add(company)
    session.flush()
    return company


def _seed_branches(session: Session, company: Company) -> list[Branch]:
    """Two clinic branches."""
    branches = [
        Branch(
            company_id=company.id,
            name="Markaziy filial",
            address="Toshkent sh., Amir Temur 12",
            phone="+998712001010",
            work_start="09:00",
            work_end="19:00",
        ),
        Branch(
            company_id=company.id,
            name="Chilonzor filiali",
            address="Toshkent sh., Chilonzor 9-kvartal",
            phone="+998712001011",
            work_start="09:00",
            work_end="18:00",
        ),
    ]
    session.add_all(branches)
    session.flush()
    return branches


def _seed_services(session: Session, company: Company, branches: list[Branch]) -> list[Service]:
    """The four demo services required by the specification."""
    services = [
        Service(
            company_id=company.id,
            branch_id=branches[0].id,
            name="Dermatolog qabuli",
            name_ru="Приём дерматолога",
            category="Konsultatsiya",
            description="Teri kasalliklari bo'yicha mutaxassis ko'rigi.",
            price=150_000,
            duration_minutes=30,
        ),
        Service(
            company_id=company.id,
            branch_id=branches[0].id,
            name="Stomatologiya",
            name_ru="Стоматология",
            category="Davolash",
            description="Tish davolash va profilaktika.",
            price=250_000,
            price_max=900_000,
            duration_minutes=60,
        ),
        Service(
            company_id=company.id,
            branch_id=branches[1].id,
            name="Lazer epilyatsiya",
            name_ru="Лазерная эпиляция",
            category="Kosmetologiya",
            description="Zamonaviy diod lazer bilan epilyatsiya.",
            price=350_000,
            price_max=1_200_000,
            duration_minutes=45,
        ),
        Service(
            company_id=company.id,
            branch_id=branches[0].id,
            name="UZI tekshiruvi",
            name_ru="УЗИ обследование",
            category="Diagnostika",
            description="Qorin bo'shlig'i va qalqonsimon bez UZI.",
            price=120_000,
            duration_minutes=25,
        ),
    ]
    session.add_all(services)
    session.flush()
    return services


def _seed_users(session: Session, company: Company, branches: list[Branch]) -> dict[str, User]:
    """Administrator, sales manager, two operators and an analyst."""
    roles = {role.name: role for role in session.execute(select(Role)).scalars().all()}
    specs = [
        ("admin", "admin123", "Administrator", RoleName.ADMIN, "#3B82F6", False),
        ("rahbar", "rahbar123", "Aziz Rahimov", RoleName.SALES_MANAGER, "#A78BFA", False),
        ("dilnoza", "dilnoza123", "Dilnoza Karimova", RoleName.OPERATOR, "#22C55E", True),
        ("jamshid", "jamshid123", "Jamshid Aliyev", RoleName.OPERATOR, "#F59E0B", True),
        ("analitik", "analitik123", "Kamola Yusupova", RoleName.ANALYST, "#38BDF8", False),
    ]
    users: dict[str, User] = {}
    for username, password, full_name, role_name, color, is_operator in specs:
        user = User(
            company_id=company.id,
            role_id=roles[role_name].id,
            branch_id=branches[0].id,
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            email=f"{username}@medline.uz",
            phone="+99890" + str(1000000 + len(users) * 111111)[:7],
            language="uz",
            is_operator=is_operator,
            avatar_color=color,
        )
        session.add(user)
        users[username] = user
    session.flush()
    return users


def _seed_marketing(session: Session) -> tuple[list[MarketingSource], list[MarketingCampaign]]:
    """Demo advertising sources and campaigns with budgets."""
    sources = [
        MarketingSource(
            name="Instagram Ads", source_type=MarketingSourceType.META_ADS, utm_source="instagram"
        ),
        MarketingSource(
            name="Google Ads", source_type=MarketingSourceType.GOOGLE_ADS, utm_source="google"
        ),
        MarketingSource(
            name="Telegram kanal",
            source_type=MarketingSourceType.TELEGRAM_CHANNEL,
            utm_source="telegram",
        ),
        MarketingSource(
            name="Organik Instagram",
            source_type=MarketingSourceType.INSTAGRAM_ORGANIC,
            utm_source="instagram_organic",
        ),
    ]
    session.add_all(sources)
    session.flush()

    today = now().date()
    campaigns = [
        MarketingCampaign(
            source_id=sources[0].id,
            name="Avgust aksiya — lazer",
            utm_campaign="avgust_aksiya",
            utm_medium="cpc",
            cost=4_500_000,
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=15),
        ),
        MarketingCampaign(
            source_id=sources[1].id,
            name="Brend qidiruvi",
            utm_campaign="brand_search",
            utm_medium="cpc",
            cost=2_800_000,
            start_date=today - timedelta(days=60),
            end_date=today + timedelta(days=30),
        ),
        MarketingCampaign(
            source_id=sources[2].id,
            name="Kanal postlari",
            utm_campaign="kanal_post",
            utm_medium="social",
            cost=900_000,
            start_date=today - timedelta(days=20),
        ),
        MarketingCampaign(
            source_id=sources[3].id,
            name="Organik kontent",
            utm_campaign="organic",
            utm_medium="organic",
            cost=0,
            start_date=today - timedelta(days=90),
        ),
    ]
    session.add_all(campaigns)
    session.flush()
    return sources, campaigns


def _seed_tags(session: Session) -> list[Tag]:
    """Demo lead tags."""
    tags = [
        Tag(name="VIP", color="#A78BFA"),
        Tag(name="Qayta murojaat", color="#38BDF8"),
        Tag(name="Chegirma so'radi", color="#F59E0B"),
        Tag(name="Shikoyat", color="#EF4444"),
    ]
    session.add_all(tags)
    session.flush()
    return tags


def _seed_quick_replies(session: Session) -> None:
    """Canned answers for the inbox composer."""
    session.add_all(
        [
            QuickReply(
                title="Salomlashuv",
                body_uz="Assalomu alaykum! MedLine Clinic. Sizga qanday yordam bera olaman?",
                body_ru="Здравствуйте! Клиника MedLine. Чем могу помочь?",
            ),
            QuickReply(
                title="Ish vaqti",
                body_uz="Biz dushanba–shanba 09:00 dan 19:00 gacha ishlaymiz.",
                body_ru="Мы работаем с понедельника по субботу с 09:00 до 19:00.",
            ),
            QuickReply(
                title="Manzil",
                body_uz="Markaziy filial: Amir Temur ko'chasi 12. Chilonzor: 9-kvartal.",
                body_ru="Центральный филиал: ул. Амира Темура 12. Чиланзар: 9-квартал.",
            ),
            QuickReply(
                title="Bron tasdig'i",
                body_uz="Bronigiz qabul qilindi. Kelishingizdan oldin eslatma yuboramiz.",
                body_ru="Ваша запись принята. Мы отправим напоминание перед визитом.",
            ),
        ]
    )
    session.flush()


def _seed_ai_profile(session: Session, company: Company) -> None:
    """The virtual sales operator profile."""
    session.add(
        AIProfile(
            company_id=company.id,
            agent_name="Aziza",
            is_enabled=True,
            autonomous=False,
            tone=ToneOfVoice.FRIENDLY,
            languages="uz,ru",
            work_start="09:00",
            work_end="19:00",
            max_auto_messages=6,
            escalate_after_unanswered=2,
            escalate_score_threshold=70,
            booking_required_fields="full_name,phone,datetime",
            forbidden_topics="tashxis,retsept,dori dozasi,huquqiy maslahat,moliyaviy maslahat",
            signature="MedLine Clinic",
        )
    )
    session.flush()


def _seed_knowledge(
    session: Session, company: Company, services: list[Service], branches: list[Branch]
) -> None:
    """Approved knowledge for the AI agent (clinic, courses and car showroom samples)."""
    today = now().date()
    items = [
        KnowledgeBaseItem(
            company_id=company.id,
            item_type=KBItemType.FAQ,
            category="Umumiy",
            title="Ish vaqti va manzil",
            title_ru="Время работы и адрес",
            body="Klinika dushanbadan shanbagacha 09:00–19:00 ishlaydi. "
            "Markaziy filial: Amir Temur 12, Chilonzor filiali: 9-kvartal.",
            body_ru="Клиника работает с понедельника по субботу 09:00–19:00. "
            "Центральный филиал: Амира Темура 12, филиал Чиланзар: 9-квартал.",
            keywords="ish vaqti,manzil,qayerda,adres,время,адрес,работаете",
            priority=3,
        ),
        KnowledgeBaseItem(
            company_id=company.id,
            item_type=KBItemType.PRICE,
            category="Narxlar",
            title="Dermatolog qabuli narxi",
            title_ru="Стоимость приёма дерматолога",
            body="Dermatolog qabuli 150 000 so'm. Ko'rik 30 daqiqa davom etadi.",
            body_ru="Приём дерматолога — 150 000 сум, длительность 30 минут.",
            keywords="dermatolog,narx,qancha,цена,дерматолог",
            service_id=services[0].id,
            price=150_000,
            priority=2,
        ),
        KnowledgeBaseItem(
            company_id=company.id,
            item_type=KBItemType.PROMO,
            category="Aksiya",
            title="Avgust aksiyasi: lazer epilyatsiyaga 20% chegirma",
            title_ru="Августовская акция: 20% на лазерную эпиляцию",
            body="Avgust oyi davomida lazer epilyatsiya paketlariga 20% chegirma amal qiladi.",
            body_ru="В августе действует скидка 20% на пакеты лазерной эпиляции.",
            keywords="aksiya,chegirma,lazer,скидка,акция,эпиляция",
            service_id=services[2].id,
            valid_from=today - timedelta(days=15),
            valid_to=today + timedelta(days=20),
            priority=4,
        ),
        KnowledgeBaseItem(
            company_id=company.id,
            item_type=KBItemType.POLICY,
            category="Qoidalar",
            title="Bekor qilish qoidasi",
            title_ru="Правила отмены",
            body="Bronni tashrifdan 3 soat oldin bekor qilish mumkin. "
            "Kechiktirilgan bekor qilishda navbat boshqa mijozga beriladi.",
            body_ru="Запись можно отменить не позднее чем за 3 часа до визита.",
            keywords="bekor,qaytarish,отмена,перенос",
            priority=1,
        ),
        KnowledgeBaseItem(
            company_id=company.id,
            item_type=KBItemType.INSTRUCTION,
            category="AI ko'rsatmasi",
            title="Tibbiy maslahat berilmaydi",
            title_ru="Медицинские консультации не даются",
            body="AI hech qachon tashxis qo'ymaydi va dori tavsiya qilmaydi — "
            "bunday savollar shifokorga yo'naltiriladi.",
            body_ru="AI не ставит диагноз и не назначает лечение — такие вопросы передаются врачу.",
            keywords="tashxis,dori,diagnoz,лечение,диагноз",
            priority=5,
        ),
        # Cross-industry samples requested by the specification
        KnowledgeBaseItem(
            company_id=company.id,
            item_type=KBItemType.SERVICE,
            category="Namuna: o'quv markazi",
            title="O'quv markazi — sinov darsi",
            title_ru="Учебный центр — пробный урок",
            body="Sinov darsi bepul, 45 daqiqa. Guruhlar 8-10 kishilik.",
            body_ru="Пробный урок бесплатный, 45 минут. Группы по 8–10 человек.",
            keywords="sinov dars,kurs,o'quv,пробный урок,курсы",
            ai_usable=False,
        ),
        KnowledgeBaseItem(
            company_id=company.id,
            item_type=KBItemType.SERVICE,
            category="Namuna: avtosalon",
            title="Avtosalon — test-drive",
            title_ru="Автосалон — тест-драйв",
            body="Test-drive uchun haydovchilik guvohnomasi kerak, davomiyligi 30 daqiqa.",
            body_ru="Для тест-драйва нужны водительские права, длительность 30 минут.",
            keywords="test drive,avtosalon,mashina,тест-драйв,автосалон",
            ai_usable=False,
        ),
    ]
    session.add_all(items)
    session.flush()


def _seed_schedule(session: Session, branches: list[Branch]) -> None:
    """Working-hours templates for both branches."""
    for branch in branches:
        for weekday in range(1, 7):
            session.add(
                ScheduleSlot(
                    branch_id=branch.id,
                    weekday=weekday,
                    start_time=branch.work_start,
                    end_time=branch.work_end,
                    slot_minutes=30,
                )
            )
    session.flush()


def _seed_leads(
    session: Session,
    company: Company,
    services: list[Service],
    branches: list[Branch],
    users: dict[str, User],
    sources: list[MarketingSource],
    campaigns: list[MarketingCampaign],
    tags: list[Tag],
) -> list[Lead]:
    """The six demo leads described by the specification."""
    reference = now()
    specs = [
        {
            "full_name": "Nodira Karimova",
            "phone": "+998901234567",
            "telegram_username": "nodira_k",
            "language": "uz",
            "channel": Channel.TELEGRAM,
            "status": LeadStatus.WAITING_OPERATOR,
            "score": 80,
            "intent": IntentLevel.HOT,
            "service": services[0],
            "owner": users["dilnoza"],
            "source": sources[0],
            "campaign": campaigns[0],
            "interest": "Dermatolog qabuli",
            "created": reference - timedelta(hours=3),
        },
        {
            "full_name": "Ольга Петрова",
            "phone": "+998935554433",
            "language": "ru",
            "channel": Channel.WHATSAPP,
            "status": LeadStatus.AI_CONVERSATION,
            "score": 45,
            "intent": IntentLevel.WARM,
            "service": services[2],
            "owner": users["jamshid"],
            "source": sources[1],
            "campaign": campaigns[1],
            "interest": "Лазерная эпиляция — цена",
            "created": reference - timedelta(hours=8),
        },
        {
            "full_name": "Sevara Tosheva",
            "telegram_username": "sevara_t",
            "language": "uz",
            "channel": Channel.INSTAGRAM,
            "status": LeadStatus.NEW,
            "score": 20,
            "intent": IntentLevel.COLD,
            "service": services[3],
            "owner": None,
            "source": sources[3],
            "campaign": campaigns[3],
            "interest": "UZI",
            "created": reference - timedelta(minutes=25),
        },
        {
            "full_name": "Jasur Ergashev",
            "phone": "+998977778899",
            "language": "uz",
            "channel": Channel.WEBSITE,
            "status": LeadStatus.BOOKED,
            "score": 85,
            "intent": IntentLevel.HOT,
            "service": services[1],
            "owner": users["dilnoza"],
            "source": sources[2],
            "campaign": campaigns[2],
            "interest": "Stomatologiya",
            "created": reference - timedelta(days=1, hours=2),
        },
        {
            "full_name": "Игорь Ким",
            "phone": "+998901112233",
            "language": "ru",
            "channel": Channel.PHONE,
            "status": LeadStatus.CALLBACK,
            "score": 35,
            "intent": IntentLevel.COLD,
            "service": services[2],
            "owner": users["jamshid"],
            "source": sources[1],
            "campaign": campaigns[1],
            "interest": "Лазерная эпиляция",
            "created": reference - timedelta(days=2),
        },
        {
            "full_name": "Bekzod Rasulov",
            "phone": "+998933334455",
            "language": "uz",
            "channel": Channel.TELEGRAM,
            "status": LeadStatus.LOST,
            "score": 10,
            "intent": IntentLevel.COLD,
            "service": services[2],
            "owner": users["dilnoza"],
            "source": sources[0],
            "campaign": campaigns[0],
            "interest": "Lazer epilyatsiya",
            "created": reference - timedelta(days=5),
            "loss_reason": LossReason.PRICE,
            "loss_comment": "Narx qimmat deb hisobladi, raqobatchiga ketdi.",
        },
        {
            "full_name": "Malika Yo'ldosheva",
            "phone": "+998909998877",
            "language": "uz",
            "channel": Channel.INSTAGRAM,
            "status": LeadStatus.WON,
            "score": 95,
            "intent": IntentLevel.HOT,
            "service": services[1],
            "owner": users["dilnoza"],
            "source": sources[0],
            "campaign": campaigns[0],
            "interest": "Stomatologiya",
            "created": reference - timedelta(days=7),
            "revenue": 850_000,
        },
    ]

    leads: list[Lead] = []
    for index, spec in enumerate(specs):
        lead = Lead(
            company_id=company.id,
            full_name=spec["full_name"],
            phone=spec.get("phone"),
            telegram_username=spec.get("telegram_username", ""),
            language=spec["language"],
            channel=spec["channel"],
            status=spec["status"],
            score=spec["score"],
            intent=spec["intent"],
            service_id=spec["service"].id,
            branch_id=branches[index % len(branches)].id,
            owner_id=spec["owner"].id if spec["owner"] else None,
            source_id=spec["source"].id,
            campaign_id=spec["campaign"].id,
            utm_source=spec["source"].utm_source,
            utm_medium=spec["campaign"].utm_medium,
            utm_campaign=spec["campaign"].utm_campaign,
            interest=spec["interest"],
            created_at=spec["created"],
            updated_at=spec["created"],
            last_activity_at=spec["created"],
            last_inbound_at=spec["created"],
            first_response_seconds=90 if spec["owner"] else None,
            external_id=f"demo-chat-{1000 + index}",
            loss_reason=spec.get("loss_reason", ""),
            loss_comment=spec.get("loss_comment", ""),
            lost_at=spec["created"] + timedelta(days=1) if spec.get("loss_reason") else None,
            revenue=float(spec.get("revenue", 0)),
            won_at=spec["created"] + timedelta(days=2) if spec.get("revenue") else None,
            ai_state=AIState.QUALIFICATION,
        )
        session.add(lead)
        session.flush()
        leads.append(lead)

        session.add(
            LeadActivity(
                lead_id=lead.id,
                kind="lead_created",
                title="Lead yaratildi",
                detail=f"channel={lead.channel}",
                created_at=lead.created_at,
            )
        )
        if spec.get("revenue"):
            session.add(
                RevenueRecord(
                    lead_id=lead.id,
                    service_id=lead.service_id,
                    branch_id=lead.branch_id,
                    campaign_id=lead.campaign_id,
                    amount=float(spec["revenue"]),
                    sale_date=(lead.won_at or now()).date(),
                    comment="Demo sotuv",
                )
            )

    leads[0].tags.append(tags[0])
    leads[1].tags.append(tags[2])
    leads[5].tags.append(tags[2])
    session.flush()
    return leads


def _seed_conversations(session: Session, leads: list[Lead], users: dict[str, User]) -> None:
    """Four scripted dialogues covering the required scenarios."""
    scripts: list[tuple[Lead, str, list[tuple[str, str, bool]]]] = [
        (
            leads[3],
            ConversationStatus.OPERATOR_HANDLING,
            [
                ("customer", "Assalomu alaykum, stomatologga yozilmoqchi edim.", False),
                (
                    "ai",
                    "Assalomu alaykum! MedLine Clinic ga xush kelibsiz. Men Azizaman. "
                    "Stomatologiya bo'yicha ertaga soat 15:00 bo'sh vaqtimiz bor.",
                    False,
                ),
                ("customer", "Menga to'g'ri keladi. Ismim Jasur, +998977778899", False),
                (
                    "ai",
                    "Ajoyib! Ertaga 15:00 ga bron qildim. Tasdiqlash xabarini yubordim.",
                    False,
                ),
                ("operator", "Bron tasdiqlandi, mijoz kelishini aytdi.", True),
            ],
        ),
        (
            leads[0],
            ConversationStatus.WAITING_OPERATOR,
            [
                ("customer", "Salom, dermatolog qabuliga yozilmoqchiman.", False),
                (
                    "ai",
                    "Assalomu alaykum! Dermatolog qabuli — 150 000 so'm, 30 daqiqa. "
                    "Sizga qulay vaqtni belgilaymizmi?",
                    False,
                ),
                ("customer", "Menda allergiya bor, qanday dori ichishim kerak?", False),
                (
                    "ai",
                    "Bu savol bo'yicha maslahatni faqat shifokorimiz bera oladi. "
                    "Sizni operatorga ulayman.",
                    False,
                ),
                ("operator", "Tibbiy savol — shifokorga yo'naltirish kerak.", True),
            ],
        ),
        (
            leads[1],
            ConversationStatus.AI_HANDLING,
            [
                ("customer", "Здравствуйте, сколько стоит лазерная эпиляция?", False),
                (
                    "ai",
                    "Здравствуйте! Лазерная эпиляция — от 350 000 сум. "
                    "В августе действует скидка 20%. Подберём удобное время?",
                    False,
                ),
                ("customer", "Дороговато, есть ещё скидки?", False),
                (
                    "ai",
                    "Понимаю вас. У нас есть действующие предложения — "
                    "оператор подберёт оптимальный вариант, сейчас передам ему диалог.",
                    False,
                ),
            ],
        ),
        (
            leads[5],
            ConversationStatus.CLOSED,
            [
                ("customer", "Lazer epilyatsiya narxi qancha?", False),
                ("ai", "Lazer epilyatsiya — 350 000 so'mdan boshlanadi.", False),
                ("customer", "Juda qimmat ekan, menga boshqa yozmang.", False),
                (
                    "ai",
                    "Tushundim, boshqa xabar yubormaymiz. Murojaatingiz uchun rahmat.",
                    False,
                ),
            ],
        ),
    ]

    for lead, status, turns in scripts:
        conversation = Conversation(
            lead_id=lead.id,
            channel=lead.channel,
            external_chat_id=lead.external_id,
            status=status,
            ai_enabled=status in (ConversationStatus.AI_HANDLING, ConversationStatus.OPEN),
            ai_state=AIState.QUALIFICATION,
            assigned_to_id=lead.owner_id,
            unread_count=1 if status == ConversationStatus.WAITING_OPERATOR else 0,
            escalated_at=now() if status == ConversationStatus.WAITING_OPERATOR else None,
            escalation_reason=(
                "Taqiqlangan mavzu" if status == ConversationStatus.WAITING_OPERATOR else ""
            ),
        )
        session.add(conversation)
        session.flush()

        timestamp = lead.created_at
        for role, text, internal in turns:
            timestamp = timestamp + timedelta(minutes=4)
            sender = {
                "customer": MessageSender.CUSTOMER,
                "ai": MessageSender.AI,
                "operator": MessageSender.OPERATOR,
            }[role]
            direction = (
                MessageDirection.INBOUND
                if role == "customer"
                else (MessageDirection.INTERNAL if internal else MessageDirection.OUTBOUND)
            )
            session.add(
                Message(
                    conversation_id=conversation.id,
                    lead_id=lead.id,
                    direction=direction,
                    sender=sender,
                    sender_user_id=lead.owner_id if role == "operator" else None,
                    channel=lead.channel,
                    body=text,
                    language=lead.language,
                    status=MessageStatus.DELIVERED,
                    is_internal=internal,
                    is_read=status != ConversationStatus.WAITING_OPERATOR,
                    created_at=timestamp,
                )
            )
            if role == "ai":
                session.add(
                    AIInteraction(
                        lead_id=lead.id,
                        conversation_id=conversation.id,
                        provider="demo_llm",
                        model="rule-based-v1",
                        state_before=AIState.NEED_DISCOVERY,
                        state_after=AIState.QUALIFICATION,
                        customer_message="",
                        suggested_reply=text,
                        final_reply=text,
                        language=lead.language,
                        status=AIInteractionStatus.SENT,
                        escalated="operatorga ulayman" in text.lower() or "передам" in text.lower(),
                        escalation_reason=(
                            "Eskalatsiya qoidasi" if "operatorga" in text.lower() else ""
                        ),
                        latency_ms=12,
                        created_at=timestamp,
                    )
                )
        conversation.last_message_at = timestamp
        conversation.last_message_preview = turns[-1][1][:120]
    session.flush()

    # The opt-out lead must be marked as Do Not Contact
    leads[5].do_not_contact = True
    leads[5].opt_out_at = now()
    session.flush()


def _seed_bookings(
    session: Session,
    leads: list[Lead],
    services: list[Service],
    branches: list[Branch],
    users: dict[str, User],
) -> None:
    """Two upcoming bookings plus one completed and one no-show."""
    reference = now().replace(minute=0, second=0, microsecond=0)
    entries = [
        (
            leads[3],
            services[1],
            reference + timedelta(days=1, hours=6),
            BookingStatus.CONFIRMED,
            True,
        ),
        (
            leads[0],
            services[0],
            reference + timedelta(days=2, hours=3),
            BookingStatus.PENDING,
            False,
        ),
        (leads[6], services[1], reference - timedelta(days=5), BookingStatus.COMPLETED, False),
        (leads[4], services[2], reference - timedelta(days=2), BookingStatus.NO_SHOW, False),
    ]
    for lead, service, starts_at, status, by_ai in entries:
        session.add(
            Booking(
                lead_id=lead.id,
                service_id=service.id,
                branch_id=lead.branch_id or branches[0].id,
                specialist_id=lead.owner_id or users["dilnoza"].id,
                purpose=BookingPurpose.CLINIC_APPOINTMENT,
                starts_at=starts_at,
                ends_at=starts_at + timedelta(minutes=service.duration_minutes),
                duration_minutes=service.duration_minutes,
                status=status,
                created_channel="ai" if by_ai else "manual",
                created_by_ai=by_ai,
                confirmation_sent_at=now() if status != BookingStatus.PENDING else None,
                confirmed_at=now() if status == BookingStatus.CONFIRMED else None,
                note="Demo bron",
            )
        )
    session.flush()


def _seed_calls(session: Session, leads: list[Lead], users: dict[str, User]) -> None:
    """Two analysed calls: one callback and one negative."""
    entries = [
        (
            leads[4],
            users["jamshid"],
            CallOutcome.CALLBACK,
            220,
            "Оператор: Здравствуйте, клиника MedLine. Клиент: Сколько стоит лазерная эпиляция? "
            "Оператор: От 350 тысяч сум. Клиент: Сейчас занят, перезвоните позже.",
            Sentiment.NEUTRAL,
            60,
        ),
        (
            leads[5],
            users["dilnoza"],
            CallOutcome.REFUSED,
            95,
            "Operator: Assalomu alaykum. Mijoz: Menga boshqa qo'ng'iroq qilmang, "
            "narxlaringiz juda qimmat va xizmatdan norozi qoldim.",
            Sentiment.NEGATIVE,
            25,
        ),
    ]
    for lead, operator, outcome, duration, transcript_text, sentiment, quality in entries:
        started = now() - timedelta(days=1, hours=4)
        call = Call(
            lead_id=lead.id,
            operator_id=operator.id,
            direction=CallDirection.OUTBOUND,
            phone=lead.phone or "",
            provider="demo_telephony",
            started_at=started,
            ended_at=started + timedelta(seconds=duration),
            duration_seconds=duration,
            outcome=outcome,
            note="Demo qo'ng'iroq",
        )
        session.add(call)
        session.flush()
        session.add(
            CallTranscript(
                call_id=call.id,
                provider="demo_stt",
                language=lead.language,
                text=transcript_text,
                confidence=0.94,
            )
        )
        session.add(
            CallAnalysis(
                call_id=call.id,
                summary=transcript_text[:160],
                customer_need="price" if outcome == CallOutcome.CALLBACK else "shikoyat",
                objections="Narx qimmat" if sentiment == Sentiment.NEGATIVE else "—",
                operator_mistakes="Bron taklif qilinmadi",
                next_best_action=(
                    "Qayta qo'ng'iroq qilish"
                    if outcome == CallOutcome.CALLBACK
                    else "Rahbar aralashuvi"
                ),
                sentiment=sentiment,
                quality_score=quality,
                got_phone=True,
                got_purpose=True,
                got_booking=False,
                alert_raised=sentiment == Sentiment.NEGATIVE,
            )
        )
    session.flush()


def _seed_tasks(session: Session, leads: list[Lead], users: dict[str, User]) -> None:
    """Follow-up tasks in different states."""
    session.add_all(
        [
            Task(
                lead_id=leads[0].id,
                assignee_id=users["dilnoza"].id,
                task_type=TaskType.WRITE_BACK,
                title="Javobsiz lead: Nodira Karimova",
                description="Tibbiy savol bo'yicha shifokor javobini yetkazish.",
                due_at=now() + timedelta(hours=1),
                priority=TaskPriority.HIGH,
                status=TaskStatus.OPEN,
                auto_rule="first_response_sla",
            ),
            Task(
                lead_id=leads[4].id,
                assignee_id=users["jamshid"].id,
                task_type=TaskType.CALL_BACK,
                title="Qayta qo'ng'iroq: Игорь Ким",
                due_at=now() - timedelta(hours=3),
                priority=TaskPriority.NORMAL,
                status=TaskStatus.OVERDUE,
                auto_rule="call_callback",
            ),
            Task(
                lead_id=leads[3].id,
                assignee_id=users["dilnoza"].id,
                task_type=TaskType.CONFIRM_BOOKING,
                title="Bronni tasdiqlash: Jasur Ergashev",
                due_at=now() + timedelta(hours=18),
                priority=TaskPriority.NORMAL,
                status=TaskStatus.DONE,
                completed_at=now() - timedelta(hours=2),
                result_comment="Mijoz tasdiqladi.",
            ),
        ]
    )
    session.flush()


def _seed_notifications(session: Session, leads: list[Lead], users: dict[str, User]) -> None:
    """A few notification centre entries."""
    session.add_all(
        [
            Notification(
                user_id=users["dilnoza"].id,
                lead_id=leads[0].id,
                level=NotificationLevel.WARNING,
                title="Issiq lead javobsiz",
                body="Nodira Karimova — skor 80, javob kutmoqda.",
                category="hot_lead",
                created_at=now() - timedelta(minutes=12),
            ),
            Notification(
                lead_id=leads[5].id,
                level=NotificationLevel.CRITICAL,
                title="Salbiy qo'ng'iroq",
                body="Bekzod Rasulov shikoyat bilan yakunladi.",
                category="call_alert",
                created_at=now() - timedelta(hours=6),
            ),
            Notification(
                user_id=users["dilnoza"].id,
                lead_id=leads[3].id,
                level=NotificationLevel.SUCCESS,
                title="Yangi bron",
                body="Jasur Ergashev — ertaga 15:00",
                category="booking",
                is_read=True,
                created_at=now() - timedelta(days=1),
            ),
        ]
    )
    session.flush()
