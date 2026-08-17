"""Minimal in-process translation catalogue (Uzbek / English).

Usage::

    from app.utils.i18n import tr, i18n
    label.setText(tr("projects"))

Switching the language emits :attr:`I18N.language_changed`; the main window
listens to it and rebuilds its pages, which keeps per-widget retranslation code
out of the UI layer.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.config import DEFAULT_LANGUAGE

# --------------------------------------------------------------------------- #
# Catalogue
# --------------------------------------------------------------------------- #

CATALOG: dict[str, dict[str, str]] = {
    # -- generic ----------------------------------------------------------- #
    "app_title": {"uz": "BuildControl", "en": "BuildControl"},
    "app_subtitle": {
        "uz": "Qurilish smetasi va xarajat nazorati",
        "en": "Construction estimate & cost control",
    },
    "ok": {"uz": "OK", "en": "OK"},
    "save": {"uz": "Saqlash", "en": "Save"},
    "cancel": {"uz": "Bekor qilish", "en": "Cancel"},
    "close": {"uz": "Yopish", "en": "Close"},
    "add": {"uz": "Qo'shish", "en": "Add"},
    "edit": {"uz": "Tahrirlash", "en": "Edit"},
    "delete": {"uz": "O'chirish", "en": "Delete"},
    "archive": {"uz": "Arxivlash", "en": "Archive"},
    "restore": {"uz": "Tiklash", "en": "Restore"},
    "refresh": {"uz": "Yangilash", "en": "Refresh"},
    "search": {"uz": "Qidiruv", "en": "Search"},
    "search_ph": {"uz": "Qidirish...", "en": "Search..."},
    "filter": {"uz": "Filtr", "en": "Filter"},
    "all": {"uz": "Barchasi", "en": "All"},
    "none": {"uz": "Yo'q", "en": "None"},
    "yes": {"uz": "Ha", "en": "Yes"},
    "no": {"uz": "Yo'q", "en": "No"},
    "open": {"uz": "Ochish", "en": "Open"},
    "export_excel": {"uz": "Excel'ga eksport", "en": "Export to Excel"},
    "import_excel": {"uz": "Excel'dan import", "en": "Import from Excel"},
    "export_pdf": {"uz": "PDF yaratish", "en": "Create PDF"},
    "print": {"uz": "Chop etish", "en": "Print"},
    "total": {"uz": "Jami", "en": "Total"},
    "from": {"uz": "dan", "en": "from"},
    "to": {"uz": "gacha", "en": "to"},
    "date": {"uz": "Sana", "en": "Date"},
    "date_from": {"uz": "Boshlanish sanasi", "en": "Date from"},
    "date_to": {"uz": "Tugash sanasi", "en": "Date to"},
    "status": {"uz": "Holat", "en": "Status"},
    "category": {"uz": "Kategoriya", "en": "Category"},
    "note": {"uz": "Izoh", "en": "Note"},
    "notes": {"uz": "Izohlar", "en": "Notes"},
    "name": {"uz": "Nomi", "en": "Name"},
    "code": {"uz": "Kod", "en": "Code"},
    "unit": {"uz": "O'lchov birligi", "en": "Unit"},
    "quantity": {"uz": "Miqdor", "en": "Quantity"},
    "price": {"uz": "Narx", "en": "Price"},
    "amount": {"uz": "Summa", "en": "Amount"},
    "responsible": {"uz": "Mas'ul shaxs", "en": "Responsible"},
    "actions": {"uz": "Amallar", "en": "Actions"},
    "page": {"uz": "Sahifa", "en": "Page"},
    "rows": {"uz": "qator", "en": "rows"},
    "of": {"uz": "/", "en": "of"},
    "confirm": {"uz": "Tasdiqlash", "en": "Confirm"},
    "confirm_question": {"uz": "Amalni tasdiqlaysizmi?", "en": "Confirm this action?"},
    "error": {"uz": "Xatolik", "en": "Error"},
    "warning": {"uz": "Ogohlantirish", "en": "Warning"},
    "success": {"uz": "Muvaffaqiyatli", "en": "Success"},
    "info": {"uz": "Ma'lumot", "en": "Information"},
    "saved": {"uz": "Saqlandi", "en": "Saved"},
    "deleted": {"uz": "O'chirildi", "en": "Deleted"},
    "no_data": {"uz": "Ma'lumot topilmadi", "en": "No data"},
    "required_field": {"uz": "Bu maydon to'ldirilishi shart", "en": "This field is required"},
    "select_row_first": {"uz": "Avval qatorni tanlang", "en": "Select a row first"},
    "permission_denied": {
        "uz": "Sizda bu amal uchun ruxsat yo'q",
        "en": "You do not have permission for this action",
    },
    "language": {"uz": "Til", "en": "Language"},
    "logout": {"uz": "Chiqish", "en": "Log out"},
    "show_archived": {"uz": "Arxivdagilar", "en": "Archived"},
    "attachments": {"uz": "Biriktirilgan fayllar", "en": "Attachments"},
    "browse": {"uz": "Tanlash", "en": "Browse"},
    "apply": {"uz": "Qo'llash", "en": "Apply"},
    "reset": {"uz": "Tozalash", "en": "Reset"},
    "created_at": {"uz": "Yaratilgan", "en": "Created"},
    "author": {"uz": "Muallif", "en": "Author"},
    "type": {"uz": "Turi", "en": "Type"},
    "percent_done": {"uz": "Bajarilish, %", "en": "Progress, %"},
    # -- auth --------------------------------------------------------------- #
    "login": {"uz": "Kirish", "en": "Sign in"},
    "username": {"uz": "Foydalanuvchi nomi", "en": "Username"},
    "password": {"uz": "Parol", "en": "Password"},
    "password_repeat": {"uz": "Parolni takrorlang", "en": "Repeat password"},
    "remember_me": {"uz": "Meni eslab qol", "en": "Remember me"},
    "login_failed": {
        "uz": "Foydalanuvchi nomi yoki parol noto'g'ri",
        "en": "Invalid username or password",
    },
    "user_inactive": {"uz": "Foydalanuvchi bloklangan", "en": "User is deactivated"},
    "first_admin_title": {"uz": "Administrator yaratish", "en": "Create administrator"},
    "first_admin_hint": {
        "uz": "Birinchi ishga tushirish. Administrator hisobini yarating.",
        "en": "First run. Create the administrator account.",
    },
    "full_name": {"uz": "F.I.Sh.", "en": "Full name"},
    "passwords_mismatch": {"uz": "Parollar mos kelmadi", "en": "Passwords do not match"},
    "password_too_short": {
        "uz": "Parol kamida 6 ta belgidan iborat bo'lsin",
        "en": "Password must be at least 6 characters",
    },
    "create": {"uz": "Yaratish", "en": "Create"},
    "username_taken": {
        "uz": "Bu foydalanuvchi nomi band",
        "en": "This username is already taken",
    },
    "demo_hint": {
        "uz": "Demo kirish: admin / admin123",
        "en": "Demo login: admin / admin123",
    },
    # -- navigation --------------------------------------------------------- #
    "nav_projects": {"uz": "Loyihalar", "en": "Projects"},
    "nav_estimates": {"uz": "Smetalar", "en": "Estimates"},
    "nav_purchases": {"uz": "Xaridlar", "en": "Purchases"},
    "nav_warehouse": {"uz": "Ombor", "en": "Warehouse"},
    "nav_materials": {"uz": "Materiallar", "en": "Materials"},
    "nav_counterparties": {"uz": "Kontragentlar", "en": "Counterparties"},
    "nav_expenses": {"uz": "Xarajatlar", "en": "Expenses"},
    "nav_reports": {"uz": "Hisobotlar", "en": "Reports"},
    "nav_audit": {"uz": "Audit jurnali", "en": "Audit log"},
    "nav_settings": {"uz": "Sozlamalar", "en": "Settings"},
    "collapse_menu": {"uz": "Menyuni yig'ish", "en": "Collapse menu"},
    # -- projects ----------------------------------------------------------- #
    "projects": {"uz": "Loyihalar", "en": "Projects"},
    "project": {"uz": "Loyiha", "en": "Project"},
    "new_project": {"uz": "Yangi loyiha", "en": "New project"},
    "project_name": {"uz": "Loyiha nomi", "en": "Project name"},
    "client": {"uz": "Mijoz", "en": "Client"},
    "address": {"uz": "Obyekt manzili", "en": "Site address"},
    "project_type": {"uz": "Loyiha turi", "en": "Project type"},
    "start_date": {"uz": "Boshlanish", "en": "Start"},
    "end_date": {"uz": "Yakunlanish", "en": "Finish"},
    "manager": {"uz": "Loyiha rahbari", "en": "Project manager"},
    "planned_budget": {"uz": "Rejalashtirilgan budjet", "en": "Planned budget"},
    "open_project": {"uz": "Loyihani ochish", "en": "Open project"},
    "back_to_projects": {"uz": "Loyihalar ro'yxatiga", "en": "Back to projects"},
    "archive_project_q": {
        "uz": "Loyiha arxivlansinmi? Ma'lumotlar o'chirilmaydi.",
        "en": "Archive this project? No data will be removed.",
    },
    # -- project tabs ------------------------------------------------------- #
    "tab_overview": {"uz": "Umumiy holat", "en": "Overview"},
    "tab_estimate": {"uz": "Smeta", "en": "Estimate"},
    "tab_purchases": {"uz": "Xaridlar", "en": "Purchases"},
    "tab_warehouse": {"uz": "Ombor", "en": "Warehouse"},
    "tab_stages": {"uz": "Ish bosqichlari", "en": "Work stages"},
    "tab_contractors": {"uz": "Pudratchilar", "en": "Contractors"},
    "tab_expenses": {"uz": "Xarajatlar", "en": "Expenses"},
    "tab_documents": {"uz": "Hujjatlar", "en": "Documents"},
    "tab_reports": {"uz": "Hisobotlar", "en": "Reports"},
    "tab_activity": {"uz": "Faollik tarixi", "en": "Activity"},
    # -- overview ----------------------------------------------------------- #
    "passport": {"uz": "Loyiha pasporti", "en": "Project passport"},
    "budget": {"uz": "Budjet", "en": "Budget"},
    "committed_cost": {"uz": "Tasdiqlangan xarajat", "en": "Committed cost"},
    "actual_cost": {"uz": "Amaldagi xarajat", "en": "Actual cost"},
    "remaining_funds": {"uz": "Qolgan mablag'", "en": "Remaining funds"},
    "delayed_stages": {"uz": "Kechikayotgan bosqichlar", "en": "Delayed stages"},
    "pending_purchases": {"uz": "Tasdiq kutayotgan xaridlar", "en": "Purchases awaiting approval"},
    "recent_activity": {"uz": "So'nggi faoliyat", "en": "Recent activity"},
    "budget_usage": {"uz": "Budjet sarfi", "en": "Budget usage"},
    "over_budget": {"uz": "Budjetdan oshgan", "en": "Over budget"},
    "estimate_total": {"uz": "Smeta jami", "en": "Estimate total"},
    "stages_summary": {"uz": "Bosqichlar", "en": "Stages"},
    # -- estimate ----------------------------------------------------------- #
    "estimate": {"uz": "Smeta", "en": "Estimate"},
    "estimate_version": {"uz": "Versiya", "en": "Version"},
    "new_version": {"uz": "Yangi versiya", "en": "New version"},
    "add_section": {"uz": "Bo'lim qo'shish", "en": "Add section"},
    "add_subsection": {"uz": "Kichik bo'lim", "en": "Add sub-section"},
    "add_item": {"uz": "Band qo'shish", "en": "Add item"},
    "section": {"uz": "Bo'lim", "en": "Section"},
    "item": {"uz": "Band", "en": "Item"},
    "plan_unit_price": {"uz": "Reja birlik narxi", "en": "Plan unit price"},
    "plan_total": {"uz": "Reja jami", "en": "Plan total"},
    "actual_unit_price": {"uz": "Amaldagi birlik narxi", "en": "Actual unit price"},
    "actual_total": {"uz": "Amaldagi jami", "en": "Actual total"},
    "variance": {"uz": "Farq", "en": "Variance"},
    "variance_percent": {"uz": "Farq, %", "en": "Variance, %"},
    "submit_for_approval": {"uz": "Tasdiqlashga yuborish", "en": "Submit for approval"},
    "approve": {"uz": "Tasdiqlash", "en": "Approve"},
    "reject": {"uz": "Rad etish", "en": "Reject"},
    "send_to_revision": {"uz": "Qayta ko'rib chiqishga", "en": "Send to revision"},
    "estimate_locked": {
        "uz": "Tasdiqlangan smeta tahrirlanmaydi. Yangi versiya yarating.",
        "en": "An approved estimate is read-only. Create a new version.",
    },
    "compare_versions": {"uz": "Versiyalarni taqqoslash", "en": "Compare versions"},
    "version_diff": {"uz": "Versiyalar farqi", "en": "Version difference"},
    "recalculate": {"uz": "Qayta hisoblash", "en": "Recalculate"},
    "move_up": {"uz": "Yuqoriga", "en": "Move up"},
    "move_down": {"uz": "Pastga", "en": "Move down"},
    "drag_hint": {
        "uz": "Bandlarni sudrab tartiblash mumkin",
        "en": "Drag and drop to reorder",
    },
    # -- purchases ---------------------------------------------------------- #
    "purchase_request": {"uz": "Xarid talabi", "en": "Purchase request"},
    "new_request": {"uz": "Yangi talab", "en": "New request"},
    "estimate_item": {"uz": "Smeta bandi", "en": "Estimate item"},
    "off_estimate": {"uz": "Smetadan tashqari xarajat", "en": "Off-estimate purchase"},
    "product_service": {"uz": "Mahsulot / xizmat", "en": "Product / service"},
    "est_price": {"uz": "Taxminiy narx", "en": "Estimated price"},
    "needed_date": {"uz": "Kerak bo'ladigan sana", "en": "Needed by"},
    "delivery_address": {"uz": "Yetkazish manzili", "en": "Delivery address"},
    "quotes": {"uz": "Yetkazib beruvchi takliflari", "en": "Supplier quotes"},
    "add_quote": {"uz": "Taklif qo'shish", "en": "Add quote"},
    "supplier": {"uz": "Yetkazib beruvchi", "en": "Supplier"},
    "contact": {"uz": "Kontakt", "en": "Contact"},
    "unit_price": {"uz": "Birlik narxi", "en": "Unit price"},
    "delivery_cost": {"uz": "Yetkazish narxi", "en": "Delivery cost"},
    "delivery_days": {"uz": "Muddat, kun", "en": "Lead time, days"},
    "payment_terms": {"uz": "To'lov sharti", "en": "Payment terms"},
    "quote_file": {"uz": "Taklif fayli", "en": "Quote file"},
    "total_value": {"uz": "Umumiy qiymat", "en": "Total value"},
    "select_quote": {"uz": "Taklifni tanlash", "en": "Select quote"},
    "best_offer": {"uz": "Eng yaxshi taklif", "en": "Best offer"},
    "best_price": {"uz": "Eng arzon", "en": "Cheapest"},
    "fastest": {"uz": "Eng tez", "en": "Fastest"},
    "create_order": {"uz": "Buyurtma yaratish", "en": "Create order"},
    "purchase_order": {"uz": "Xarid buyurtmasi", "en": "Purchase order"},
    "order_no": {"uz": "Buyurtma raqami", "en": "Order no."},
    "no_quote_selected": {"uz": "Taklif tanlanmagan", "en": "No quote selected"},
    "estimate_item_required": {
        "uz": "Smeta bandini tanlang yoki 'smetadan tashqari' belgisini qo'ying",
        "en": "Pick an estimate item or mark the request as off-estimate",
    },
    # -- warehouse ---------------------------------------------------------- #
    "materials": {"uz": "Materiallar katalogi", "en": "Material catalogue"},
    "material": {"uz": "Material", "en": "Material"},
    "sku": {"uz": "SKU / kod", "en": "SKU / code"},
    "min_stock": {"uz": "Minimal qoldiq", "en": "Minimum stock"},
    "standard_price": {"uz": "Standart narx", "en": "Standard price"},
    "stock": {"uz": "Qoldiq", "en": "Stock"},
    "stock_value": {"uz": "Qoldiq qiymati", "en": "Stock value"},
    "transactions": {"uz": "Ombor harakati", "en": "Stock movements"},
    "new_transaction": {"uz": "Yangi harakat", "en": "New movement"},
    "low_stock_warning": {"uz": "Minimal qoldiqdan kam", "en": "Below minimum stock"},
    "low_stock_items": {"uz": "Kam qolgan materiallar", "en": "Low stock materials"},
    "document": {"uz": "Hujjat / foto", "en": "Document / photo"},
    "not_enough_stock": {"uz": "Omborda yetarli qoldiq yo'q", "en": "Not enough stock"},
    "quantity_positive": {
        "uz": "Miqdor noldan katta bo'lishi kerak",
        "en": "Quantity must be greater than zero",
    },
    "sku_exists": {
        "uz": "Bunday SKU allaqachon mavjud",
        "en": "This SKU already exists",
    },
    # -- stages ------------------------------------------------------------- #
    "stages": {"uz": "Ish bosqichlari", "en": "Work stages"},
    "stage": {"uz": "Bosqich", "en": "Stage"},
    "new_stage": {"uz": "Yangi bosqich", "en": "New stage"},
    "plan_start": {"uz": "Reja boshlanish", "en": "Plan start"},
    "plan_end": {"uz": "Reja yakun", "en": "Plan finish"},
    "actual_start": {"uz": "Amaldagi boshlanish", "en": "Actual start"},
    "actual_end": {"uz": "Amaldagi yakun", "en": "Actual finish"},
    "dependencies": {"uz": "Bog'liqliklar", "en": "Dependencies"},
    "timeline": {"uz": "Vaqt jadvali", "en": "Timeline"},
    "site_log": {"uz": "Kundalik nazorat jurnali", "en": "Daily site log"},
    "new_log": {"uz": "Yangi yozuv", "en": "New entry"},
    "work_done": {"uz": "Bajarilgan ish", "en": "Work done"},
    "workers_count": {"uz": "Ishchilar soni", "en": "Workers"},
    "issue": {"uz": "Muammo", "en": "Issue"},
    "photo": {"uz": "Foto", "en": "Photo"},
    "linked_section": {"uz": "Bog'liq smeta bo'limi", "en": "Linked estimate section"},
    # -- counterparties ----------------------------------------------------- #
    "counterparties": {"uz": "Kontragentlar", "en": "Counterparties"},
    "contractors": {"uz": "Pudratchilar", "en": "Contractors"},
    "suppliers": {"uz": "Yetkazib beruvchilar", "en": "Suppliers"},
    "new_counterparty": {"uz": "Yangi kontragent", "en": "New counterparty"},
    "tin": {"uz": "STIR", "en": "TIN"},
    "phone": {"uz": "Telefon", "en": "Phone"},
    "email": {"uz": "Email", "en": "Email"},
    "bank_details": {"uz": "Bank rekvizitlari", "en": "Bank details"},
    "rating": {"uz": "Reyting", "en": "Rating"},
    "contract_amount": {"uz": "Shartnoma summasi", "en": "Contract amount"},
    "paid_amount": {"uz": "To'langan summa", "en": "Paid amount"},
    "completed_work": {"uz": "Bajarilgan ish", "en": "Completed work"},
    "delay_days": {"uz": "Kechikish, kun", "en": "Delay, days"},
    "quality_score": {"uz": "Sifat bahosi", "en": "Quality score"},
    "disputes": {"uz": "Nizolar soni", "en": "Disputes"},
    "recalc_rating": {"uz": "Reytingni hisoblash", "en": "Recalculate rating"},
    # -- expenses ----------------------------------------------------------- #
    "expenses": {"uz": "Xarajatlar", "en": "Expenses"},
    "new_expense": {"uz": "Yangi xarajat", "en": "New expense"},
    "counterparty": {"uz": "Kontragent", "en": "Counterparty"},
    "pay_date": {"uz": "To'lov sanasi", "en": "Payment date"},
    "method": {"uz": "To'lov usuli", "en": "Payment method"},
    "invoice_no": {"uz": "Chek / faktura", "en": "Invoice no."},
    "mark_paid": {"uz": "To'langan deb belgilash", "en": "Mark as paid"},
    "payments": {"uz": "To'lovlar", "en": "Payments"},
    "add_payment": {"uz": "To'lov qo'shish", "en": "Add payment"},
    "approve_expense_q": {"uz": "Xarajat tasdiqlansinmi?", "en": "Approve this expense?"},
    "budget_exceed_warning": {
        "uz": "Diqqat: bu xarajat loyiha budjetidan oshib ketadi.",
        "en": "Warning: this expense pushes the project over budget.",
    },
    # -- reports ------------------------------------------------------------ #
    "reports": {"uz": "Hisobotlar", "en": "Reports"},
    "report_type": {"uz": "Hisobot turi", "en": "Report type"},
    "generate": {"uz": "Yaratish", "en": "Generate"},
    "rep_estimate": {"uz": "Loyiha smetasi", "en": "Project estimate"},
    "rep_plan_fact": {"uz": "Reja-fakt xarajat", "en": "Plan vs actual"},
    "rep_overrun": {"uz": "Budjet oshishi", "en": "Budget overrun"},
    "rep_purchases": {"uz": "Xaridlar reyestri", "en": "Purchase register"},
    "rep_quotes": {"uz": "Yetkazib beruvchilar taqqoslanishi", "en": "Supplier comparison"},
    "rep_stock": {"uz": "Ombor qoldig'i", "en": "Stock balance"},
    "rep_movements": {"uz": "Materiallar harakati", "en": "Material movements"},
    "rep_stages": {"uz": "Bosqichlar holati", "en": "Stage status"},
    "rep_delays": {"uz": "Kechikayotgan ishlar", "en": "Delayed works"},
    "rep_contractors": {"uz": "Pudratchi samaradorligi", "en": "Contractor performance"},
    "rep_payments": {"uz": "Loyiha to'lovlari", "en": "Project payments"},
    "report_saved": {"uz": "Hisobot saqlandi", "en": "Report saved"},
    "open_folder": {"uz": "Papkani ochish", "en": "Open folder"},
    # -- settings ----------------------------------------------------------- #
    "settings": {"uz": "Sozlamalar", "en": "Settings"},
    "company": {"uz": "Kompaniya", "en": "Company"},
    "company_name": {"uz": "Kompaniya nomi", "en": "Company name"},
    "logo": {"uz": "Logo", "en": "Logo"},
    "requisites": {"uz": "Rekvizitlar", "en": "Requisites"},
    "users": {"uz": "Foydalanuvchilar", "en": "Users"},
    "new_user": {"uz": "Yangi foydalanuvchi", "en": "New user"},
    "role": {"uz": "Rol", "en": "Role"},
    "roles": {"uz": "Rollar va ruxsatlar", "en": "Roles & permissions"},
    "is_active": {"uz": "Faol", "en": "Active"},
    "reset_password": {"uz": "Parolni almashtirish", "en": "Reset password"},
    "dictionaries": {"uz": "Ma'lumotnomalar", "en": "Dictionaries"},
    "backup": {"uz": "Zaxira nusxa", "en": "Backup"},
    "create_backup": {"uz": "Zaxira yaratish", "en": "Create backup"},
    "restore_backup": {"uz": "Zaxiradan tiklash", "en": "Restore from backup"},
    "restore_warning": {
        "uz": "Tiklashdan so'ng dastur qayta ishga tushirilishi kerak. Davom etilsinmi?",
        "en": "The application must be restarted after restore. Continue?",
    },
    "export_data": {"uz": "Ma'lumotlarni eksport", "en": "Export data"},
    "backup_created": {"uz": "Zaxira nusxa yaratildi", "en": "Backup created"},
    "restart_required": {"uz": "Dasturni qayta ishga tushiring", "en": "Please restart the app"},
    # -- synchronisation ---------------------------------------------------- #
    "sync": {"uz": "Sinxronizatsiya", "en": "Synchronisation"},
    "sync_intro": {
        "uz": (
            "Har bir kompyuterda o'z bazasi saqlanadi va internetsiz ham ishlaydi. "
            "O'zgarishlar umumiy jurnal orqali almashadi."
        ),
        "en": (
            "Every computer keeps its own database and works offline. Changes are "
            "exchanged through a shared change log."
        ),
    },
    "sync_backend": {"uz": "Ulanish turi", "en": "Backend"},
    "mqtt_broker": {"uz": "Broker", "en": "Broker"},
    "mqtt_host": {"uz": "Broker manzili", "en": "Broker host"},
    "mqtt_port": {"uz": "Port", "en": "Port"},
    "mqtt_tls": {"uz": "TLS (shifrlangan ulanish)", "en": "TLS (encrypted connection)"},
    "mqtt_user": {"uz": "Foydalanuvchi (ixtiyoriy)", "en": "Username (optional)"},
    "mqtt_password": {"uz": "Parol (ixtiyoriy)", "en": "Password (optional)"},
    "mqtt_prefix": {"uz": "Mavzu prefiksi", "en": "Topic prefix"},
    "mqtt_custom": {"uz": "Boshqa (qo'lda kiritish)", "en": "Other (manual)"},
    "sync_passphrase": {"uz": "Shifrlash paroli", "en": "Encryption passphrase"},
    "sync_passphrase_hint": {
        "uz": (
            "Bo'sh qoldirilsa ma'lumot ochiq yuboriladi. Ommaviy brokerda parol qo'yish "
            "tavsiya etiladi — barcha kompyuterlarda bir xil bo'lishi shart."
        ),
        "en": (
            "Left empty the data travels in the clear. On a public broker set a passphrase "
            "— it must be identical on every installation."
        ),
    },
    "mqtt_warning": {
        "uz": (
            "Diqqat: ommaviy broker hammaga ochiq. Ish maydoni kalitini uzun va tasodifiy "
            "qiling hamda shifrlash parolini yoqing."
        ),
        "en": (
            "Warning: a public broker is open to everyone. Use a long random workspace key "
            "and enable the encryption passphrase."
        ),
    },
    "mqtt_setup_steps": {
        "uz": (
            "1. Ro'yxatdan o'tish shart emas — broker bepul va ochiq.\n"
            "2. Barcha kompyuterlarda bir xil broker, ish maydoni kaliti va shifrlash "
            "parolini kiriting.\n"
            "3. Birinchi kompyuterda 'Hamma ma'lumotni yuklash' tugmasini bosing.\n"
            "4. Har bir yozuv alohida mavzuda retained saqlanadi, shuning uchun yangi "
            "qurilma ulanishi bilan to'liq nusxani oladi."
        ),
        "en": (
            "1. No sign-up needed — the broker is free and open.\n"
            "2. Enter the same broker, workspace key and passphrase everywhere.\n"
            "3. Press 'Upload everything' on the first computer.\n"
            "4. Each row is retained on its own topic, so a new device receives the whole "
            "snapshot the moment it connects."
        ),
    },
    "sync_url": {"uz": "Supabase URL", "en": "Supabase URL"},
    "sync_api_key": {"uz": "API kaliti (anon)", "en": "API key (anon)"},
    "sync_folder": {"uz": "Umumiy papka", "en": "Shared folder"},
    "sync_tenant": {"uz": "Ish maydoni kaliti", "en": "Workspace key"},
    "sync_tenant_hint": {
        "uz": "Bir xil kalitdagi kompyuterlar ma'lumot almashadi",
        "en": "Installations sharing this key exchange data",
    },
    "sync_auto": {"uz": "Avtomatik sinxronizatsiya", "en": "Automatic synchronisation"},
    "sync_interval": {"uz": "Interval, soniya", "en": "Interval, seconds"},
    "sync_device_name": {"uz": "Ushbu kompyuter nomi", "en": "This computer's name"},
    "sync_device_id": {"uz": "Qurilma ID", "en": "Device ID"},
    "sync_now": {"uz": "Hozir sinxronlash", "en": "Synchronise now"},
    "sync_test": {"uz": "Ulanishni tekshirish", "en": "Test connection"},
    "sync_status": {"uz": "Holat", "en": "Status"},
    "sync_pending": {"uz": "Yuborilmagan o'zgarishlar", "en": "Pending changes"},
    "sync_last_push": {"uz": "Oxirgi yuborish", "en": "Last push"},
    "sync_last_pull": {"uz": "Oxirgi qabul", "en": "Last pull"},
    "sync_cursor": {"uz": "Jurnal pozitsiyasi", "en": "Log position"},
    "sync_totals": {"uz": "Jami yuborilgan / qabul qilingan", "en": "Total sent / received"},
    "sync_upload_all": {"uz": "Hamma ma'lumotni yuklash", "en": "Upload everything"},
    "sync_upload_all_q": {
        "uz": "Ushbu kompyuterdagi barcha yozuvlar serverga yuboriladi. Davom etilsinmi?",
        "en": "Every row on this computer will be sent to the server. Continue?",
    },
    "sync_reset_cursor": {"uz": "Jurnalni boshidan o'qish", "en": "Replay whole log"},
    "sync_reset_q": {
        "uz": "Umumiy jurnal boshidan qayta o'qiladi. Davom etilsinmi?",
        "en": "The shared log will be replayed from the beginning. Continue?",
    },
    "sync_running": {"uz": "Sinxronlanmoqda...", "en": "Synchronising..."},
    "sync_ok": {"uz": "Sinxronizatsiya yakunlandi", "en": "Synchronisation finished"},
    "sync_failed": {"uz": "Sinxronizatsiya xatosi", "en": "Synchronisation failed"},
    "sync_disabled": {"uz": "O'chirilgan", "en": "Disabled"},
    "sync_never": {"uz": "Hech qachon", "en": "Never"},
    "sync_setup_title": {"uz": "Supabase'ni sozlash (bepul)", "en": "Supabase setup (free)"},
    "sync_setup_steps": {
        "uz": (
            "1. supabase.com — bepul ro'yxatdan o'ting va yangi loyiha yarating.\n"
            "2. SQL Editor'ni oching va quyidagi so'rovni bajaring.\n"
            "3. Settings → API bo'limidan Project URL va anon public kalitini nusxalab, "
            "yuqoridagi maydonlarga qo'ying.\n"
            "4. Har bir kompyuterda bir xil URL, kalit va ish maydoni kalitini kiriting."
        ),
        "en": (
            "1. Sign up free at supabase.com and create a project.\n"
            "2. Open the SQL Editor and run the query below.\n"
            "3. Copy Project URL and the anon public key from Settings → API into the "
            "fields above.\n"
            "4. Enter the same URL, key and workspace key on every computer."
        ),
    },
    "copy_sql": {"uz": "SQL nusxalash", "en": "Copy SQL"},
    "copied": {"uz": "Nusxalandi", "en": "Copied"},
    # -- audit -------------------------------------------------------------- #
    "audit": {"uz": "Audit jurnali", "en": "Audit log"},
    "action": {"uz": "Amal", "en": "Action"},
    "user": {"uz": "Foydalanuvchi", "en": "User"},
    "entity": {"uz": "Obyekt", "en": "Entity"},
    "description": {"uz": "Tavsif", "en": "Description"},
    # -- enums -------------------------------------------------------------- #
    "enum.role.admin": {"uz": "Administrator", "en": "Administrator"},
    "enum.role.manager": {"uz": "Loyiha rahbari", "en": "Project manager"},
    "enum.role.estimator": {"uz": "Smetachi", "en": "Estimator"},
    "enum.role.storekeeper": {"uz": "Omborchi", "en": "Storekeeper"},
    "enum.role.viewer": {"uz": "Kuzatuvchi", "en": "Viewer"},
    "enum.project_type.new_build": {"uz": "Yangi qurilish", "en": "New build"},
    "enum.project_type.renovation": {"uz": "Ta'mirlash", "en": "Renovation"},
    "enum.project_type.interior": {"uz": "Interyer", "en": "Interior"},
    "enum.project_type.facade": {"uz": "Fasad", "en": "Facade"},
    "enum.project_type.other": {"uz": "Boshqa", "en": "Other"},
    "enum.project_status.planned": {"uz": "Rejalashtirilgan", "en": "Planned"},
    "enum.project_status.active": {"uz": "Faol", "en": "Active"},
    "enum.project_status.suspended": {"uz": "To'xtatilgan", "en": "Suspended"},
    "enum.project_status.completed": {"uz": "Yakunlangan", "en": "Completed"},
    "enum.project_status.archived": {"uz": "Arxiv", "en": "Archived"},
    "enum.estimate_status.draft": {"uz": "Qoralama", "en": "Draft"},
    "enum.estimate_status.submitted": {"uz": "Tasdiqlashga yuborilgan", "en": "Submitted"},
    "enum.estimate_status.approved": {"uz": "Tasdiqlangan", "en": "Approved"},
    "enum.estimate_status.revision": {"uz": "Qayta ko'rib chiqilmoqda", "en": "In revision"},
    "enum.item_status.planned": {"uz": "Rejada", "en": "Planned"},
    "enum.item_status.in_progress": {"uz": "Jarayonda", "en": "In progress"},
    "enum.item_status.needs_purchase": {"uz": "Xarid kerak", "en": "Needs purchase"},
    "enum.item_status.done": {"uz": "Bajarilgan", "en": "Done"},
    "enum.item_status.cancelled": {"uz": "Bekor qilingan", "en": "Cancelled"},
    "enum.unit.piece": {"uz": "dona", "en": "pcs"},
    "enum.unit.kg": {"uz": "kg", "en": "kg"},
    "enum.unit.ton": {"uz": "tonna", "en": "ton"},
    "enum.unit.m": {"uz": "metr", "en": "m"},
    "enum.unit.m2": {"uz": "m²", "en": "m²"},
    "enum.unit.m3": {"uz": "m³", "en": "m³"},
    "enum.unit.hour": {"uz": "soat", "en": "hour"},
    "enum.unit.day": {"uz": "kun", "en": "day"},
    "enum.unit.service": {"uz": "xizmat", "en": "service"},
    "enum.unit.liter": {"uz": "litr", "en": "litre"},
    "enum.unit.set": {"uz": "komplekt", "en": "set"},
    "enum.purchase_status.draft": {"uz": "Qoralama", "en": "Draft"},
    "enum.purchase_status.submitted": {"uz": "Yuborilgan", "en": "Submitted"},
    "enum.purchase_status.approved": {"uz": "Tasdiqlangan", "en": "Approved"},
    "enum.purchase_status.rejected": {"uz": "Rad etilgan", "en": "Rejected"},
    "enum.purchase_status.ordered": {"uz": "Buyurtma berilgan", "en": "Ordered"},
    "enum.purchase_status.partial": {"uz": "Qisman qabul qilingan", "en": "Partially received"},
    "enum.purchase_status.completed": {"uz": "Yakunlangan", "en": "Completed"},
    "enum.order_status.new": {"uz": "Yangi", "en": "New"},
    "enum.order_status.sent": {"uz": "Yuborilgan", "en": "Sent"},
    "enum.order_status.delivered": {"uz": "Yetkazilgan", "en": "Delivered"},
    "enum.order_status.cancelled": {"uz": "Bekor qilingan", "en": "Cancelled"},
    "enum.tx.in": {"uz": "Kirim", "en": "Receipt"},
    "enum.tx.out": {"uz": "Chiqim", "en": "Issue"},
    "enum.tx.return": {"uz": "Qaytarish", "en": "Return"},
    "enum.tx.adjust": {"uz": "Inventarizatsiya", "en": "Adjustment"},
    "enum.tx.loss": {"uz": "Yo'qotish / shikast", "en": "Loss / damage"},
    "enum.stage_status.not_started": {"uz": "Boshlanmagan", "en": "Not started"},
    "enum.stage_status.in_progress": {"uz": "Jarayonda", "en": "In progress"},
    "enum.stage_status.review": {"uz": "Tekshiruvda", "en": "In review"},
    "enum.stage_status.delayed": {"uz": "Kechikkan", "en": "Delayed"},
    "enum.stage_status.done": {"uz": "Yakunlangan", "en": "Completed"},
    "enum.stage_status.blocked": {"uz": "Bloklangan", "en": "Blocked"},
    "enum.cp_kind.supplier": {"uz": "Yetkazib beruvchi", "en": "Supplier"},
    "enum.cp_kind.contractor": {"uz": "Pudratchi", "en": "Contractor"},
    "enum.expense_status.pending": {"uz": "Kutilmoqda", "en": "Pending"},
    "enum.expense_status.approved": {"uz": "Tasdiqlangan", "en": "Approved"},
    "enum.expense_status.paid": {"uz": "To'langan", "en": "Paid"},
    "enum.expense_status.rejected": {"uz": "Rad etilgan", "en": "Rejected"},
    "enum.method.cash": {"uz": "Naqd", "en": "Cash"},
    "enum.method.card": {"uz": "Karta", "en": "Card"},
    "enum.method.transfer": {"uz": "Bank o'tkazmasi", "en": "Bank transfer"},
    "enum.exp_cat.material": {"uz": "Material", "en": "Material"},
    "enum.exp_cat.labor": {"uz": "Ish haqi", "en": "Labor"},
    "enum.exp_cat.equipment": {"uz": "Texnika", "en": "Equipment"},
    "enum.exp_cat.transport": {"uz": "Transport", "en": "Transport"},
    "enum.exp_cat.subcontract": {"uz": "Subpudrat", "en": "Subcontract"},
    "enum.exp_cat.overhead": {"uz": "Umumiy xarajat", "en": "Overhead"},
    "enum.exp_cat.other": {"uz": "Boshqa", "en": "Other"},
    # -- audit actions ------------------------------------------------------ #
    "audit.login": {"uz": "Tizimga kirish", "en": "Sign in"},
    "audit.logout": {"uz": "Tizimdan chiqish", "en": "Sign out"},
    "audit.create": {"uz": "Yaratildi", "en": "Created"},
    "audit.update": {"uz": "O'zgartirildi", "en": "Updated"},
    "audit.delete": {"uz": "O'chirildi", "en": "Deleted"},
    "audit.archive": {"uz": "Arxivlandi", "en": "Archived"},
    "audit.approve": {"uz": "Tasdiqlandi", "en": "Approved"},
    "audit.reject": {"uz": "Rad etildi", "en": "Rejected"},
    "audit.payment": {"uz": "To'lov", "en": "Payment"},
    "audit.stock": {"uz": "Ombor harakati", "en": "Stock movement"},
    "audit.backup": {"uz": "Zaxira", "en": "Backup"},
}


class I18N(QObject):
    """Holds the active language and notifies listeners when it changes."""

    language_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._language: str = DEFAULT_LANGUAGE

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        """Switch the active language and notify listeners."""
        if language not in ("uz", "en") or language == self._language:
            return
        self._language = language
        self.language_changed.emit(language)

    def translate(self, key: str, **kwargs: object) -> str:
        """Return the localized string for ``key`` (falls back to the key)."""
        entry = CATALOG.get(key)
        if entry is None:
            text = key.replace("_", " ").capitalize()
        else:
            text = entry.get(self._language) or entry.get("uz") or key
        return text.format(**kwargs) if kwargs else text


i18n = I18N()


def tr(key: str, **kwargs: object) -> str:
    """Shorthand for :meth:`I18N.translate`."""
    return i18n.translate(key, **kwargs)


def current_language() -> str:
    """Return the active language code."""
    return i18n.language
