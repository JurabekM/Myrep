package uz.buildcontrol.mobile.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.util.UUID

/**
 * Room entities mirroring the desktop SQLAlchemy schema column for column.
 *
 * `id` is a local surrogate key that differs per installation; `uid` is the
 * global identity used by replication and `sync_ts` carries the logical write
 * time for last-write-wins conflict resolution.
 */

fun newUid(): String = UUID.randomUUID().toString().replace("-", "")

fun now(): Long = System.currentTimeMillis()

@Entity(tableName = "roles", indices = [Index(value = ["uid"], unique = true)])
data class RoleRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String = "",
    @ColumnInfo(name = "name_uz") val nameUz: String = "",
    @ColumnInfo(name = "name_en") val nameEn: String = "",
    val description: String? = "",
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
)

@Entity(tableName = "users", indices = [Index(value = ["uid"], unique = true)])
data class UserRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val username: String = "",
    @ColumnInfo(name = "full_name") val fullName: String = "",
    @ColumnInfo(name = "password_hash") val passwordHash: String = "",
    @ColumnInfo(name = "role_id") val roleId: Long? = null,
    val email: String? = "",
    val phone: String? = "",
    @ColumnInfo(name = "is_active") val isActive: Boolean = true,
    @ColumnInfo(name = "last_login") val lastLogin: Long? = null,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
    @ColumnInfo(name = "is_archived") val isArchived: Boolean = false,
)

@Entity(tableName = "ref_items", indices = [Index(value = ["uid"], unique = true)])
data class RefItemRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val kind: String = "",
    val code: String = "",
    @ColumnInfo(name = "name_uz") val nameUz: String = "",
    @ColumnInfo(name = "name_en") val nameEn: String = "",
    @ColumnInfo(name = "order_index") val orderIndex: Int = 0,
    @ColumnInfo(name = "is_system") val isSystem: Boolean = false,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "is_archived") val isArchived: Boolean = false,
)

@Entity(tableName = "company_settings", indices = [Index(value = ["uid"], unique = true)])
data class CompanySettingsRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String = "BuildControl",
    @ColumnInfo(name = "logo_path") val logoPath: String? = "",
    val address: String? = "",
    val phone: String? = "",
    val requisites: String? = "",
    val currency: String = "UZS",
    val language: String = "uz",
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
)

@Entity(tableName = "counterparties", indices = [Index(value = ["uid"], unique = true)])
data class CounterpartyRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val kind: String = "supplier",
    val name: String = "",
    val tin: String? = "",
    val phone: String? = "",
    val email: String? = "",
    val address: String? = "",
    @ColumnInfo(name = "bank_details") val bankDetails: String? = "",
    val category: String? = "",
    val rating: Double = 0.0,
    val note: String? = "",
    @ColumnInfo(name = "contract_amount") val contractAmount: Double = 0.0,
    @ColumnInfo(name = "paid_amount") val paidAmount: Double = 0.0,
    @ColumnInfo(name = "completed_work") val completedWork: Double = 0.0,
    @ColumnInfo(name = "delay_days") val delayDays: Int = 0,
    @ColumnInfo(name = "quality_score") val qualityScore: Double = 0.0,
    val disputes: Int = 0,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
    @ColumnInfo(name = "is_archived") val isArchived: Boolean = false,
)

@Entity(tableName = "materials", indices = [Index(value = ["uid"], unique = true)])
data class MaterialRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val sku: String = "",
    val name: String = "",
    val category: String? = "",
    val unit: String = "piece",
    @ColumnInfo(name = "min_stock") val minStock: Double = 0.0,
    @ColumnInfo(name = "standard_price") val standardPrice: Double = 0.0,
    @ColumnInfo(name = "supplier_id") val supplierId: Long? = null,
    val note: String? = "",
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
    @ColumnInfo(name = "is_archived") val isArchived: Boolean = false,
)

@Entity(tableName = "projects", indices = [Index(value = ["uid"], unique = true)])
data class ProjectRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String = "",
    val name: String = "",
    val client: String? = "",
    val address: String? = "",
    @ColumnInfo(name = "project_type") val projectType: String = "renovation",
    @ColumnInfo(name = "start_date") val startDate: String? = null,
    @ColumnInfo(name = "end_date") val endDate: String? = null,
    @ColumnInfo(name = "manager_id") val managerId: Long? = null,
    @ColumnInfo(name = "planned_budget") val plannedBudget: Double = 0.0,
    val currency: String = "UZS",
    val status: String = "planned",
    val notes: String? = "",
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
    @ColumnInfo(name = "is_archived") val isArchived: Boolean = false,
)

@Entity(tableName = "project_members", indices = [Index(value = ["uid"], unique = true)])
data class ProjectMemberRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "project_id") val projectId: Long? = null,
    @ColumnInfo(name = "user_id") val userId: Long? = null,
    @ColumnInfo(name = "role_in_project") val roleInProject: String? = "",
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
)

@Entity(tableName = "estimate_versions", indices = [Index(value = ["uid"], unique = true)])
data class EstimateVersionRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "project_id") val projectId: Long? = null,
    @ColumnInfo(name = "version_no") val versionNo: Int = 1,
    val status: String = "draft",
    @ColumnInfo(name = "is_current") val isCurrent: Boolean = true,
    val note: String? = "",
    @ColumnInfo(name = "created_by_id") val createdById: Long? = null,
    @ColumnInfo(name = "approved_by_id") val approvedById: Long? = null,
    @ColumnInfo(name = "approved_at") val approvedAt: Long? = null,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
)

@Entity(tableName = "estimate_sections", indices = [Index(value = ["uid"], unique = true)])
data class EstimateSectionRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "version_id") val versionId: Long? = null,
    @ColumnInfo(name = "parent_id") val parentId: Long? = null,
    val code: String? = "",
    val name: String = "",
    @ColumnInfo(name = "order_index") val orderIndex: Int = 0,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
)

@Entity(tableName = "estimate_items", indices = [Index(value = ["uid"], unique = true)])
data class EstimateItemRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "section_id") val sectionId: Long? = null,
    val code: String? = "",
    val name: String = "",
    val category: String? = "",
    val unit: String = "piece",
    val quantity: Double = 0.0,
    @ColumnInfo(name = "plan_unit_price") val planUnitPrice: Double = 0.0,
    @ColumnInfo(name = "actual_cost") val actualCost: Double = 0.0,
    @ColumnInfo(name = "progress_percent") val progressPercent: Double = 0.0,
    @ColumnInfo(name = "responsible_id") val responsibleId: Long? = null,
    val status: String = "planned",
    val note: String? = "",
    @ColumnInfo(name = "order_index") val orderIndex: Int = 0,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
) {
    val planTotal: Double get() = quantity * planUnitPrice
    val variance: Double get() = actualCost - planTotal
    val variancePercent: Double get() = if (planTotal != 0.0) variance / planTotal * 100.0 else 0.0
}

@Entity(tableName = "purchase_requests", indices = [Index(value = ["uid"], unique = true)])
data class PurchaseRequestRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val number: String? = "",
    @ColumnInfo(name = "project_id") val projectId: Long? = null,
    @ColumnInfo(name = "estimate_item_id") val estimateItemId: Long? = null,
    @ColumnInfo(name = "off_estimate") val offEstimate: Boolean = false,
    val title: String = "",
    val unit: String = "piece",
    val quantity: Double = 0.0,
    @ColumnInfo(name = "est_price") val estPrice: Double = 0.0,
    @ColumnInfo(name = "needed_date") val neededDate: String? = null,
    @ColumnInfo(name = "delivery_address") val deliveryAddress: String? = "",
    @ColumnInfo(name = "responsible_id") val responsibleId: Long? = null,
    val status: String = "draft",
    val note: String? = "",
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
    @ColumnInfo(name = "is_archived") val isArchived: Boolean = false,
) {
    val estTotal: Double get() = quantity * estPrice
}

@Entity(tableName = "supplier_quotes", indices = [Index(value = ["uid"], unique = true)])
data class SupplierQuoteRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "request_id") val requestId: Long? = null,
    @ColumnInfo(name = "supplier_id") val supplierId: Long? = null,
    @ColumnInfo(name = "supplier_name") val supplierName: String? = "",
    val contact: String? = "",
    @ColumnInfo(name = "unit_price") val unitPrice: Double = 0.0,
    @ColumnInfo(name = "delivery_cost") val deliveryCost: Double = 0.0,
    @ColumnInfo(name = "delivery_days") val deliveryDays: Int = 0,
    @ColumnInfo(name = "payment_terms") val paymentTerms: String? = "",
    @ColumnInfo(name = "file_path") val filePath: String? = "",
    @ColumnInfo(name = "is_selected") val isSelected: Boolean = false,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
) {
    fun totalValue(quantity: Double): Double = unitPrice * quantity + deliveryCost
}

@Entity(tableName = "purchase_orders", indices = [Index(value = ["uid"], unique = true)])
data class PurchaseOrderRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "order_no") val orderNo: String = "",
    @ColumnInfo(name = "request_id") val requestId: Long? = null,
    @ColumnInfo(name = "quote_id") val quoteId: Long? = null,
    @ColumnInfo(name = "supplier_id") val supplierId: Long? = null,
    @ColumnInfo(name = "order_date") val orderDate: String? = null,
    @ColumnInfo(name = "total_amount") val totalAmount: Double = 0.0,
    val status: String = "new",
    val note: String? = "",
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
)

@Entity(tableName = "warehouse_transactions", indices = [Index(value = ["uid"], unique = true)])
data class WarehouseTxRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "tx_date") val txDate: String? = null,
    val kind: String = "in",
    @ColumnInfo(name = "material_id") val materialId: Long? = null,
    val quantity: Double = 0.0,
    @ColumnInfo(name = "unit_price") val unitPrice: Double = 0.0,
    @ColumnInfo(name = "project_id") val projectId: Long? = null,
    @ColumnInfo(name = "estimate_item_id") val estimateItemId: Long? = null,
    @ColumnInfo(name = "user_id") val userId: Long? = null,
    @ColumnInfo(name = "doc_path") val docPath: String? = "",
    val note: String? = "",
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
) {
    val total: Double get() = quantity * unitPrice
}

@Entity(tableName = "work_stages", indices = [Index(value = ["uid"], unique = true)])
data class WorkStageRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "project_id") val projectId: Long? = null,
    val name: String = "",
    @ColumnInfo(name = "section_id") val sectionId: Long? = null,
    @ColumnInfo(name = "plan_start") val planStart: String? = null,
    @ColumnInfo(name = "plan_end") val planEnd: String? = null,
    @ColumnInfo(name = "actual_start") val actualStart: String? = null,
    @ColumnInfo(name = "actual_end") val actualEnd: String? = null,
    @ColumnInfo(name = "progress_percent") val progressPercent: Double = 0.0,
    @ColumnInfo(name = "responsible_id") val responsibleId: Long? = null,
    val status: String = "not_started",
    val dependencies: String? = "",
    val note: String? = "",
    @ColumnInfo(name = "order_index") val orderIndex: Int = 0,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
    @ColumnInfo(name = "is_archived") val isArchived: Boolean = false,
)

@Entity(tableName = "daily_site_logs", indices = [Index(value = ["uid"], unique = true)])
data class SiteLogRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "log_date") val logDate: String? = null,
    @ColumnInfo(name = "project_id") val projectId: Long? = null,
    @ColumnInfo(name = "stage_id") val stageId: Long? = null,
    @ColumnInfo(name = "work_done") val workDone: String? = "",
    @ColumnInfo(name = "progress_percent") val progressPercent: Double = 0.0,
    @ColumnInfo(name = "workers_count") val workersCount: Int = 0,
    val issue: String? = "",
    @ColumnInfo(name = "photo_path") val photoPath: String? = "",
    @ColumnInfo(name = "author_id") val authorId: Long? = null,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
)

@Entity(tableName = "expenses", indices = [Index(value = ["uid"], unique = true)])
data class ExpenseRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "project_id") val projectId: Long? = null,
    val category: String = "material",
    @ColumnInfo(name = "estimate_item_id") val estimateItemId: Long? = null,
    @ColumnInfo(name = "counterparty_id") val counterpartyId: Long? = null,
    val amount: Double = 0.0,
    val currency: String = "UZS",
    @ColumnInfo(name = "pay_date") val payDate: String? = null,
    val method: String = "transfer",
    @ColumnInfo(name = "invoice_no") val invoiceNo: String? = "",
    @ColumnInfo(name = "doc_path") val docPath: String? = "",
    val note: String? = "",
    val status: String = "pending",
    @ColumnInfo(name = "created_by_id") val createdById: Long? = null,
    @ColumnInfo(name = "approved_by_id") val approvedById: Long? = null,
    @ColumnInfo(name = "approved_at") val approvedAt: Long? = null,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
    @ColumnInfo(name = "is_archived") val isArchived: Boolean = false,
)

@Entity(tableName = "payments", indices = [Index(value = ["uid"], unique = true)])
data class PaymentRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "expense_id") val expenseId: Long? = null,
    val amount: Double = 0.0,
    @ColumnInfo(name = "pay_date") val payDate: String? = null,
    val method: String = "transfer",
    val note: String? = "",
    @ColumnInfo(name = "created_by_id") val createdById: Long? = null,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
)

@Entity(tableName = "attachments", indices = [Index(value = ["uid"], unique = true)])
data class AttachmentRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "entity_type") val entityType: String = "",
    @ColumnInfo(name = "entity_id") val entityId: Long? = null,
    val title: String? = "",
    @ColumnInfo(name = "file_path") val filePath: String = "",
    @ColumnInfo(name = "user_id") val userId: Long? = null,
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = now(),
)

@Entity(tableName = "audit_logs", indices = [Index(value = ["uid"], unique = true)])
data class AuditLogRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val ts: Long = now(),
    @ColumnInfo(name = "user_id") val userId: Long? = null,
    val username: String? = "",
    val action: String = "",
    @ColumnInfo(name = "entity_type") val entityType: String? = "",
    @ColumnInfo(name = "entity_id") val entityId: Long? = null,
    @ColumnInfo(name = "project_id") val projectId: Long? = null,
    val description: String? = "",
    @ColumnInfo(name = "old_value") val oldValue: String? = "",
    @ColumnInfo(name = "new_value") val newValue: String? = "",
    val uid: String = newUid(),
    @ColumnInfo(name = "sync_ts") val syncTs: Long = now(),
)

// --------------------------------------------------------------------------- //
// Local-only replication bookkeeping (never itself replicated)
// --------------------------------------------------------------------------- //

@Entity(tableName = "sync_outbox")
data class OutboxRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val entity: String,
    val uid: String,
    val op: String,
    val payload: String,
    val ts: Long = now(),
)

/**
 * Maps a foreign uid onto the local uid of the same logical row.
 *
 * Two installations can create the same natural row independently (seeded
 * roles, a project code typed on both). They merge on the natural key but each
 * keeps its own uid; the alias keeps the other side's foreign keys resolvable.
 */
@Entity(
    tableName = "sync_uid_alias",
    indices = [Index(value = ["entity", "foreign_uid"], unique = true)],
)
data class UidAliasRow(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val entity: String,
    @ColumnInfo(name = "foreign_uid") val foreignUid: String,
    @ColumnInfo(name = "local_uid") val localUid: String,
    @ColumnInfo(name = "created_at") val createdAt: Long = now(),
)

@Entity(tableName = "sync_state")
data class SyncStateRow(
    @PrimaryKey val id: Long = 1,
    @ColumnInfo(name = "device_id") val deviceId: String = newUid().take(16),
    @ColumnInfo(name = "device_name") val deviceName: String = "",
    val cursor: String = "",
    @ColumnInfo(name = "last_push_at") val lastPushAt: Long? = null,
    @ColumnInfo(name = "last_pull_at") val lastPullAt: Long? = null,
    @ColumnInfo(name = "last_error") val lastError: String = "",
    @ColumnInfo(name = "pushed_total") val pushedTotal: Int = 0,
    @ColumnInfo(name = "pulled_total") val pulledTotal: Int = 0,
)
