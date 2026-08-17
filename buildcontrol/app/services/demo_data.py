"""Demo dataset seeded on first run.

Creates two realistic projects with estimates, purchases, stock movements,
work stages and expenses that demonstrate the normal / warning / over-budget
states of the interface.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select

from app.database.session import session_scope
from app.models.entities import Project, User
from app.models.enums import (
    CounterpartyKind,
    EstimateItemStatus,
    EstimateStatus,
    ExpenseCategory,
    ExpenseStatus,
    OrderStatus,
    PaymentMethod,
    ProjectStatus,
    ProjectType,
    PurchaseStatus,
    RoleCode,
    StageStatus,
    TxKind,
    Unit,
)
from app.repositories import Repositories
from app.services import audit_service
from app.services.audit_service import Action
from app.services.auth_service import ensure_roles
from app.services.settings_service import seed_reference_data
from app.utils.security import hash_password

TODAY = date.today()

#: username, full name, role, password
DEMO_USERS: list[tuple[str, str, str, str]] = [
    ("admin", "Bosh administrator", RoleCode.ADMIN.value, "admin123"),
    ("rahbar", "Alisher Karimov", RoleCode.MANAGER.value, "rahbar123"),
    ("smetachi", "Dilnoza Yusupova", RoleCode.ESTIMATOR.value, "smeta123"),
    ("omborchi", "Bekzod Tursunov", RoleCode.STOREKEEPER.value, "ombor123"),
    ("kuzatuvchi", "Nodira Ergasheva", RoleCode.VIEWER.value, "kuzat123"),
]


def is_seeded() -> bool:
    """True when the demo dataset (or any project) already exists."""
    with session_scope() as session:
        return bool(session.scalar(select(func.count()).select_from(Project)))


def seed_demo_data() -> None:
    """Populate the database with the demo dataset (idempotent)."""
    if is_seeded():
        return
    seed_reference_data()
    with session_scope() as session:
        ensure_roles(session)
        repos = Repositories(session)

        # -- users --------------------------------------------------------- #
        users: dict[str, User] = {}
        for username, full_name, role_code, password in DEMO_USERS:
            existing = repos.users.by_username(username)
            if existing is None:
                role = repos.roles.by_code(role_code)
                assert role is not None
                existing = repos.users.create(
                    username=username,
                    full_name=full_name,
                    password_hash=hash_password(password),
                    role_id=role.id,
                    email=f"{username}@buildcontrol.uz",
                    phone="+998 90 000 00 00",
                )
            users[username] = existing

        admin, manager, estimator, storekeeper = (
            users["admin"],
            users["rahbar"],
            users["smetachi"],
            users["omborchi"],
        )

        company = repos.company.get_or_create()
        company.name = "BuildControl Qurilish MChJ"
        company.address = "Toshkent sh., Amir Temur ko'chasi 108"
        company.phone = "+998 71 200 00 00"
        company.requisites = "STIR 300123456 · Hisob raqam 20208000900123456001"

        # -- counterparties ------------------------------------------------ #
        suppliers = [
            repos.counterparties.create(
                kind=CounterpartyKind.SUPPLIER.value,
                name="Qurilish Savdo MChJ",
                tin="301112233",
                phone="+998 90 111 22 33",
                email="sales@qsavdo.uz",
                address="Toshkent, Sergeli",
                category="Beton, armatura",
                bank_details="Ipoteka Bank, MFO 00449",
                rating=4.5,
            ),
            repos.counterparties.create(
                kind=CounterpartyKind.SUPPLIER.value,
                name="Stroy Market Servis",
                tin="302223344",
                phone="+998 93 222 33 44",
                email="info@stroymarket.uz",
                address="Toshkent, Yunusobod",
                category="Pardozlash materiallari",
                bank_details="Kapital Bank, MFO 01083",
                rating=4.1,
            ),
            repos.counterparties.create(
                kind=CounterpartyKind.SUPPLIER.value,
                name="ElektroTexnika Plus",
                tin="303334455",
                phone="+998 94 333 44 55",
                email="order@elektroplus.uz",
                address="Samarqand sh.",
                category="Elektr jihozlari",
                bank_details="Asaka Bank, MFO 00874",
                rating=3.9,
            ),
        ]
        contractors = [
            repos.counterparties.create(
                kind=CounterpartyKind.CONTRACTOR.value,
                name="Mustahkam Bino Qurilish",
                tin="304445566",
                phone="+998 91 444 55 66",
                category="Umumqurilish",
                contract_amount=420_000_000,
                paid_amount=250_000_000,
                completed_work=60,
                delay_days=4,
                quality_score=4.5,
                disputes=0,
                rating=4.4,
            ),
            repos.counterparties.create(
                kind=CounterpartyKind.CONTRACTOR.value,
                name="Interyer Usta Servis",
                tin="305556677",
                phone="+998 97 555 66 77",
                category="Pardozlash, interyer",
                contract_amount=180_000_000,
                paid_amount=195_000_000,
                completed_work=85,
                delay_days=21,
                quality_score=3.5,
                disputes=2,
                rating=3.1,
            ),
        ]

        # -- materials ----------------------------------------------------- #
        materials = [
            repos.materials.create(
                sku="MAT-001",
                name="Sement M400 (50 kg)",
                category="Beton",
                unit=Unit.PIECE.value,
                min_stock=100,
                standard_price=55_000,
                supplier_id=suppliers[0].id,
            ),
            repos.materials.create(
                sku="MAT-002",
                name="Armatura A500C d12",
                category="Beton",
                unit=Unit.TON.value,
                min_stock=2,
                standard_price=8_900_000,
                supplier_id=suppliers[0].id,
            ),
            repos.materials.create(
                sku="MAT-003",
                name="Gipskarton 12.5 mm",
                category="Pardozlash",
                unit=Unit.SQM.value,
                min_stock=200,
                standard_price=42_000,
                supplier_id=suppliers[1].id,
            ),
            repos.materials.create(
                sku="MAT-004",
                name="Kabel VVG 3x2.5",
                category="Elektr",
                unit=Unit.METER.value,
                min_stock=500,
                standard_price=18_500,
                supplier_id=suppliers[2].id,
            ),
            repos.materials.create(
                sku="MAT-005",
                name="Laminat 33-klass",
                category="Pardozlash",
                unit=Unit.SQM.value,
                min_stock=80,
                standard_price=145_000,
                supplier_id=suppliers[1].id,
            ),
        ]

        # -- project 1: apartment renovation -------------------------------- #
        project1 = repos.projects.create(
            code="PRJ-0001",
            name="Yunusobod xonadon ta'miri",
            client="Karimov Sardor",
            address="Toshkent, Yunusobod 12-mavze, 45-uy, 27-xonadon",
            project_type=ProjectType.RENOVATION.value,
            start_date=TODAY - timedelta(days=55),
            end_date=TODAY + timedelta(days=35),
            manager_id=manager.id,
            planned_budget=320_000_000,
            status=ProjectStatus.ACTIVE.value,
            notes="Uch xonali xonadon, to'liq kapital ta'mir.",
        )
        version1 = repos.versions.create(
            project_id=project1.id,
            version_no=1,
            status=EstimateStatus.APPROVED.value,
            is_current=True,
            created_by_id=estimator.id,
            approved_by_id=manager.id,
            note="Mijoz bilan kelishilgan asosiy smeta",
        )

        s_prep = repos.sections.create(
            version_id=version1.id, code="1", name="Tayyorlov ishlari", order_index=0
        )
        s_demo = repos.sections.create(
            version_id=version1.id,
            parent_id=s_prep.id,
            code="1.1",
            name="Demontaj",
            order_index=0,
        )
        s_trash = repos.sections.create(
            version_id=version1.id,
            parent_id=s_prep.id,
            code="1.2",
            name="Chiqindi olib chiqish",
            order_index=1,
        )
        s_fin = repos.sections.create(
            version_id=version1.id, code="2", name="Pardozlash ishlari", order_index=1
        )
        s_elec = repos.sections.create(
            version_id=version1.id, code="3", name="Elektr ishlari", order_index=2
        )

        items1 = [
            repos.items.create(
                section_id=s_demo.id,
                code="1.1.1",
                name="Eski devor qoplamalarini olish",
                category="prep",
                unit=Unit.SQM.value,
                quantity=180,
                plan_unit_price=35_000,
                progress_percent=100,
                responsible_id=manager.id,
                status=EstimateItemStatus.DONE.value,
                order_index=0,
            ),
            repos.items.create(
                section_id=s_trash.id,
                code="1.2.1",
                name="Qurilish chiqindisini olib chiqish",
                category="prep",
                unit=Unit.CBM.value,
                quantity=24,
                plan_unit_price=280_000,
                progress_percent=100,
                status=EstimateItemStatus.DONE.value,
                order_index=1,
            ),
            repos.items.create(
                section_id=s_fin.id,
                code="2.1",
                name="Gipskarton devor va shift",
                category="finishing",
                unit=Unit.SQM.value,
                quantity=210,
                plan_unit_price=185_000,
                progress_percent=65,
                responsible_id=manager.id,
                status=EstimateItemStatus.IN_PROGRESS.value,
                order_index=2,
            ),
            repos.items.create(
                section_id=s_fin.id,
                code="2.2",
                name="Laminat yotqizish",
                category="finishing",
                unit=Unit.SQM.value,
                quantity=95,
                plan_unit_price=210_000,
                progress_percent=20,
                status=EstimateItemStatus.NEEDS_PURCHASE.value,
                order_index=3,
            ),
            repos.items.create(
                section_id=s_elec.id,
                code="3.1",
                name="Elektr o'tkazgichlarni almashtirish",
                category="electrical",
                unit=Unit.METER.value,
                quantity=640,
                plan_unit_price=27_000,
                progress_percent=80,
                status=EstimateItemStatus.IN_PROGRESS.value,
                order_index=4,
            ),
            repos.items.create(
                section_id=s_elec.id,
                code="3.2",
                name="Rozetka va vyklyuchatellar o'rnatish",
                category="electrical",
                unit=Unit.PIECE.value,
                quantity=48,
                plan_unit_price=95_000,
                progress_percent=40,
                status=EstimateItemStatus.IN_PROGRESS.value,
                order_index=5,
            ),
        ]

        # -- project 2: office building ------------------------------------ #
        project2 = repos.projects.create(
            code="PRJ-0002",
            name="Samarqand ofis binosi",
            client="Silk Road Invest MChJ",
            address="Samarqand sh., Registon ko'chasi 14",
            project_type=ProjectType.NEW_BUILD.value,
            start_date=TODAY - timedelta(days=120),
            end_date=TODAY + timedelta(days=210),
            manager_id=manager.id,
            planned_budget=2_450_000_000,
            status=ProjectStatus.ACTIVE.value,
            notes="4 qavatli ofis binosi, umumiy maydon 2 800 m².",
        )
        version2 = repos.versions.create(
            project_id=project2.id,
            version_no=1,
            status=EstimateStatus.SUBMITTED.value,
            is_current=True,
            created_by_id=estimator.id,
            note="Birinchi tahrir, tasdiq kutilmoqda",
        )
        s2_zero = repos.sections.create(
            version_id=version2.id, code="1", name="Nol bosqich", order_index=0
        )
        s2_conc = repos.sections.create(
            version_id=version2.id, code="2", name="Beton ishlari", order_index=1
        )
        s2_rebar = repos.sections.create(
            version_id=version2.id,
            parent_id=s2_conc.id,
            code="2.1",
            name="Armatura",
            order_index=0,
        )
        s2_pour = repos.sections.create(
            version_id=version2.id,
            parent_id=s2_conc.id,
            code="2.2",
            name="Beton quyish",
            order_index=1,
        )
        s2_fac = repos.sections.create(
            version_id=version2.id, code="3", name="Fasad ishlari", order_index=2
        )

        items2 = [
            repos.items.create(
                section_id=s2_zero.id,
                code="1.1",
                name="Kotlovan qazish",
                category="prep",
                unit=Unit.CBM.value,
                quantity=1850,
                plan_unit_price=95_000,
                progress_percent=100,
                status=EstimateItemStatus.DONE.value,
                order_index=0,
            ),
            repos.items.create(
                section_id=s2_rebar.id,
                code="2.1.1",
                name="Armatura karkas montaji",
                category="concrete",
                unit=Unit.TON.value,
                quantity=64,
                plan_unit_price=11_200_000,
                progress_percent=70,
                responsible_id=manager.id,
                status=EstimateItemStatus.IN_PROGRESS.value,
                order_index=1,
            ),
            repos.items.create(
                section_id=s2_pour.id,
                code="2.2.1",
                name="Monolit beton quyish M300",
                category="concrete",
                unit=Unit.CBM.value,
                quantity=920,
                plan_unit_price=780_000,
                progress_percent=55,
                status=EstimateItemStatus.IN_PROGRESS.value,
                order_index=2,
            ),
            repos.items.create(
                section_id=s2_fac.id,
                code="3.1",
                name="Ventilyatsiyali fasad montaji",
                category="facade",
                unit=Unit.SQM.value,
                quantity=1650,
                plan_unit_price=620_000,
                progress_percent=5,
                status=EstimateItemStatus.NEEDS_PURCHASE.value,
                order_index=3,
            ),
        ]

        # -- stock movements ------------------------------------------------ #
        stock_ops = [
            (materials[0], TxKind.IN.value, 400, 55_000, None, None, 40),
            (materials[0], TxKind.OUT.value, 260, 55_000, project2.id, items2[2].id, 25),
            (materials[1], TxKind.IN.value, 12, 8_900_000, None, None, 38),
            (materials[1], TxKind.OUT.value, 9.5, 8_900_000, project2.id, items2[1].id, 20),
            (materials[2], TxKind.IN.value, 320, 42_000, None, None, 30),
            (materials[2], TxKind.OUT.value, 205, 43_500, project1.id, items1[2].id, 14),
            (materials[3], TxKind.IN.value, 900, 18_500, None, None, 28),
            (materials[3], TxKind.OUT.value, 640, 19_200, project1.id, items1[4].id, 12),
            (materials[4], TxKind.IN.value, 60, 145_000, None, None, 9),
            (materials[4], TxKind.LOSS.value, 4, 145_000, project1.id, items1[3].id, 5),
        ]
        for material, kind, qty, price, project_id, item_id, days_ago in stock_ops:
            repos.stock.create(
                tx_date=TODAY - timedelta(days=days_ago),
                kind=kind,
                material_id=material.id,
                quantity=qty,
                unit_price=price,
                project_id=project_id,
                estimate_item_id=item_id,
                user_id=storekeeper.id,
                note="Demo",
            )

        # -- work stages ---------------------------------------------------- #
        stages = [
            (
                project1.id,
                "Demontaj va tayyorlov",
                s_prep.id,
                -55,
                -40,
                100,
                StageStatus.DONE.value,
            ),
            (project1.id, "Elektr montaj", s_elec.id, -38, -10, 80, StageStatus.IN_PROGRESS.value),
            (project1.id, "Gipskarton ishlari", s_fin.id, -30, -5, 65, StageStatus.REVIEW.value),
            (project1.id, "Laminat va pardoz", s_fin.id, -6, 25, 20, StageStatus.IN_PROGRESS.value),
            (project2.id, "Nol bosqich", s2_zero.id, -120, -70, 100, StageStatus.DONE.value),
            (
                project2.id,
                "Karkas va beton",
                s2_conc.id,
                -70,
                -3,
                62,
                StageStatus.IN_PROGRESS.value,
            ),
            (project2.id, "Fasad montaji", s2_fac.id, 5, 150, 5, StageStatus.NOT_STARTED.value),
        ]
        stage_objects = []
        for index, (pid, name, section_id, start, end, progress, status) in enumerate(stages):
            stage_objects.append(
                repos.stages.create(
                    project_id=pid,
                    name=name,
                    section_id=section_id,
                    plan_start=TODAY + timedelta(days=start),
                    plan_end=TODAY + timedelta(days=end),
                    actual_start=TODAY + timedelta(days=start + 1) if progress else None,
                    actual_end=TODAY + timedelta(days=end) if progress >= 100 else None,
                    progress_percent=progress,
                    responsible_id=manager.id,
                    status=status,
                    order_index=index,
                )
            )

        # -- site logs ------------------------------------------------------ #
        repos.logs.create(
            log_date=TODAY - timedelta(days=3),
            project_id=project1.id,
            stage_id=stage_objects[2].id,
            work_done="Yotoqxona va zal shiftida gipskarton karkasi yig'ildi.",
            progress_percent=65,
            workers_count=6,
            issue="Profil yetishmadi, qo'shimcha xarid kerak.",
            author_id=manager.id,
        )
        repos.logs.create(
            log_date=TODAY - timedelta(days=1),
            project_id=project2.id,
            stage_id=stage_objects[5].id,
            work_done="3-qavat plitasi armaturalandi, beton quyishga tayyorlandi.",
            progress_percent=62,
            workers_count=18,
            issue="",
            author_id=manager.id,
        )

        # -- purchase requests --------------------------------------------- #
        request1 = repos.requests.create(
            number="XT-00001",
            project_id=project1.id,
            estimate_item_id=items1[3].id,
            title="Laminat 33-klass, 95 m²",
            unit=Unit.SQM.value,
            quantity=95,
            est_price=145_000,
            needed_date=TODAY + timedelta(days=7),
            delivery_address=project1.address,
            responsible_id=manager.id,
            status=PurchaseStatus.SUBMITTED.value,
            note="Rangi: yong'oq",
        )
        quote_a = repos.quotes.create(
            request_id=request1.id,
            supplier_id=suppliers[1].id,
            supplier_name=suppliers[1].name,
            contact="+998 93 222 33 44",
            unit_price=142_000,
            delivery_cost=900_000,
            delivery_days=5,
            payment_terms="50% oldindan",
        )
        repos.quotes.create(
            request_id=request1.id,
            supplier_id=suppliers[0].id,
            supplier_name=suppliers[0].name,
            contact="+998 90 111 22 33",
            unit_price=138_000,
            delivery_cost=2_400_000,
            delivery_days=12,
            payment_terms="To'liq oldindan",
        )
        quote_a.is_selected = True

        request2 = repos.requests.create(
            number="XT-00002",
            project_id=project2.id,
            estimate_item_id=items2[3].id,
            title="Fasad kassetalari, 1650 m²",
            unit=Unit.SQM.value,
            quantity=1650,
            est_price=480_000,
            needed_date=TODAY + timedelta(days=30),
            delivery_address=project2.address,
            responsible_id=manager.id,
            status=PurchaseStatus.DRAFT.value,
        )
        repos.quotes.create(
            request_id=request2.id,
            supplier_id=suppliers[2].id,
            supplier_name=suppliers[2].name,
            unit_price=495_000,
            delivery_cost=18_000_000,
            delivery_days=25,
            payment_terms="30/70",
        )

        request3 = repos.requests.create(
            number="XT-00003",
            project_id=project1.id,
            off_estimate=True,
            title="Qo'shimcha gipskarton profil",
            unit=Unit.PIECE.value,
            quantity=120,
            est_price=32_000,
            needed_date=TODAY + timedelta(days=2),
            delivery_address=project1.address,
            responsible_id=storekeeper.id,
            status=PurchaseStatus.APPROVED.value,
            note="Smetadan tashqari, obyektda zarurat tug'ildi.",
        )
        quote_c = repos.quotes.create(
            request_id=request3.id,
            supplier_id=suppliers[1].id,
            supplier_name=suppliers[1].name,
            unit_price=31_500,
            delivery_cost=250_000,
            delivery_days=2,
            payment_terms="Yetkazib berilgach",
            is_selected=True,
        )
        repos.orders.create(
            order_no="PO-00001",
            request_id=request3.id,
            quote_id=quote_c.id,
            supplier_id=suppliers[1].id,
            order_date=TODAY - timedelta(days=1),
            total_amount=quote_c.total_value(request3.quantity),
            status=OrderStatus.SENT.value,
        )

        # -- expenses: normal / warning / over budget ------------------------ #
        expenses = [
            # project 1 — healthy
            (
                project1.id,
                ExpenseCategory.MATERIAL.value,
                items1[2].id,
                suppliers[1].id,
                28_400_000,
                -20,
                ExpenseStatus.PAID.value,
                "Gipskarton partiyasi",
            ),
            (
                project1.id,
                ExpenseCategory.LABOR.value,
                items1[4].id,
                contractors[0].id,
                12_600_000,
                -14,
                ExpenseStatus.PAID.value,
                "Elektrmontaj brigadasi",
            ),
            # project 1 — pending approval (yellow)
            (
                project1.id,
                ExpenseCategory.MATERIAL.value,
                items1[3].id,
                suppliers[1].id,
                14_390_000,
                -2,
                ExpenseStatus.PENDING.value,
                "Laminat oldindan to'lov",
            ),
            # project 1 — over budget on a single estimate line (red)
            (
                project1.id,
                ExpenseCategory.SUBCONTRACT.value,
                items1[5].id,
                contractors[1].id,
                9_800_000,
                -6,
                ExpenseStatus.APPROVED.value,
                "Rozetka montaji, narx oshdi",
            ),
            # project 2
            (
                project2.id,
                ExpenseCategory.MATERIAL.value,
                items2[1].id,
                suppliers[0].id,
                612_000_000,
                -35,
                ExpenseStatus.PAID.value,
                "Armatura yetkazib berish",
            ),
            (
                project2.id,
                ExpenseCategory.EQUIPMENT.value,
                None,
                contractors[0].id,
                86_000_000,
                -25,
                ExpenseStatus.PAID.value,
                "Kran ijarasi",
            ),
            (
                project2.id,
                ExpenseCategory.MATERIAL.value,
                items2[2].id,
                suppliers[0].id,
                418_000_000,
                -12,
                ExpenseStatus.APPROVED.value,
                "Beton yetkazib berish",
            ),
            (
                project2.id,
                ExpenseCategory.OVERHEAD.value,
                None,
                None,
                34_500_000,
                -4,
                ExpenseStatus.PENDING.value,
                "Obyekt umumiy xarajatlari",
            ),
        ]
        for pid, category, item_id, cp_id, amount, days, status, note in expenses:
            expense = repos.expenses.create(
                project_id=pid,
                category=category,
                estimate_item_id=item_id,
                counterparty_id=cp_id,
                amount=amount,
                pay_date=TODAY + timedelta(days=days),
                method=PaymentMethod.TRANSFER.value,
                invoice_no=f"INV-{abs(days):03d}",
                note=note,
                status=status,
                created_by_id=estimator.id,
                approved_by_id=(
                    manager.id
                    if status in (ExpenseStatus.APPROVED.value, ExpenseStatus.PAID.value)
                    else None
                ),
            )
            if status == ExpenseStatus.PAID.value:
                repos.payments.create(
                    expense_id=expense.id,
                    amount=amount,
                    pay_date=TODAY + timedelta(days=days),
                    method=PaymentMethod.TRANSFER.value,
                    created_by_id=manager.id,
                    note="Demo to'lov",
                )

        # -- audit trail so the activity panels are not empty ---------------- #
        trail = [
            (project1.id, manager, Action.CREATE, "Project", project1.id, project1.name, -56),
            (
                project1.id,
                estimator,
                Action.CREATE,
                "EstimateVersion",
                version1.id,
                "smeta v1 tayyorlandi",
                -50,
            ),
            (
                project1.id,
                manager,
                Action.APPROVE,
                "EstimateVersion",
                version1.id,
                "smeta v1 tasdiqlandi",
                -48,
            ),
            (
                project1.id,
                storekeeper,
                Action.STOCK,
                "WarehouseTransaction",
                None,
                "Gipskarton chiqimi: 205 m²",
                -14,
            ),
            (
                project1.id,
                manager,
                Action.APPROVE,
                "Expense",
                None,
                "Rozetka montaji tasdiqlandi",
                -6,
            ),
            (
                project1.id,
                storekeeper,
                Action.CREATE,
                "PurchaseRequest",
                request3.id,
                f"{request3.number} {request3.title}",
                -2,
            ),
            (project2.id, manager, Action.CREATE, "Project", project2.id, project2.name, -121),
            (
                project2.id,
                estimator,
                Action.CREATE,
                "EstimateVersion",
                version2.id,
                "smeta v1 tasdiqlashga yuborildi",
                -100,
            ),
            (
                project2.id,
                storekeeper,
                Action.STOCK,
                "WarehouseTransaction",
                None,
                "Armatura chiqimi: 9.5 tonna",
                -20,
            ),
            (
                project2.id,
                manager,
                Action.PAYMENT,
                "Expense",
                None,
                "Armatura uchun to'lov: 612 000 000 so'm",
                -35,
            ),
            (
                project2.id,
                manager,
                Action.CREATE,
                "PurchaseRequest",
                request2.id,
                f"{request2.number} {request2.title}",
                -8,
            ),
        ]
        for pid, actor, action, entity, entity_id, description, days in trail:
            entry = audit_service.log(
                session,
                user=actor,
                action=action,
                entity_type=entity,
                entity_id=entity_id,
                project_id=pid,
                description=description,
            )
            entry.ts = datetime.now() + timedelta(days=days)

        session.flush()
        del admin, contractors, request1

    # Recalculate cached actual costs for both demo projects.
    from app.services import estimate_service, stage_service

    with session_scope() as session:
        for project in Repositories(session).projects.list():
            estimate_service.recalc_item_actuals(session, project.id)
            stage_service.refresh_delays(session, project.id)
