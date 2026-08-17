package uz.buildcontrol.mobile.domain

/** Machine codes shared with the desktop database. */
object RoleCode {
    const val ADMIN = "admin"
    const val MANAGER = "manager"
    const val ESTIMATOR = "estimator"
    const val STOREKEEPER = "storekeeper"
    const val VIEWER = "viewer"
    val all = listOf(ADMIN, MANAGER, ESTIMATOR, STOREKEEPER, VIEWER)
}

object ProjectStatus {
    const val PLANNED = "planned"
    const val ACTIVE = "active"
    const val SUSPENDED = "suspended"
    const val COMPLETED = "completed"
    const val ARCHIVED = "archived"
    val all = listOf(PLANNED, ACTIVE, SUSPENDED, COMPLETED, ARCHIVED)
}

object ProjectType {
    val all = listOf("new_build", "renovation", "interior", "facade", "other")
}

object EstimateStatus {
    const val DRAFT = "draft"
    const val SUBMITTED = "submitted"
    const val APPROVED = "approved"
    const val REVISION = "revision"
    val editable = setOf(DRAFT, REVISION)
}

object ItemStatus {
    const val PLANNED = "planned"
    const val IN_PROGRESS = "in_progress"
    const val NEEDS_PURCHASE = "needs_purchase"
    const val DONE = "done"
    const val CANCELLED = "cancelled"
    val all = listOf(PLANNED, IN_PROGRESS, NEEDS_PURCHASE, DONE, CANCELLED)
}

object Units {
    val all = listOf("piece", "kg", "ton", "m", "m2", "m3", "hour", "day", "service", "liter", "set")
}

object PurchaseStatus {
    const val DRAFT = "draft"
    const val SUBMITTED = "submitted"
    const val APPROVED = "approved"
    const val REJECTED = "rejected"
    const val ORDERED = "ordered"
    const val PARTIAL = "partial"
    const val COMPLETED = "completed"
    val all = listOf(DRAFT, SUBMITTED, APPROVED, REJECTED, ORDERED, PARTIAL, COMPLETED)
}

object TxKind {
    const val IN = "in"
    const val OUT = "out"
    const val RETURN = "return"
    const val ADJUST = "adjust"
    const val LOSS = "loss"
    val all = listOf(IN, OUT, RETURN, ADJUST, LOSS)
    val positive = setOf(IN, RETURN, ADJUST)
}

object StageStatus {
    const val NOT_STARTED = "not_started"
    const val IN_PROGRESS = "in_progress"
    const val REVIEW = "review"
    const val DELAYED = "delayed"
    const val DONE = "done"
    const val BLOCKED = "blocked"
    val all = listOf(NOT_STARTED, IN_PROGRESS, REVIEW, DELAYED, DONE, BLOCKED)
    val terminal = setOf(DONE, BLOCKED)
}

object ExpenseStatus {
    const val PENDING = "pending"
    const val APPROVED = "approved"
    const val PAID = "paid"
    const val REJECTED = "rejected"
    val all = listOf(PENDING, APPROVED, PAID, REJECTED)
    val counted = setOf(APPROVED, PAID)
}

object ExpenseCategory {
    val all = listOf("material", "labor", "equipment", "transport", "subcontract", "overhead", "other")
}

object PaymentMethod {
    val all = listOf("cash", "card", "transfer")
}

object CounterpartyKind {
    const val SUPPLIER = "supplier"
    const val CONTRACTOR = "contractor"
}

// --------------------------------------------------------------------------- //
// Permissions — mirrors app/services/permissions.py
// --------------------------------------------------------------------------- //

object Perm {
    const val PROJECT_VIEW = "project.view"
    const val PROJECT_EDIT = "project.edit"
    const val PROJECT_ARCHIVE = "project.archive"
    const val ESTIMATE_VIEW = "estimate.view"
    const val ESTIMATE_EDIT = "estimate.edit"
    const val ESTIMATE_APPROVE = "estimate.approve"
    const val PURCHASE_VIEW = "purchase.view"
    const val PURCHASE_EDIT = "purchase.edit"
    const val PURCHASE_APPROVE = "purchase.approve"
    const val WAREHOUSE_VIEW = "warehouse.view"
    const val WAREHOUSE_EDIT = "warehouse.edit"
    const val STAGE_VIEW = "stage.view"
    const val STAGE_EDIT = "stage.edit"
    const val COUNTERPARTY_VIEW = "counterparty.view"
    const val COUNTERPARTY_EDIT = "counterparty.edit"
    const val EXPENSE_VIEW = "expense.view"
    const val EXPENSE_EDIT = "expense.edit"
    const val EXPENSE_APPROVE = "expense.approve"
    const val REPORT_VIEW = "report.view"
    const val SETTINGS_MANAGE = "settings.manage"
    const val USER_MANAGE = "user.manage"
    const val AUDIT_VIEW = "audit.view"
}

private val viewOnly = setOf(
    Perm.PROJECT_VIEW, Perm.ESTIMATE_VIEW, Perm.PURCHASE_VIEW, Perm.WAREHOUSE_VIEW,
    Perm.STAGE_VIEW, Perm.COUNTERPARTY_VIEW, Perm.EXPENSE_VIEW, Perm.REPORT_VIEW,
)

val ROLE_PERMISSIONS: Map<String, Set<String>> = mapOf(
    RoleCode.ADMIN to setOf("*"),
    RoleCode.MANAGER to viewOnly + setOf(
        Perm.PROJECT_EDIT, Perm.PROJECT_ARCHIVE, Perm.ESTIMATE_EDIT, Perm.ESTIMATE_APPROVE,
        Perm.PURCHASE_EDIT, Perm.PURCHASE_APPROVE, Perm.WAREHOUSE_EDIT, Perm.STAGE_EDIT,
        Perm.COUNTERPARTY_EDIT, Perm.EXPENSE_EDIT, Perm.EXPENSE_APPROVE, Perm.AUDIT_VIEW,
    ),
    RoleCode.ESTIMATOR to viewOnly + setOf(
        Perm.ESTIMATE_EDIT, Perm.PURCHASE_EDIT, Perm.STAGE_EDIT, Perm.EXPENSE_EDIT,
        Perm.COUNTERPARTY_EDIT,
    ),
    RoleCode.STOREKEEPER to viewOnly + setOf(Perm.WAREHOUSE_EDIT, Perm.PURCHASE_EDIT),
    RoleCode.VIEWER to viewOnly,
)

fun hasPerm(roleCode: String, permission: String): Boolean {
    val perms = ROLE_PERMISSIONS[roleCode] ?: return false
    return "*" in perms || permission in perms
}

class PermissionDenied(val permission: String) : Exception("Permission denied: $permission")

/** Signed-in user snapshot held by the interface. */
data class CurrentUser(
    val id: Long,
    val uid: String,
    val username: String,
    val fullName: String,
    val roleCode: String,
) {
    val label: String get() = fullName.ifBlank { username }
    fun can(permission: String): Boolean = hasPerm(roleCode, permission)
}

// --------------------------------------------------------------------------- //
// Calculations — identical to the desktop formulas
// --------------------------------------------------------------------------- //

data class ProjectTotals(
    val plannedBudget: Double = 0.0,
    val estimateTotal: Double = 0.0,
    val committed: Double = 0.0,
    val pending: Double = 0.0,
    val materialIssued: Double = 0.0,
    val delayedStages: Int = 0,
    val totalStages: Int = 0,
    val doneStages: Int = 0,
    val pendingPurchases: Int = 0,
    val overBudgetItems: Int = 0,
    val avgProgress: Double = 0.0,
) {
    val actual: Double get() = committed + materialIssued
    val remaining: Double get() = plannedBudget - actual
    val usageRatio: Double get() = if (plannedBudget > 0) actual / plannedBudget else 0.0
    val isOverBudget: Boolean get() = plannedBudget > 0 && actual > plannedBudget
}

/** Contractor rating, 0..5 — same weights as `counterparty_service.compute_rating`. */
fun computeRating(
    delayDays: Int,
    contractAmount: Double,
    paidAmount: Double,
    qualityScore: Double,
    disputes: Int,
): Double {
    val timeliness = (5.0 - (maxOf(0, delayDays) / 10.0)).coerceAtLeast(0.0)
    val price = if (contractAmount > 0) {
        val overrun = ((paidAmount - contractAmount) / contractAmount).coerceAtLeast(0.0)
        (5.0 - overrun * 10.0).coerceAtLeast(0.0)
    } else 5.0
    val quality = qualityScore.coerceIn(0.0, 5.0)
    val disputeScore = (5.0 - 0.5 * maxOf(0, disputes)).coerceAtLeast(0.0)
    val rating = 0.4 * timeliness + 0.2 * price + 0.3 * quality + 0.1 * disputeScore
    return Math.round(rating.coerceIn(0.0, 5.0) * 100.0) / 100.0
}
