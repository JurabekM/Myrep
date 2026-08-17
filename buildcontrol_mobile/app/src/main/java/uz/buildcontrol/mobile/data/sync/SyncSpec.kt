package uz.buildcontrol.mobile.data.sync

/**
 * Wire description of every replicated table.
 *
 * This mirrors `app/sync/registry.py` on the desktop: the same entity names,
 * the same column names, and foreign keys that travel as the target row's uid.
 * Any divergence here silently breaks interoperability, so the list is kept
 * explicit rather than derived.
 */

enum class ColKind { TEXT, INT, REAL, BOOL, DATETIME, DATE }

data class Col(val name: String, val kind: ColKind, val fk: String? = null)

data class TableSpec(
    val entity: String,
    val table: String,
    val cols: List<Col>,
    val naturalKeys: List<String> = emptyList(),
    val singleton: Boolean = false,
) {
    val byName: Map<String, Col> = cols.associateBy { it.name }
    fun fkCols(): List<Col> = cols.filter { it.fk != null }
}

private fun t(name: String) = Col(name, ColKind.TEXT)
private fun i(name: String) = Col(name, ColKind.INT)
private fun r(name: String) = Col(name, ColKind.REAL)
private fun b(name: String) = Col(name, ColKind.BOOL)
private fun dt(name: String) = Col(name, ColKind.DATETIME)
private fun d(name: String) = Col(name, ColKind.DATE)
private fun fk(name: String, target: String) = Col(name, ColKind.INT, target)

/** Shared trailing columns present on most tables. */
private val SYNC_COLS = listOf(t("uid"), dt("sync_ts"))
private val STAMP_COLS = listOf(dt("created_at"), dt("updated_at"))
private val ARCHIVE_COL = listOf(b("is_archived"))

/**
 * Ordered so parents are applied before children when a batch arrives.
 */
val SYNC_TABLES: List<TableSpec> = listOf(
    TableSpec(
        "Role", "roles",
        listOf(t("code"), t("name_uz"), t("name_en"), t("description")) + SYNC_COLS,
        naturalKeys = listOf("code"),
    ),
    TableSpec(
        "User", "users",
        listOf(
            t("username"), t("full_name"), t("password_hash"), fk("role_id", "roles"),
            t("email"), t("phone"), b("is_active"), dt("last_login"),
        ) + SYNC_COLS + STAMP_COLS + ARCHIVE_COL,
        naturalKeys = listOf("username"),
    ),
    TableSpec(
        "RefItem", "ref_items",
        listOf(
            t("kind"), t("code"), t("name_uz"), t("name_en"), i("order_index"), b("is_system"),
        ) + SYNC_COLS + ARCHIVE_COL,
        naturalKeys = listOf("kind", "code"),
    ),
    TableSpec(
        "CompanySettings", "company_settings",
        listOf(
            t("name"), t("logo_path"), t("address"), t("phone"), t("requisites"),
            t("currency"), t("language"),
        ) + SYNC_COLS,
        singleton = true,
    ),
    TableSpec(
        "Counterparty", "counterparties",
        listOf(
            t("kind"), t("name"), t("tin"), t("phone"), t("email"), t("address"),
            t("bank_details"), t("category"), r("rating"), t("note"),
            r("contract_amount"), r("paid_amount"), r("completed_work"),
            i("delay_days"), r("quality_score"), i("disputes"),
        ) + SYNC_COLS + STAMP_COLS + ARCHIVE_COL,
    ),
    TableSpec(
        "Material", "materials",
        listOf(
            t("sku"), t("name"), t("category"), t("unit"), r("min_stock"),
            r("standard_price"), fk("supplier_id", "counterparties"), t("note"),
        ) + SYNC_COLS + STAMP_COLS + ARCHIVE_COL,
        naturalKeys = listOf("sku"),
    ),
    TableSpec(
        "Project", "projects",
        listOf(
            t("code"), t("name"), t("client"), t("address"), t("project_type"),
            d("start_date"), d("end_date"), fk("manager_id", "users"),
            r("planned_budget"), t("currency"), t("status"), t("notes"),
        ) + SYNC_COLS + STAMP_COLS + ARCHIVE_COL,
        naturalKeys = listOf("code"),
    ),
    TableSpec(
        "ProjectMember", "project_members",
        listOf(
            fk("project_id", "projects"), fk("user_id", "users"), t("role_in_project"),
        ) + SYNC_COLS,
    ),
    TableSpec(
        "EstimateVersion", "estimate_versions",
        listOf(
            fk("project_id", "projects"), i("version_no"), t("status"), b("is_current"),
            t("note"), fk("created_by_id", "users"), fk("approved_by_id", "users"),
            dt("approved_at"),
        ) + SYNC_COLS + STAMP_COLS,
    ),
    TableSpec(
        "EstimateSection", "estimate_sections",
        listOf(
            fk("version_id", "estimate_versions"), fk("parent_id", "estimate_sections"),
            t("code"), t("name"), i("order_index"),
        ) + SYNC_COLS,
    ),
    TableSpec(
        "EstimateItem", "estimate_items",
        listOf(
            fk("section_id", "estimate_sections"), t("code"), t("name"), t("category"),
            t("unit"), r("quantity"), r("plan_unit_price"), r("actual_cost"),
            r("progress_percent"), fk("responsible_id", "users"), t("status"), t("note"),
            i("order_index"),
        ) + SYNC_COLS,
    ),
    TableSpec(
        "PurchaseRequest", "purchase_requests",
        listOf(
            t("number"), fk("project_id", "projects"), fk("estimate_item_id", "estimate_items"),
            b("off_estimate"), t("title"), t("unit"), r("quantity"), r("est_price"),
            d("needed_date"), t("delivery_address"), fk("responsible_id", "users"),
            t("status"), t("note"),
        ) + SYNC_COLS + STAMP_COLS + ARCHIVE_COL,
    ),
    TableSpec(
        "SupplierQuote", "supplier_quotes",
        listOf(
            fk("request_id", "purchase_requests"), fk("supplier_id", "counterparties"),
            t("supplier_name"), t("contact"), r("unit_price"), r("delivery_cost"),
            i("delivery_days"), t("payment_terms"), t("file_path"), b("is_selected"),
        ) + SYNC_COLS + STAMP_COLS,
    ),
    TableSpec(
        "PurchaseOrder", "purchase_orders",
        listOf(
            t("order_no"), fk("request_id", "purchase_requests"),
            fk("quote_id", "supplier_quotes"), fk("supplier_id", "counterparties"),
            d("order_date"), r("total_amount"), t("status"), t("note"),
        ) + SYNC_COLS + STAMP_COLS,
    ),
    TableSpec(
        "WarehouseTransaction", "warehouse_transactions",
        listOf(
            d("tx_date"), t("kind"), fk("material_id", "materials"), r("quantity"),
            r("unit_price"), fk("project_id", "projects"),
            fk("estimate_item_id", "estimate_items"), fk("user_id", "users"),
            t("doc_path"), t("note"),
        ) + SYNC_COLS + STAMP_COLS,
    ),
    TableSpec(
        "WorkStage", "work_stages",
        listOf(
            fk("project_id", "projects"), t("name"), fk("section_id", "estimate_sections"),
            d("plan_start"), d("plan_end"), d("actual_start"), d("actual_end"),
            r("progress_percent"), fk("responsible_id", "users"), t("status"),
            t("dependencies"), t("note"), i("order_index"),
        ) + SYNC_COLS + STAMP_COLS + ARCHIVE_COL,
    ),
    TableSpec(
        "DailySiteLog", "daily_site_logs",
        listOf(
            d("log_date"), fk("project_id", "projects"), fk("stage_id", "work_stages"),
            t("work_done"), r("progress_percent"), i("workers_count"), t("issue"),
            t("photo_path"), fk("author_id", "users"),
        ) + SYNC_COLS + STAMP_COLS,
    ),
    TableSpec(
        "Expense", "expenses",
        listOf(
            fk("project_id", "projects"), t("category"),
            fk("estimate_item_id", "estimate_items"), fk("counterparty_id", "counterparties"),
            r("amount"), t("currency"), d("pay_date"), t("method"), t("invoice_no"),
            t("doc_path"), t("note"), t("status"), fk("created_by_id", "users"),
            fk("approved_by_id", "users"), dt("approved_at"),
        ) + SYNC_COLS + STAMP_COLS + ARCHIVE_COL,
    ),
    TableSpec(
        "Payment", "payments",
        listOf(
            fk("expense_id", "expenses"), r("amount"), d("pay_date"), t("method"),
            t("note"), fk("created_by_id", "users"),
        ) + SYNC_COLS + STAMP_COLS,
    ),
    TableSpec(
        "Attachment", "attachments",
        listOf(
            t("entity_type"), i("entity_id"), t("title"), t("file_path"),
            fk("user_id", "users"),
        ) + SYNC_COLS + STAMP_COLS,
    ),
    TableSpec(
        "AuditLog", "audit_logs",
        listOf(
            dt("ts"), fk("user_id", "users"), t("username"), t("action"), t("entity_type"),
            i("entity_id"), fk("project_id", "projects"), t("description"),
            t("old_value"), t("new_value"),
        ) + SYNC_COLS,
    ),
)

val SPEC_BY_ENTITY: Map<String, TableSpec> = SYNC_TABLES.associateBy { it.entity }
val SPEC_BY_TABLE: Map<String, TableSpec> = SYNC_TABLES.associateBy { it.table }
val ENTITY_ORDER: Map<String, Int> = SYNC_TABLES.withIndex().associate { it.value.entity to it.index }
