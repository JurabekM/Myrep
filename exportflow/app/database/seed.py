"""Reference data and demo dataset seeding.

``seed_reference_data`` is always executed (roles, permissions, categories,
templates). ``seed_demo_data`` runs only on a fresh database so the application
is immediately usable in Demo mode.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.engine import session_scope
from app.models import (
    RFQ,
    Buyer,
    BuyerContact,
    Catalog,
    CatalogItem,
    Certificate,
    ChecklistTemplate,
    ChecklistTemplateItem,
    Company,
    Contract,
    EmailTemplate,
    Lead,
    MarketingSource,
    Permission,
    Product,
    ProductCategory,
    ProductPrice,
    ProductSpecification,
    Quotation,
    QuotationItem,
    RFQItem,
    Role,
    SalesAgent,
    Shipment,
    ShipmentItem,
    User,
)
from app.services import integration_service
from app.services.permissions import PERMISSIONS, ROLE_NAMES, permissions_for_role
from app.utils.enums import ALL_ROLES, ROLE_ADMIN
from app.utils.formatting import now, today
from app.utils.logging_setup import get_logger
from app.utils.security import hash_password

log = get_logger(__name__)

DEMO_ADMIN_USERNAME = "admin"
DEMO_ADMIN_PASSWORD = "admin123"


# --------------------------------------------------------------- reference
def seed_permissions_and_roles(session: Session) -> None:
    """Create every permission and system role, keeping them in sync."""
    existing = {row.code: row for row in session.scalars(select(Permission)).all()}
    for code, (module, description) in PERMISSIONS.items():
        if code in existing:
            continue
        session.add(Permission(code=code, module=module, description=description))
    session.flush()
    all_permissions = {row.code: row for row in session.scalars(select(Permission)).all()}

    for role_code in ALL_ROLES:
        role = session.scalar(select(Role).where(Role.code == role_code))
        if role is None:
            role = Role(code=role_code, name=ROLE_NAMES[role_code], is_system=True)
            session.add(role)
            session.flush()
        role.name = ROLE_NAMES[role_code]
        wanted = set(permissions_for_role(role_code))
        role.permissions = [all_permissions[code] for code in wanted if code in all_permissions]
    session.flush()


def seed_checklist_templates(session: Session) -> None:
    """Create the standard export readiness checklist templates."""
    definitions = [
        (
            "product_export_readiness",
            "Product export readiness",
            "product",
            None,
            [
                ("product_readiness", "Product specification confirmed", 3, "high"),
                ("product_readiness", "HS code verified", 3, "high"),
                ("certificates", "Required certificates identified", 5, "high"),
                ("packaging", "Export packaging defined", 5, "normal"),
                ("packaging", "Carton and pallet data recorded", 7, "normal"),
                ("pricing", "EXW / FOB cost calculated", 7, "high"),
                (
                    "product_readiness",
                    "Product label matches target market requirements",
                    10,
                    "high",
                ),
            ],
        ),
        (
            "rfq_response",
            "RFQ response readiness",
            "lead",
            "rfq_received",
            [
                ("pricing", "Valid approved price available", 1, "critical"),
                ("incoterms", "Incoterm agreed with the buyer", 2, "high"),
                ("logistics", "Loading port defined", 2, "high"),
                ("logistics", "Transport quote requested", 3, "normal"),
                ("certificates", "Certificate requirements checked", 2, "high"),
                ("packaging", "MOQ agreed with the buyer", 3, "normal"),
            ],
        ),
        (
            "quotation_sent",
            "After quotation sent",
            "lead",
            "quotation_sent",
            [
                ("payment_terms", "Payment terms confirmed", 3, "high"),
                ("sample", "Sample requirement clarified", 5, "normal"),
                ("logistics", "Freight cost validated", 5, "normal"),
            ],
        ),
        (
            "contract_preparation",
            "Contract preparation",
            "lead",
            "contract_preparation",
            [
                ("contract", "Draft contract prepared", 3, "critical"),
                ("payment_terms", "Payment terms confirmed in writing", 3, "critical"),
                ("customs_documents", "Certificate of Origin process checked", 5, "high"),
                ("customs_documents", "Commercial invoice template ready", 5, "normal"),
                ("customs_documents", "Packing list template ready", 5, "normal"),
                ("contract", "Contract signed by both parties", 10, "critical"),
            ],
        ),
        (
            "shipment_preparation",
            "Shipment preparation",
            "lead",
            "contract_signed",
            [
                ("shipment", "Booking requested with the forwarder", 3, "high"),
                ("customs_documents", "Customs declaration submitted", 5, "high"),
                (
                    "certificates",
                    "Phytosanitary / veterinary certificate obtained if required",
                    5,
                    "high",
                ),
                ("shipment", "Container loading plan approved", 6, "normal"),
                ("logistics", "Tracking reference shared with the buyer", 8, "normal"),
            ],
        ),
    ]
    for code, name, scope, trigger, items in definitions:
        template = session.scalar(select(ChecklistTemplate).where(ChecklistTemplate.code == code))
        if template is not None:
            continue
        template = ChecklistTemplate(
            code=code, name=name, scope=scope, trigger_status=trigger, description=name
        )
        session.add(template)
        session.flush()
        for order, (category, title, offset, priority) in enumerate(items):
            session.add(
                ChecklistTemplateItem(
                    template_id=template.id,
                    category=category,
                    title=title,
                    priority=priority,
                    due_offset_days=offset,
                    sort_order=order,
                )
            )
    session.flush()


def seed_email_templates(session: Session) -> None:
    """Create the default multilingual email templates."""
    templates = [
        (
            "first_contact_en",
            "First contact (EN)",
            "en",
            "first_contact",
            "{company} — export supplier enquiry",
            "Dear {contact},\n\nWe are {company}, a manufacturer based in Uzbekistan. "
            "We would be glad to introduce our products to {buyer}.\n\n"
            "Please let us know which items and volumes are of interest and we will "
            "prepare a detailed quotation.\n\nBest regards,\n{sender}\n{company}\n"
            "{company_phone} | {company_email}",
        ),
        (
            "quotation_cover_en",
            "Quotation cover letter (EN)",
            "en",
            "quotation",
            "Quotation {quotation_number} — {company}",
            "Dear {contact},\n\nPlease find attached our quotation {quotation_number} "
            "for a total of {quotation_total}, valid until {valid_until}.\n\n"
            "We remain at your disposal for any clarification.\n\n"
            "Best regards,\n{sender}\n{company}",
        ),
        (
            "follow_up_en",
            "Follow-up (EN)",
            "en",
            "follow_up",
            "Following up — quotation {quotation_number}",
            "Dear {contact},\n\nI am following up on quotation {quotation_number} sent earlier. "
            "Could you share your feedback on the commercial terms?\n\n"
            "Best regards,\n{sender}\n{company}",
        ),
        (
            "first_contact_ru",
            "Первое обращение (RU)",
            "ru",
            "first_contact",
            "{company} — предложение о сотрудничестве",
            "Уважаемый(ая) {contact},\n\nМы — компания {company}, производитель из Узбекистана. "
            "Будем рады представить нашу продукцию компании {buyer}.\n\n"
            "Сообщите, какие позиции и объёмы вас интересуют, и мы подготовим "
            "детальное предложение.\n\nС уважением,\n{sender}\n{company}\n"
            "{company_phone} | {company_email}",
        ),
        (
            "first_contact_uz",
            "Birinchi murojaat (UZ)",
            "uz",
            "first_contact",
            "{company} — hamkorlik taklifi",
            "Hurmatli {contact},\n\nBiz {company} kompaniyasimiz, O‘zbekistondagi ishlab chiqaruvchi. "
            "{buyer} kompaniyasiga mahsulotlarimizni taqdim etishdan mamnun bo‘lamiz.\n\n"
            "Qaysi pozitsiyalar va hajmlar qiziqtirishini bildiring — batafsil taklif tayyorlaymiz.\n\n"
            "Hurmat bilan,\n{sender}\n{company}",
        ),
    ]
    for code, name, language, purpose, subject, body in templates:
        if session.scalar(select(EmailTemplate).where(EmailTemplate.code == code)):
            continue
        session.add(
            EmailTemplate(
                code=code,
                name=name,
                language=language,
                purpose=purpose,
                subject=subject,
                body=body,
            )
        )
    session.flush()


def seed_marketing_sources(session: Session) -> None:
    """Create the standard marketing channels."""
    for code, name in (
        ("alibaba", "Alibaba"),
        ("linkedin", "LinkedIn"),
        ("email", "Email campaign"),
        ("website_inquiry", "Website inquiry"),
        ("trade_fair", "Trade fair"),
        ("sales_agent", "Sales agent"),
        ("referral", "Referral"),
        ("manual", "Manual entry"),
        ("other", "Other"),
    ):
        if session.scalar(select(MarketingSource).where(MarketingSource.code == code)):
            continue
        session.add(MarketingSource(code=code, name=name))
    session.flush()


def seed_categories(session: Session) -> None:
    """Create the default export product categories."""
    categories = [
        ("textile", "To‘qimachilik", "Текстиль", "Textile"),
        ("furniture", "Mebel", "Мебель", "Furniture"),
        ("dried_fruit", "Quritilgan mevalar", "Сухофрукты", "Dried fruits"),
        ("food", "Oziq-ovqat", "Продукты питания", "Food products"),
        ("cosmetics", "Kosmetika", "Косметика", "Cosmetics"),
        ("construction", "Qurilish materiallari", "Стройматериалы", "Construction materials"),
        ("ceramics", "Keramika", "Керамика", "Ceramics"),
    ]
    for code, uz, ru, en in categories:
        if session.scalar(select(ProductCategory).where(ProductCategory.code == code)):
            continue
        session.add(ProductCategory(code=code, name_uz=uz, name_ru=ru, name_en=en))
    session.flush()


def seed_reference_data(session: Session) -> None:
    """Seed everything the application needs regardless of demo data."""
    seed_permissions_and_roles(session)
    seed_categories(session)
    seed_checklist_templates(session)
    seed_email_templates(session)
    seed_marketing_sources(session)
    integration_service.ensure_defaults(session)


# -------------------------------------------------------------------- demo
def _demo_company(session: Session) -> Company:
    company = session.scalars(select(Company)).first()
    if company is None:
        company = Company(name="Samarkand Export Textile LLC")
        session.add(company)
    company.name = "Samarkand Export Textile LLC"
    company.legal_name = 'MChJ "Samarkand Export Textile"'
    company.address = "12 Registon street, Samarkand 140100, Uzbekistan"
    company.country = "Uzbekistan"
    company.city = "Samarkand"
    company.tax_id = "302145879"
    company.phone = "+998 66 233 45 67"
    company.email = "export@samarkand-textile.uz"
    company.website = "https://samarkand-textile.uz"
    company.export_contact_name = "Dilshod Rakhimov"
    company.export_contact_phone = "+998 90 123 45 67"
    company.export_contact_email = "d.rakhimov@samarkand-textile.uz"
    company.bank_name = "JSCB Uzpromstroybank, Samarkand branch"
    company.bank_account = "20208840100000012345"
    company.bank_swift = "UZPSUZ22XXX"
    company.default_currency = "USD"
    company.about_en = (
        "Samarkand Export Textile LLC is a vertically integrated manufacturer of cotton home "
        "textile and food products from Uzbekistan. We serve importers, distributors and retail "
        "chains across Europe, the Gulf region and Central Asia, supplying against agreed "
        "specifications with export-grade packaging."
    )
    company.about_ru = (
        "Samarkand Export Textile LLC — вертикально интегрированный производитель хлопкового "
        "домашнего текстиля и продуктов питания из Узбекистана. Мы работаем с импортёрами, "
        "дистрибьюторами и розничными сетями Европы, стран Залива и Центральной Азии."
    )
    company.about_uz = (
        "Samarkand Export Textile LLC — O‘zbekistondagi paxta uy tekstili va oziq-ovqat "
        "mahsulotlari ishlab chiqaruvchisi. Yevropa, Fors ko‘rfazi va Markaziy Osiyo "
        "bozorlaridagi importchilar bilan ishlaymiz."
    )
    session.flush()
    return company


def _demo_users(session: Session) -> dict[str, User]:
    roles = {role.code: role for role in session.scalars(select(Role)).unique().all()}
    definitions = [
        (DEMO_ADMIN_USERNAME, DEMO_ADMIN_PASSWORD, "System Administrator", ROLE_ADMIN, "uz"),
        ("dilshod", "demo12345", "Dilshod Rakhimov", "export_manager", "uz"),
        ("nigora", "demo12345", "Nigora Yusupova", "sales_manager", "ru"),
        ("bekzod", "demo12345", "Bekzod Tursunov", "logistics_specialist", "uz"),
        ("kamola", "demo12345", "Kamola Sadykova", "catalog_manager", "en"),
        ("viewer", "demo12345", "Read Only", "viewer", "en"),
    ]
    users: dict[str, User] = {}
    for username, password, full_name, role_code, language in definitions:
        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                password_hash=hash_password(password),
                full_name=full_name,
                role_id=roles[role_code].id,
                language=language,
                email=f"{username}@samarkand-textile.uz",
            )
            session.add(user)
        users[username] = user
    session.flush()
    return users


def _demo_products(session: Session, categories: dict[str, ProductCategory]) -> dict[str, Product]:
    definitions = [
        {
            "sku": "TX-TOW-500",
            "category": "textile",
            "name_en": "100% Cotton Bath Towel 70x140",
            "name_ru": "Банное полотенце 100% хлопок 70х140",
            "name_uz": "100% paxta hammom sochiq 70x140",
            "short_desc_en": "Ring-spun cotton bath towel, 500 gsm, OEKO-TEX compliant yarn.",
            "short_desc_ru": "Банное полотенце из кольцевой пряжи, 500 г/м².",
            "short_desc_uz": "Halqa yigirilgan paxtadan hammom sochig‘i, 500 g/m².",
            "full_desc_en": (
                "Bath towel produced from long-staple Uzbek cotton, 500 gsm, double-stitched hem, "
                "high absorbency after the first wash. Available in 12 standard colours, custom "
                "sizes and jacquard borders on request. Packed in individual polybags."
            ),
            "hs_code": "6302600000",
            "moq": 3000,
            "unit": "pcs",
            "capacity_month": 120000,
            "capacity_year": 1400000,
            "lead_time_days": 30,
            "net_weight": 0.49,
            "gross_weight": 0.55,
            "packaging_type": "Individual polybag, 20 pcs per carton",
            "units_per_carton": 20,
            "cartons_per_pallet": 40,
            "carton_dimensions": "60x40x40 cm",
            "brand": "SamCotton",
            "tags": "towel,cotton,home textile,hotel",
            "status": "active",
            "specs": [
                ("Material", "100% cotton", "100% хлопок", "100% paxta"),
                ("Density", "500 gsm", "500 г/м²", "500 g/m²"),
                ("Size", "70x140 cm", "70х140 см", "70x140 sm"),
                ("Colours", "12 standard", "12 стандартных", "12 standart"),
            ],
        },
        {
            "sku": "TX-BED-220",
            "category": "textile",
            "name_en": "Hotel Bed Linen Set (Sateen 220 TC)",
            "name_ru": "Комплект гостиничного постельного белья (сатин 220 TC)",
            "name_uz": "Mehmonxona choyshab to‘plami (saten 220 TC)",
            "short_desc_en": "Sateen weave hotel bed linen set, 220 thread count, white.",
            "short_desc_ru": "Комплект постельного белья сатин, 220 нитей, белый.",
            "short_desc_uz": "Saten to‘qimali mehmonxona choyshab to‘plami, 220 ip.",
            "full_desc_en": (
                "Hotel-grade bed linen set including flat sheet, fitted sheet, duvet cover and two "
                "pillowcases. Sateen weave, 220 thread count, industrial laundry resistant, "
                "shrinkage below 3% after 50 wash cycles."
            ),
            "hs_code": "6302219000",
            "moq": 500,
            "unit": "set",
            "capacity_month": 25000,
            "lead_time_days": 35,
            "net_weight": 2.1,
            "gross_weight": 2.35,
            "packaging_type": "PVC bag, 6 sets per carton",
            "units_per_carton": 6,
            "cartons_per_pallet": 30,
            "brand": "SamCotton Hotel",
            "tags": "bed linen,hotel,sateen",
            "status": "active",
            "specs": [
                ("Composition", "100% cotton sateen", "100% хлопковый сатин", "100% paxta saten"),
                ("Thread count", "220 TC", "220 TC", "220 TC"),
                ("Set", "4 pieces", "4 предмета", "4 buyum"),
            ],
        },
        {
            "sku": "FD-APR-ORG",
            "category": "dried_fruit",
            "name_en": "Organic Dried Apricots (Sun-dried, unsulphured)",
            "name_ru": "Органическая курага (солнечная сушка, без серы)",
            "name_uz": "Organik quritilgan o‘rik (quyoshda quritilgan, oltingugurtsiz)",
            "short_desc_en": "Sun-dried unsulphured apricots from the Fergana valley.",
            "short_desc_ru": "Курага солнечной сушки из Ферганской долины, без серы.",
            "short_desc_uz": "Farg‘ona vodiysidan quyoshda quritilgan oltingugurtsiz o‘rik.",
            "full_desc_en": (
                "Whole pitted apricots, sun-dried without sulphur dioxide, moisture 18-20%, "
                "calibrated in three sizes. Suitable for retail packing and industrial use. "
                "Delivered in food-grade cartons with inner liner."
            ),
            "hs_code": "0813100000",
            "moq": 5000,
            "unit": "kg",
            "capacity_month": 90000,
            "lead_time_days": 21,
            "net_weight": 1.0,
            "gross_weight": 1.06,
            "packaging_type": "10 kg carton with food-grade liner",
            "units_per_carton": 10,
            "cartons_per_pallet": 60,
            "shelf_life": "12 months",
            "storage_condition": "Store at +5..+20 °C, relative humidity below 65%",
            "brand": "Fergana Sun",
            "tags": "dried fruit,apricot,organic,food",
            "status": "active",
            "specs": [
                ("Moisture", "18-20%", "18-20%", "18-20%"),
                (
                    "Calibration",
                    "60/80, 80/100, 100/120",
                    "60/80, 80/100, 100/120",
                    "60/80, 80/100, 100/120",
                ),
                ("Treatment", "Unsulphured", "Без серы", "Oltingugurtsiz"),
            ],
        },
        {
            "sku": "CR-TBL-24",
            "category": "ceramics",
            "name_en": "Decorative Ceramic Tableware Set (24 pcs)",
            "name_ru": "Декоративный керамический столовый сервиз (24 предмета)",
            "name_uz": "Dekorativ keramika dasturxon to‘plami (24 dona)",
            "short_desc_en": "Hand-painted Rishtan-style ceramic tableware, 24-piece set.",
            "short_desc_ru": "Расписной риштанский керамический сервиз, 24 предмета.",
            "short_desc_uz": "Qo‘lda bo‘yalgan Rishton uslubidagi keramika to‘plami, 24 dona.",
            "full_desc_en": (
                "Traditional hand-painted ceramic tableware set combining six plates, six bowls, "
                "six saucers and six cups. Lead-free glaze, dishwasher safe, packed with foam "
                "inserts for export transportation."
            ),
            "hs_code": "6912002300",
            "moq": 200,
            "unit": "set",
            "capacity_month": 4000,
            "lead_time_days": 45,
            "net_weight": 6.4,
            "gross_weight": 7.8,
            "packaging_type": "Foam insert box, 2 sets per carton",
            "units_per_carton": 2,
            "cartons_per_pallet": 24,
            "brand": "Rishton Art",
            "tags": "ceramics,tableware,handmade",
            "status": "active",
            "specs": [
                ("Pieces", "24", "24", "24"),
                ("Glaze", "Lead-free", "Без свинца", "Qo‘rg‘oshinsiz"),
                ("Decoration", "Hand-painted", "Ручная роспись", "Qo‘lda bo‘yalgan"),
            ],
        },
    ]

    products: dict[str, Product] = {}
    for definition in definitions:
        sku = definition["sku"]
        product = session.scalar(select(Product).where(Product.sku == sku))
        if product is not None:
            products[sku] = product
            continue
        specs = definition.pop("specs")
        category_code = definition.pop("category")
        product = Product(
            **definition,
            category_id=categories[category_code].id,
            origin_country="Uzbekistan",
            manufacturer="Samarkand Export Textile LLC",
            export_ready=True,
        )
        session.add(product)
        session.flush()
        for order, (name_en, value_en, value_ru, value_uz) in enumerate(specs):
            session.add(
                ProductSpecification(
                    product_id=product.id,
                    name_en=name_en,
                    name_ru=name_en,
                    name_uz=name_en,
                    value_en=value_en,
                    value_ru=value_ru,
                    value_uz=value_uz,
                    sort_order=order,
                )
            )
        products[sku] = product
    session.flush()
    return products


def _demo_prices(session: Session, products: dict[str, Product]) -> None:
    definitions = [
        ("TX-TOW-500", "EXW", "USD", "Samarkand factory", 2.35, 3000, 30),
        ("TX-TOW-500", "FOB", "USD", "Tashkent (rail terminal)", 2.62, 3000, 30),
        ("TX-TOW-500", "CIF", "USD", "Jebel Ali", 2.95, 5000, 35),
        ("TX-BED-220", "FOB", "USD", "Tashkent (rail terminal)", 18.40, 500, 35),
        ("TX-BED-220", "DAP", "EUR", "Hamburg", 21.80, 500, 45),
        ("FD-APR-ORG", "FCA", "USD", "Samarkand warehouse", 3.10, 5000, 21),
        ("FD-APR-ORG", "CIF", "USD", "Jebel Ali", 3.55, 10000, 28),
        ("CR-TBL-24", "EXW", "USD", "Rishtan workshop", 46.00, 200, 45),
        ("CR-TBL-24", "FOB", "USD", "Tashkent (air cargo)", 52.50, 200, 45),
    ]
    for sku, incoterm, currency, origin, price, moq, lead_time in definitions:
        product = products[sku]
        exists = session.scalar(
            select(ProductPrice).where(
                ProductPrice.product_id == product.id,
                ProductPrice.incoterm == incoterm,
                ProductPrice.currency == currency,
            )
        )
        if exists is not None:
            continue
        session.add(
            ProductPrice(
                product_id=product.id,
                incoterm=incoterm,
                currency=currency,
                origin_point=origin,
                unit_price=price,
                moq=moq,
                valid_from=today() - dt.timedelta(days=20),
                valid_to=today() + dt.timedelta(days=160),
                payment_terms="30% advance, 70% against B/L copy",
                lead_time_days=lead_time,
                status="approved",
            )
        )
    # One deliberately expired price so the validity rule is visible in demo.
    towel = products["TX-TOW-500"]
    if not session.scalar(
        select(ProductPrice).where(
            ProductPrice.product_id == towel.id, ProductPrice.status == "expired"
        )
    ):
        session.add(
            ProductPrice(
                product_id=towel.id,
                incoterm="CFR",
                currency="USD",
                origin_point="Riga",
                unit_price=2.80,
                moq=3000,
                valid_from=today() - dt.timedelta(days=200),
                valid_to=today() - dt.timedelta(days=15),
                payment_terms="Irrevocable L/C at sight",
                lead_time_days=40,
                status="expired",
            )
        )
    session.flush()


def _demo_certificates(session: Session, products: dict[str, Product]) -> None:
    definitions = [
        ("OEKO-TEX Standard 100", "other", "TX-TOW-500", "OEKO-TEX Association", 400),
        ("ISO 9001:2015", "iso", None, "TUV Rheinland", 620),
        ("Halal certificate", "halal", "FD-APR-ORG", "Uzbekistan Halal Center", 45),
        (
            "Certificate of Origin (Form A)",
            "certificate_of_origin",
            None,
            "Chamber of Commerce",
            120,
        ),
        ("Phytosanitary certificate", "phytosanitary", "FD-APR-ORG", "State Plant Quarantine", 25),
    ]
    for name, cert_type, sku, issuer, days_left in definitions:
        if session.scalar(select(Certificate).where(Certificate.name == name)):
            continue
        session.add(
            Certificate(
                name=name,
                cert_type=cert_type,
                product_id=products[sku].id if sku else None,
                issuer=issuer,
                number=f"{cert_type.upper()[:4]}-{2000 + days_left}",
                issue_date=today() - dt.timedelta(days=300),
                expiry_date=today() + dt.timedelta(days=days_left),
                target_market="EU, GCC, CIS",
                verification_status="verified",
                status="valid",
            )
        )
    session.flush()


def _demo_buyers(
    session: Session, users: dict[str, User], agents: dict[str, SalesAgent]
) -> dict[str, Buyer]:
    definitions = [
        {
            "company_name": "Nordic Home AB",
            "contact_person": "Erik Lindqvist",
            "position": "Purchasing Director",
            "country": "Sweden",
            "city": "Gothenburg",
            "email": "erik.lindqvist@nordichome.example",
            "phone": "+46 31 555 0101",
            "website": "https://nordichome.example",
            "linkedin": "https://linkedin.com/company/nordic-home",
            "buyer_type": "importer",
            "interested_categories": "textile",
            "annual_potential": 420000,
            "target_market": "Scandinavia",
            "language": "en",
            "source": "linkedin",
            "risk_level": "low",
            "manager": "nigora",
            "agent": None,
        },
        {
            "company_name": "Al Noor Trading LLC",
            "contact_person": "Khalid Al Mansoori",
            "position": "General Manager",
            "country": "UAE",
            "city": "Dubai",
            "email": "khalid@alnoortrading.example",
            "phone": "+971 4 555 0202",
            "website": "https://alnoortrading.example",
            "buyer_type": "distributor",
            "interested_categories": "dried_fruit,textile",
            "annual_potential": 610000,
            "target_market": "GCC",
            "language": "en",
            "source": "alibaba",
            "risk_level": "medium",
            "manager": "dilshod",
            "agent": "gulf",
        },
        {
            "company_name": "Vostok Retail Group",
            "contact_person": "Айгуль Нурланова",
            "position": "Категорийный менеджер",
            "country": "Kazakhstan",
            "city": "Almaty",
            "email": "a.nurlanova@vostokretail.example",
            "phone": "+7 727 555 0303",
            "buyer_type": "retailer",
            "interested_categories": "textile,ceramics",
            "annual_potential": 280000,
            "target_market": "Central Asia",
            "language": "ru",
            "source": "trade_fair",
            "risk_level": "low",
            "manager": "nigora",
            "agent": None,
        },
        {
            "company_name": "Bavaria Naturkost GmbH",
            "contact_person": "Anna Weber",
            "position": "Head of Sourcing",
            "country": "Germany",
            "city": "Munich",
            "email": "a.weber@bavaria-naturkost.example",
            "phone": "+49 89 555 0404",
            "website": "https://bavaria-naturkost.example",
            "buyer_type": "wholesaler",
            "interested_categories": "dried_fruit",
            "annual_potential": 350000,
            "target_market": "EU",
            "language": "en",
            "source": "email",
            "risk_level": "medium",
            "manager": "dilshod",
            "agent": "eu",
        },
    ]
    buyers: dict[str, Buyer] = {}
    for definition in definitions:
        name = definition["company_name"]
        buyer = session.scalar(select(Buyer).where(Buyer.company_name == name))
        if buyer is not None:
            buyers[name] = buyer
            continue
        manager = definition.pop("manager")
        agent = definition.pop("agent")
        buyer = Buyer(
            **definition,
            manager_id=users[manager].id if manager else None,
            agent_id=agents[agent].id if agent else None,
            status="active",
        )
        session.add(buyer)
        session.flush()
        session.add(
            BuyerContact(
                buyer_id=buyer.id,
                full_name=buyer.contact_person or "Contact",
                position=buyer.position,
                email=buyer.email,
                phone=buyer.phone,
                language=buyer.language,
                is_primary=True,
            )
        )
        buyers[name] = buyer
    session.flush()
    return buyers


def _demo_agents(session: Session) -> dict[str, SalesAgent]:
    definitions = [
        ("gulf", "Rashid Trading Agency", "GCC region", "UAE", 3.5),
        ("eu", "EuroBridge Sourcing", "European Union", "Germany", 4.0),
    ]
    agents: dict[str, SalesAgent] = {}
    for code, name, market, country, commission in definitions:
        agent = session.scalar(select(SalesAgent).where(SalesAgent.name == name))
        if agent is None:
            agent = SalesAgent(
                name=name,
                market=market,
                country=country,
                email=f"info@{code}-agency.example",
                phone="+971 4 555 0900" if code == "gulf" else "+49 89 555 0900",
                commission_percent=commission,
                commission_terms=f"{commission}% of the shipped FOB value, paid after payment receipt",
                commission_status="active",
            )
            session.add(agent)
        agents[code] = agent
    session.flush()
    return agents


def _demo_leads(
    session: Session, buyers: dict[str, Buyer], products: dict[str, Product], users: dict[str, User]
) -> dict[str, Lead]:
    definitions = [
        {
            "key": "nordic_towel",
            "title": "Nordic Home AB — bath towel programme 2026",
            "buyer": "Nordic Home AB",
            "product": "TX-TOW-500",
            "source": "linkedin",
            "source_detail": "Inbound LinkedIn message from purchasing director",
            "status": "quotation_sent",
            "temperature": "hot",
            "expected_value": 78000,
            "probability": 60,
            "next_step": "Wait for feedback on FOB price",
            "next_follow_up": today() - dt.timedelta(days=2),
            "incoterm": "FOB",
            "destination": "Gothenburg",
            "manager": "nigora",
        },
        {
            "key": "alnoor_apricot",
            "title": "Al Noor Trading — dried apricots RFQ (Alibaba)",
            "buyer": "Al Noor Trading LLC",
            "product": "FD-APR-ORG",
            "source": "alibaba",
            "source_detail": "Alibaba RFQ #RFQ-88213",
            "status": "rfq_received",
            "temperature": "hot",
            "expected_value": 96000,
            "probability": 45,
            "next_step": "Prepare CIF Jebel Ali quotation",
            "next_follow_up": today() + dt.timedelta(days=1),
            "incoterm": "CIF",
            "destination": "Jebel Ali",
            "manager": "dilshod",
        },
        {
            "key": "bavaria_cert",
            "title": "Bavaria Naturkost — organic certification enquiry",
            "buyer": "Bavaria Naturkost GmbH",
            "product": "FD-APR-ORG",
            "source": "email",
            "source_detail": "Buyer asked for EU organic and HACCP documents",
            "status": "in_review",
            "temperature": "warm",
            "expected_value": 54000,
            "probability": 30,
            "next_step": "Confirm which certificates can be issued",
            "next_follow_up": today() + dt.timedelta(days=3),
            "incoterm": "DAP",
            "destination": "Munich",
            "manager": "dilshod",
        },
        {
            "key": "alnoor_cif",
            "title": "Al Noor Trading — CIF Dubai towel price request",
            "buyer": "Al Noor Trading LLC",
            "product": "TX-TOW-500",
            "source": "alibaba",
            "source_detail": "Second enquiry, CIF Dubai pricing",
            "status": "qualified",
            "temperature": "warm",
            "expected_value": 42000,
            "probability": 35,
            "next_step": "Collect freight quotes for Jebel Ali",
            "next_follow_up": today() + dt.timedelta(days=4),
            "incoterm": "CIF",
            "destination": "Jebel Ali",
            "manager": "dilshod",
        },
        {
            "key": "vostok_sample",
            "title": "Vostok Retail — ceramic tableware sample",
            "buyer": "Vostok Retail Group",
            "product": "CR-TBL-24",
            "source": "trade_fair",
            "source_detail": "Met at the Almaty Home Expo",
            "status": "sample_sent",
            "temperature": "warm",
            "expected_value": 21000,
            "probability": 50,
            "next_step": "Ask for sample feedback",
            "next_follow_up": today() + dt.timedelta(days=2),
            "incoterm": "DAP",
            "destination": "Almaty",
            "manager": "nigora",
        },
        {
            "key": "nordic_bed_won",
            "title": "Nordic Home AB — hotel bed linen contract",
            "buyer": "Nordic Home AB",
            "product": "TX-BED-220",
            "source": "referral",
            "source_detail": "Referred by an existing customer",
            "status": "closed_won",
            "temperature": "hot",
            "expected_value": 132000,
            "probability": 100,
            "next_step": "Shipment in progress",
            "incoterm": "FOB",
            "destination": "Gothenburg",
            "manager": "nigora",
        },
        {
            "key": "vostok_lost",
            "title": "Vostok Retail — towel tender Q1",
            "buyer": "Vostok Retail Group",
            "product": "TX-TOW-500",
            "source": "website_inquiry",
            "source_detail": "Tender request through the website",
            "status": "closed_lost",
            "temperature": "cold",
            "expected_value": 38000,
            "probability": 0,
            "lost_reason": "price_too_high",
            "lost_comment": "Turkish supplier offered 8% lower FOB price.",
            "incoterm": "FOB",
            "destination": "Almaty",
            "manager": "nigora",
        },
    ]
    leads: dict[str, Lead] = {}
    for definition in definitions:
        key = definition.pop("key")
        title = definition["title"]
        lead = session.scalar(select(Lead).where(Lead.title == title))
        if lead is not None:
            leads[key] = lead
            continue
        buyer = buyers[definition.pop("buyer")]
        product = products[definition.pop("product")]
        manager = users[definition.pop("manager")]
        lead = Lead(
            **definition,
            buyer_id=buyer.id,
            product_id=product.id,
            category_id=product.category_id,
            country=buyer.country,
            manager_id=manager.id,
            currency="USD",
        )
        if lead.status == "closed_won":
            lead.won_at = now()
            lead.closed_at = now()
        if lead.status == "closed_lost":
            lead.closed_at = now()
        session.add(lead)
        leads[key] = lead
    session.flush()
    return leads


def _demo_sales_documents(
    session: Session,
    buyers: dict[str, Buyer],
    products: dict[str, Product],
    leads: dict[str, Lead],
    users: dict[str, User],
) -> None:
    """Create the demo RFQ, quotation Q-2026-0001, contract and shipment."""
    apricot = products["FD-APR-ORG"]
    towel = products["TX-TOW-500"]
    bed = products["TX-BED-220"]
    al_noor = buyers["Al Noor Trading LLC"]
    nordic = buyers["Nordic Home AB"]

    rfq_number = f"RFQ-{today().year}-0001"
    rfq = session.scalar(select(RFQ).where(RFQ.number == rfq_number))
    if rfq is None:
        rfq = RFQ(
            number=rfq_number,
            buyer_id=al_noor.id,
            lead_id=leads["alnoor_apricot"].id,
            received_at=today() - dt.timedelta(days=5),
            deadline=today() + dt.timedelta(days=2),
            target_incoterm="CIF",
            destination="Jebel Ali, UAE",
            payment_condition="Irrevocable L/C at sight",
            certificate_requirements="Halal, Certificate of Origin, Phytosanitary",
            packaging_requirements="10 kg export cartons with food-grade liner, palletised",
            currency="USD",
            status="in_review",
            internal_notes="Buyer requested a 20 ft container trial, repeat monthly orders expected.",
        )
        session.add(rfq)
        session.flush()
        session.add_all(
            [
                RFQItem(
                    rfq_id=rfq.id,
                    product_id=apricot.id,
                    description="Organic dried apricots 80/100",
                    quantity=18000,
                    unit="kg",
                    target_price=3.35,
                ),
                RFQItem(
                    rfq_id=rfq.id,
                    product_id=towel.id,
                    description="Cotton bath towel 70x140, white",
                    quantity=6000,
                    unit="pcs",
                    target_price=2.80,
                ),
            ]
        )

    quotation_number = f"Q-{today().year}-0001"
    quotation = session.scalar(select(Quotation).where(Quotation.number == quotation_number))
    if quotation is None:
        quotation = Quotation(
            number=quotation_number,
            revision=1,
            buyer_id=al_noor.id,
            lead_id=leads["alnoor_apricot"].id,
            rfq_id=rfq.id,
            language="en",
            currency="USD",
            issue_date=today() - dt.timedelta(days=3),
            valid_until=today() + dt.timedelta(days=27),
            payment_terms="30% advance, 70% against B/L copy",
            delivery_terms="CIF Jebel Ali, UAE",
            incoterm="CIF",
            loading_port="Tashkent — Jebel Ali (multimodal)",
            destination="Jebel Ali, UAE",
            lead_time_days=28,
            packaging="Apricots: 10 kg carton with liner. Towels: 20 pcs per carton, individual polybag.",
            certificate_refs="Halal certificate, Certificate of Origin (Form A), Phytosanitary certificate",
            intro_text=(
                "Thank you for your enquiry. Please find below our offer for organic dried apricots "
                "and cotton bath towels on CIF Jebel Ali terms."
            ),
            remarks="Prices are based on a full 40 HC container. Partial loads are quoted separately.",
            freight_cost=2400.0,
            insurance_cost=380.0,
            discount=500.0,
            status="approved",
            manager_id=users["dilshod"].id,
            approved_by_id=users["dilshod"].id,
            approved_at=now(),
        )
        session.add(quotation)
        session.flush()
        items = [
            (apricot, "Organic dried apricots, sun-dried 80/100", 18000, "kg", 3.55),
            (towel, "100% cotton bath towel 70x140, 500 gsm, white", 6000, "pcs", 2.95),
        ]
        subtotal = 0.0
        for order, (product, description, quantity, unit, unit_price) in enumerate(items):
            line_total = round(quantity * unit_price, 2)
            subtotal += line_total
            session.add(
                QuotationItem(
                    quotation_id=quotation.id,
                    product_id=product.id,
                    description=description,
                    hs_code=product.hs_code,
                    quantity=quantity,
                    unit=unit,
                    unit_price=unit_price,
                    line_total=line_total,
                    moq=product.moq,
                    lead_time_days=product.lead_time_days,
                    packaging=product.packaging_type,
                    sort_order=order,
                )
            )
        quotation.subtotal = round(subtotal, 2)
        quotation.grand_total = round(
            subtotal + quotation.freight_cost + quotation.insurance_cost - quotation.discount, 2
        )
        session.flush()

    contract_number = f"C-{today().year}-0001"
    contract = session.scalar(select(Contract).where(Contract.number == contract_number))
    if contract is None:
        contract = Contract(
            number=contract_number,
            buyer_id=nordic.id,
            lead_id=leads["nordic_bed_won"].id,
            sign_date=today() - dt.timedelta(days=25),
            valid_until=today() + dt.timedelta(days=340),
            currency="USD",
            amount=132000,
            incoterm="FOB",
            payment_terms="Irrevocable L/C at sight",
            delivery_terms="FOB Tashkent",
            status="in_execution",
            notes="Annual hotel bed linen supply contract, four shipments.",
        )
        session.add(contract)
        session.flush()

    shipment_number = f"SH-{today().year}-0001"
    shipment = session.scalar(select(Shipment).where(Shipment.number == shipment_number))
    if shipment is None:
        shipment = Shipment(
            number=shipment_number,
            buyer_id=nordic.id,
            lead_id=leads["nordic_bed_won"].id,
            contract_id=contract.id,
            incoterm="FOB",
            origin="Samarkand",
            loading_port="Tashkent rail terminal",
            destination="Gothenburg, Sweden",
            container_type="40HC",
            forwarder="Central Asia Logistics",
            carrier="Rail + short sea",
            tracking_reference="CAL-2026-118842",
            etd=today() + dt.timedelta(days=6),
            eta=today() + dt.timedelta(days=32),
            customs_status="declaration_submitted",
            status="booked",
            currency="USD",
            planned_freight_cost=4200,
            planned_insurance_cost=520,
            freight_cost=4450,
            insurance_cost=520,
            notes="First of four contract shipments.",
        )
        session.add(shipment)
        session.flush()
        session.add(
            ShipmentItem(
                shipment_id=shipment.id,
                product_id=bed.id,
                description="Hotel bed linen set, sateen 220 TC, white",
                hs_code=bed.hs_code,
                quantity=1800,
                unit="set",
                unit_price=18.40,
                packages=300,
                net_weight=3780,
                gross_weight=4230,
            )
        )
        shipment.package_count = 300
        shipment.net_weight = 3780
        shipment.gross_weight = 4230
    session.flush()


def _demo_catalog(session: Session, products: dict[str, Product]) -> None:
    title = "Samarkand Export Textile — Export Catalog 2026"
    catalog = session.scalar(select(Catalog).where(Catalog.title == title))
    if catalog is not None:
        return
    catalog = Catalog(
        title=title,
        language="en",
        version="1.0",
        subtitle="Cotton home textile, dried fruits and ceramics from Uzbekistan",
        cover_note="Prices and terms are confirmed in writing per enquiry.",
        contact_text="Export department is available on working days 09:00-18:00 (GMT+5).",
        include_certificates=1,
        include_prices=0,
        template="modern",
    )
    session.add(catalog)
    session.flush()
    for order, sku in enumerate(("TX-TOW-500", "TX-BED-220", "FD-APR-ORG", "CR-TBL-24")):
        session.add(
            CatalogItem(catalog_id=catalog.id, product_id=products[sku].id, sort_order=order)
        )
    session.flush()


def seed_demo_data(session: Session) -> None:
    """Populate the database with the full demo dataset."""
    _demo_company(session)
    users = _demo_users(session)
    categories = {row.code: row for row in session.scalars(select(ProductCategory)).unique().all()}
    products = _demo_products(session, categories)
    _demo_prices(session, products)
    _demo_certificates(session, products)
    agents = _demo_agents(session)
    buyers = _demo_buyers(session, users, agents)
    leads = _demo_leads(session, buyers, products, users)
    _demo_sales_documents(session, buyers, products, leads, users)
    _demo_catalog(session, products)
    log.info("Demo dataset seeded")


def database_is_empty(session: Session) -> bool:
    """True when no user account exists yet."""
    return not session.scalar(select(func.count()).select_from(User))


def initialise(with_demo: bool = True) -> dict:
    """Run reference seeding and, on a fresh database, the demo dataset."""
    with session_scope() as session:
        seed_reference_data(session)
        fresh = database_is_empty(session)
        if fresh and with_demo:
            seed_demo_data(session)
        return {"fresh": fresh, "demo": fresh and with_demo}
