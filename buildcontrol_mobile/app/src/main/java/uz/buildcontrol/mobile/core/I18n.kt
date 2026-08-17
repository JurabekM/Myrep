package uz.buildcontrol.mobile.core

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/**
 * In-process translation catalogue (Uzbek / English).
 *
 * The active language is Compose state, so switching it recomposes the whole
 * interface without restarting the activity.
 */
object I18n {

    var language by mutableStateOf("uz")
        private set

    /** Switch the active language; unknown codes are ignored. */
    fun apply(code: String) {
        if (code == "uz" || code == "en") language = code
    }

    fun currencySuffix(): String = if (language == "uz") "so'm" else "UZS"

    fun tr(key: String): String {
        val entry = CATALOG[key] ?: return key.replace('_', ' ').replaceFirstChar { it.uppercase() }
        return (if (language == "uz") entry.first else entry.second)
    }

    fun enum(prefix: String, code: String?): String =
        if (code.isNullOrBlank()) "—" else tr("$prefix.$code")

    private val CATALOG: Map<String, Pair<String, String>> = mapOf(
        // generic
        "app_name" to ("BuildControl" to "BuildControl"),
        "ok" to ("OK" to "OK"),
        "save" to ("Saqlash" to "Save"),
        "cancel" to ("Bekor qilish" to "Cancel"),
        "close" to ("Yopish" to "Close"),
        "add" to ("Qo'shish" to "Add"),
        "edit" to ("Tahrirlash" to "Edit"),
        "delete" to ("O'chirish" to "Delete"),
        "archive" to ("Arxivlash" to "Archive"),
        "refresh" to ("Yangilash" to "Refresh"),
        "search" to ("Qidirish..." to "Search..."),
        "all" to ("Barchasi" to "All"),
        "yes" to ("Ha" to "Yes"),
        "no" to ("Yo'q" to "No"),
        "total" to ("Jami" to "Total"),
        "date" to ("Sana" to "Date"),
        "status" to ("Holat" to "Status"),
        "category" to ("Kategoriya" to "Category"),
        "note" to ("Izoh" to "Note"),
        "name" to ("Nomi" to "Name"),
        "code" to ("Kod" to "Code"),
        "unit" to ("O'lchov birligi" to "Unit"),
        "quantity" to ("Miqdor" to "Quantity"),
        "amount" to ("Summa" to "Amount"),
        "price" to ("Narx" to "Price"),
        "responsible" to ("Mas'ul" to "Responsible"),
        "no_data" to ("Ma'lumot yo'q" to "No data"),
        "required_field" to ("To'ldirilishi shart" to "Required"),
        "permission_denied" to ("Sizda ruxsat yo'q" to "Permission denied"),
        "saved" to ("Saqlandi" to "Saved"),
        "language" to ("Til" to "Language"),
        "logout" to ("Chiqish" to "Log out"),
        "confirm" to ("Tasdiqlash" to "Confirm"),
        "percent_done" to ("Bajarilish" to "Progress"),
        "filter" to ("Filtr" to "Filter"),
        "created" to ("Yaratilgan" to "Created"),
        "of" to ("dan" to "of"),
        // auth
        "login" to ("Kirish" to "Sign in"),
        "username" to ("Foydalanuvchi nomi" to "Username"),
        "password" to ("Parol" to "Password"),
        "login_failed" to ("Login yoki parol noto'g'ri" to "Invalid username or password"),
        "user_inactive" to ("Foydalanuvchi bloklangan" to "User is deactivated"),
        "no_users_hint" to (
            "Bazada foydalanuvchi yo'q. Avval sinxronizatsiyani sozlab, ma'lumotni yuklab oling."
                to "No users yet. Configure synchronisation first and pull the data."
            ),
        "remember_me" to ("Meni eslab qol" to "Remember me"),
        "demo_hint" to ("Demo: admin / admin123" to "Demo: admin / admin123"),
        // navigation
        "nav_projects" to ("Loyihalar" to "Projects"),
        "nav_warehouse" to ("Ombor" to "Warehouse"),
        "nav_expenses" to ("Xarajatlar" to "Expenses"),
        "nav_settings" to ("Sozlamalar" to "Settings"),
        // projects
        "projects" to ("Loyihalar" to "Projects"),
        "project" to ("Loyiha" to "Project"),
        "new_project" to ("Yangi loyiha" to "New project"),
        "project_name" to ("Loyiha nomi" to "Project name"),
        "client" to ("Mijoz" to "Client"),
        "address" to ("Manzil" to "Address"),
        "project_type" to ("Loyiha turi" to "Project type"),
        "start_date" to ("Boshlanish" to "Start"),
        "end_date" to ("Yakunlanish" to "Finish"),
        "planned_budget" to ("Rejalashtirilgan budjet" to "Planned budget"),
        "show_archived" to ("Arxivdagilar" to "Archived"),
        // tabs
        "tab_overview" to ("Holat" to "Overview"),
        "tab_estimate" to ("Smeta" to "Estimate"),
        "tab_purchases" to ("Xaridlar" to "Purchases"),
        "tab_warehouse" to ("Ombor" to "Warehouse"),
        "tab_stages" to ("Bosqichlar" to "Stages"),
        "tab_expenses" to ("Xarajatlar" to "Expenses"),
        // overview
        "budget" to ("Budjet" to "Budget"),
        "committed_cost" to ("Tasdiqlangan" to "Committed"),
        "actual_cost" to ("Amaldagi xarajat" to "Actual cost"),
        "remaining_funds" to ("Qolgan mablag'" to "Remaining"),
        "estimate_total" to ("Smeta jami" to "Estimate total"),
        "budget_usage" to ("Budjet sarfi" to "Budget usage"),
        "delayed_stages" to ("Kechikkan bosqichlar" to "Delayed stages"),
        "pending_purchases" to ("Tasdiq kutayotgan xaridlar" to "Purchases awaiting approval"),
        "over_budget" to ("Budjetdan oshgan" to "Over budget"),
        "stages_summary" to ("Bosqichlar" to "Stages"),
        "materials_issued" to ("Ombordan chiqim" to "Materials issued"),
        // estimate
        "estimate" to ("Smeta" to "Estimate"),
        "estimate_version" to ("Versiya" to "Version"),
        "add_section" to ("Bo'lim qo'shish" to "Add section"),
        "add_item" to ("Band qo'shish" to "Add item"),
        "plan_unit_price" to ("Reja birlik narxi" to "Plan unit price"),
        "plan_total" to ("Reja jami" to "Plan total"),
        "actual_total" to ("Amaldagi jami" to "Actual total"),
        "variance" to ("Farq" to "Variance"),
        "estimate_locked" to (
            "Tasdiqlangan smeta tahrirlanmaydi" to "An approved estimate is read-only"
            ),
        "section" to ("Bo'lim" to "Section"),
        "item" to ("Band" to "Item"),
        "no_estimate" to ("Smeta hali yaratilmagan" to "No estimate yet"),
        // purchases
        "purchase_request" to ("Xarid talabi" to "Purchase request"),
        "new_request" to ("Yangi talab" to "New request"),
        "product_service" to ("Mahsulot / xizmat" to "Product / service"),
        "est_price" to ("Taxminiy narx" to "Estimated price"),
        "needed_date" to ("Kerak bo'ladigan sana" to "Needed by"),
        "off_estimate" to ("Smetadan tashqari" to "Off-estimate"),
        "estimate_item" to ("Smeta bandi" to "Estimate item"),
        "estimate_item_required" to (
            "Smeta bandini tanlang yoki 'smetadan tashqari' belgilang"
                to "Pick an estimate item or mark it off-estimate"
            ),
        "quotes" to ("Takliflar" to "Quotes"),
        "add_quote" to ("Taklif qo'shish" to "Add quote"),
        "supplier" to ("Yetkazib beruvchi" to "Supplier"),
        "unit_price" to ("Birlik narxi" to "Unit price"),
        "delivery_cost" to ("Yetkazish narxi" to "Delivery cost"),
        "delivery_days" to ("Muddat, kun" to "Lead time, days"),
        "total_value" to ("Umumiy qiymat" to "Total value"),
        "best_offer" to ("Eng yaxshi" to "Best"),
        "select_quote" to ("Tanlash" to "Select"),
        "submit" to ("Tasdiqlashga yuborish" to "Submit"),
        "approve" to ("Tasdiqlash" to "Approve"),
        "reject" to ("Rad etish" to "Reject"),
        // warehouse
        "materials" to ("Materiallar" to "Materials"),
        "material" to ("Material" to "Material"),
        "sku" to ("SKU" to "SKU"),
        "min_stock" to ("Minimal qoldiq" to "Minimum stock"),
        "standard_price" to ("Standart narx" to "Standard price"),
        "stock" to ("Qoldiq" to "Stock"),
        "stock_value" to ("Qoldiq qiymati" to "Stock value"),
        "low_stock" to ("Kam qolgan" to "Low stock"),
        "movements" to ("Harakatlar" to "Movements"),
        "new_movement" to ("Yangi harakat" to "New movement"),
        "not_enough_stock" to ("Omborda yetarli qoldiq yo'q" to "Not enough stock"),
        "quantity_positive" to ("Miqdor noldan katta bo'lsin" to "Quantity must be positive"),
        "sku_exists" to ("Bunday SKU mavjud" to "This SKU already exists"),
        "new_material" to ("Yangi material" to "New material"),
        // stages
        "stages" to ("Ish bosqichlari" to "Work stages"),
        "stage" to ("Bosqich" to "Stage"),
        "new_stage" to ("Yangi bosqich" to "New stage"),
        "plan_start" to ("Reja boshlanish" to "Plan start"),
        "plan_end" to ("Reja yakun" to "Plan finish"),
        "site_log" to ("Kundalik jurnal" to "Site log"),
        "new_log" to ("Yangi yozuv" to "New entry"),
        "work_done" to ("Bajarilgan ish" to "Work done"),
        "workers_count" to ("Ishchilar soni" to "Workers"),
        "issue" to ("Muammo" to "Issue"),
        "overdue_days" to ("Kechikish, kun" to "Overdue, days"),
        // expenses
        "expenses" to ("Xarajatlar" to "Expenses"),
        "new_expense" to ("Yangi xarajat" to "New expense"),
        "counterparty" to ("Kontragent" to "Counterparty"),
        "pay_date" to ("To'lov sanasi" to "Payment date"),
        "method" to ("To'lov usuli" to "Payment method"),
        "invoice_no" to ("Chek / faktura" to "Invoice no."),
        "mark_paid" to ("To'langan" to "Mark paid"),
        "budget_exceed_warning" to (
            "Diqqat: bu xarajat budjetdan oshib ketadi" to "Warning: this pushes the project over budget"
            ),
        "paid_amount" to ("To'langan" to "Paid"),
        // settings / sync
        "settings" to ("Sozlamalar" to "Settings"),
        "sync" to ("Sinxronizatsiya" to "Synchronisation"),
        "sync_intro" to (
            "Telefon o'z bazasida ishlaydi va internetsiz ham to'liq ishlaydi."
                to "The phone keeps its own database and works offline."
            ),
        "sync_backend" to ("Ulanish turi" to "Backend"),
        "sync_url" to ("Supabase URL" to "Supabase URL"),
        "sync_api_key" to ("API kaliti (anon)" to "API key (anon)"),
        "sync_tenant" to ("Ish maydoni kaliti" to "Workspace key"),
        "sync_device_name" to ("Qurilma nomi" to "Device name"),
        "sync_auto" to ("Avtomatik sinxronizatsiya" to "Automatic sync"),
        "sync_now" to ("Hozir sinxronlash" to "Sync now"),
        "sync_test" to ("Ulanishni tekshirish" to "Test connection"),
        "sync_status" to ("Holat" to "Status"),
        "sync_pending" to ("Yuborilmagan" to "Pending"),
        "sync_last_push" to ("Oxirgi yuborish" to "Last push"),
        "sync_last_pull" to ("Oxirgi qabul" to "Last pull"),
        "sync_cursor" to ("Jurnal pozitsiyasi" to "Log position"),
        "sync_upload_all" to ("Hammasini yuklash" to "Upload everything"),
        "sync_reset" to ("Jurnalni qayta o'qish" to "Replay log"),
        "sync_running" to ("Sinxronlanmoqda..." to "Synchronising..."),
        "sync_ok" to ("Sinxronizatsiya yakunlandi" to "Sync finished"),
        "sync_failed" to ("Sinxronizatsiya xatosi" to "Sync failed"),
        "sync_disabled" to ("O'chirilgan" to "Disabled"),
        "sync_never" to ("Hech qachon" to "Never"),
        "sync_off_option" to ("O'chirilgan (faqat lokal)" to "Disabled (local only)"),
        "sync_supabase_option" to ("Supabase (internet)" to "Supabase (internet)"),
        "sync_mqtt_option" to (
            "MQTT broker (bepul, ro'yxatdan o'tmasdan)"
                to "MQTT broker (free, no sign-up)"
            ),
        "mqtt_broker" to ("Broker" to "Broker"),
        "mqtt_host" to ("Broker manzili" to "Broker host"),
        "mqtt_port" to ("Port" to "Port"),
        "mqtt_tls" to ("TLS (shifrlangan ulanish)" to "TLS (encrypted connection)"),
        "mqtt_prefix" to ("Mavzu prefiksi" to "Topic prefix"),
        "mqtt_custom" to ("Boshqa (qo'lda)" to "Other (manual)"),
        "sync_passphrase" to ("Shifrlash paroli" to "Encryption passphrase"),
        "mqtt_warning" to (
            "Diqqat: ommaviy broker hammaga ochiq. Ish maydoni kalitini uzun qiling "
                + "va shifrlash parolini yoqing."
                to "Warning: a public broker is open to everyone. Use a long workspace "
                + "key and enable the passphrase."
            ),
        "sync_help" to (
            "Kompyuterdagi BuildControl bilan bir xil URL, kalit va ish maydoni kalitini kiriting."
                to "Enter the same URL, key and workspace key as the desktop application."
            ),
        "device_id" to ("Qurilma ID" to "Device ID"),
        "about" to ("Dastur haqi" to "About"),
        // enums
        "role.admin" to ("Administrator" to "Administrator"),
        "role.manager" to ("Loyiha rahbari" to "Project manager"),
        "role.estimator" to ("Smetachi" to "Estimator"),
        "role.storekeeper" to ("Omborchi" to "Storekeeper"),
        "role.viewer" to ("Kuzatuvchi" to "Viewer"),
        "ptype.new_build" to ("Yangi qurilish" to "New build"),
        "ptype.renovation" to ("Ta'mirlash" to "Renovation"),
        "ptype.interior" to ("Interyer" to "Interior"),
        "ptype.facade" to ("Fasad" to "Facade"),
        "ptype.other" to ("Boshqa" to "Other"),
        "pstatus.planned" to ("Rejalashtirilgan" to "Planned"),
        "pstatus.active" to ("Faol" to "Active"),
        "pstatus.suspended" to ("To'xtatilgan" to "Suspended"),
        "pstatus.completed" to ("Yakunlangan" to "Completed"),
        "pstatus.archived" to ("Arxiv" to "Archived"),
        "estatus.draft" to ("Qoralama" to "Draft"),
        "estatus.submitted" to ("Tasdiqlashga yuborilgan" to "Submitted"),
        "estatus.approved" to ("Tasdiqlangan" to "Approved"),
        "estatus.revision" to ("Qayta ko'rib chiqilmoqda" to "In revision"),
        "istatus.planned" to ("Rejada" to "Planned"),
        "istatus.in_progress" to ("Jarayonda" to "In progress"),
        "istatus.needs_purchase" to ("Xarid kerak" to "Needs purchase"),
        "istatus.done" to ("Bajarilgan" to "Done"),
        "istatus.cancelled" to ("Bekor qilingan" to "Cancelled"),
        "unit.piece" to ("dona" to "pcs"),
        "unit.kg" to ("kg" to "kg"),
        "unit.ton" to ("tonna" to "ton"),
        "unit.m" to ("metr" to "m"),
        "unit.m2" to ("m²" to "m²"),
        "unit.m3" to ("m³" to "m³"),
        "unit.hour" to ("soat" to "hour"),
        "unit.day" to ("kun" to "day"),
        "unit.service" to ("xizmat" to "service"),
        "unit.liter" to ("litr" to "litre"),
        "unit.set" to ("komplekt" to "set"),
        "purchase.draft" to ("Qoralama" to "Draft"),
        "purchase.submitted" to ("Yuborilgan" to "Submitted"),
        "purchase.approved" to ("Tasdiqlangan" to "Approved"),
        "purchase.rejected" to ("Rad etilgan" to "Rejected"),
        "purchase.ordered" to ("Buyurtma berilgan" to "Ordered"),
        "purchase.partial" to ("Qisman qabul" to "Partial"),
        "purchase.completed" to ("Yakunlangan" to "Completed"),
        "tx.in" to ("Kirim" to "Receipt"),
        "tx.out" to ("Chiqim" to "Issue"),
        "tx.return" to ("Qaytarish" to "Return"),
        "tx.adjust" to ("Inventarizatsiya" to "Adjustment"),
        "tx.loss" to ("Yo'qotish" to "Loss"),
        "sstatus.not_started" to ("Boshlanmagan" to "Not started"),
        "sstatus.in_progress" to ("Jarayonda" to "In progress"),
        "sstatus.review" to ("Tekshiruvda" to "In review"),
        "sstatus.delayed" to ("Kechikkan" to "Delayed"),
        "sstatus.done" to ("Yakunlangan" to "Completed"),
        "sstatus.blocked" to ("Bloklangan" to "Blocked"),
        "xstatus.pending" to ("Kutilmoqda" to "Pending"),
        "xstatus.approved" to ("Tasdiqlangan" to "Approved"),
        "xstatus.paid" to ("To'langan" to "Paid"),
        "xstatus.rejected" to ("Rad etilgan" to "Rejected"),
        "method.cash" to ("Naqd" to "Cash"),
        "method.card" to ("Karta" to "Card"),
        "method.transfer" to ("Bank o'tkazmasi" to "Bank transfer"),
        "xcat.material" to ("Material" to "Material"),
        "xcat.labor" to ("Ish haqi" to "Labor"),
        "xcat.equipment" to ("Texnika" to "Equipment"),
        "xcat.transport" to ("Transport" to "Transport"),
        "xcat.subcontract" to ("Subpudrat" to "Subcontract"),
        "xcat.overhead" to ("Umumiy xarajat" to "Overhead"),
        "xcat.other" to ("Boshqa" to "Other"),
    )
}

/** Shorthand used throughout the composables. */
fun tr(key: String): String = I18n.tr(key)
