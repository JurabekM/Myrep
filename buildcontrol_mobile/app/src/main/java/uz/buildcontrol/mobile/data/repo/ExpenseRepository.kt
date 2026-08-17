package uz.buildcontrol.mobile.data.repo

import androidx.room.withTransaction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import uz.buildcontrol.mobile.data.db.BcDatabase
import uz.buildcontrol.mobile.data.db.CounterpartyRow
import uz.buildcontrol.mobile.data.db.ExpenseRow
import uz.buildcontrol.mobile.data.db.PaymentRow
import uz.buildcontrol.mobile.data.db.now
import uz.buildcontrol.mobile.data.sync.SyncRecorder
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.ExpenseStatus
import uz.buildcontrol.mobile.domain.Perm
import uz.buildcontrol.mobile.domain.PermissionDenied
import uz.buildcontrol.mobile.domain.computeRating

/** Expenses, their approval workflow and payments. */
class ExpenseRepository(
    private val db: BcDatabase,
    private val recorder: SyncRecorder,
    private val estimates: EstimateRepository,
    private val projects: ProjectRepository,
    private val auth: AuthRepository,
) {
    private val dao = db.dao()

    fun observeExpenses(projectId: Long?, status: String): Flow<List<ExpenseRow>> =
        dao.observeExpenses(projectId, status)

    suspend fun paid(expenseId: Long): Double = withContext(Dispatchers.IO) {
        dao.paidTotal(expenseId)
    }

    suspend fun save(actor: CurrentUser, row: ExpenseRow): Long = withContext(Dispatchers.IO) {
        if (!actor.can(Perm.EXPENSE_EDIT)) throw PermissionDenied(Perm.EXPENSE_EDIT)
        val id = db.withTransaction {
            val stamped = row.copy(syncTs = now(), updatedAt = now())
            val newId: Long
            if (stamped.id == 0L) {
                val created = stamped.copy(
                    createdById = actor.id,
                    status = ExpenseStatus.PENDING,
                )
                newId = dao.insert(created)
                recorder.upsert("Expense", created.uid)
            } else {
                dao.update(stamped)
                recorder.upsert("Expense", stamped.uid)
                newId = stamped.id
            }
            auth.audit(
                actor, if (row.id == 0L) "create" else "update", "Expense", newId,
                stamped.projectId, "${stamped.category}: ${stamped.note.orEmpty()}",
                newValue = "${stamped.amount}/${stamped.status}",
            )
            newId
        }
        row.projectId?.let { estimates.recalcActuals(it) }
        id
    }

    /** Approving requires `expense.approve`, so estimators cannot sign off their own entries. */
    suspend fun setStatus(actor: CurrentUser, expense: ExpenseRow, status: String) =
        withContext(Dispatchers.IO) {
            if (!actor.can(Perm.EXPENSE_APPROVE)) throw PermissionDenied(Perm.EXPENSE_APPROVE)
            db.withTransaction {
                val updated = expense.copy(
                    status = status,
                    approvedById = if (status in ExpenseStatus.counted) actor.id else expense.approvedById,
                    approvedAt = if (status in ExpenseStatus.counted) now() else expense.approvedAt,
                    syncTs = now(),
                    updatedAt = now(),
                )
                dao.update(updated)
                recorder.upsert("Expense", updated.uid)
                auth.audit(
                    actor,
                    when (status) {
                        ExpenseStatus.APPROVED -> "approve"
                        ExpenseStatus.PAID -> "payment"
                        ExpenseStatus.REJECTED -> "reject"
                        else -> "update"
                    },
                    "Expense", expense.id, expense.projectId,
                    "${expense.amount} (${expense.category})", expense.status, status,
                )
            }
            expense.projectId?.let { estimates.recalcActuals(it) }
        }

    suspend fun addPayment(actor: CurrentUser, expense: ExpenseRow, amount: Double, method: String) =
        withContext(Dispatchers.IO) {
            if (!actor.can(Perm.EXPENSE_APPROVE)) throw PermissionDenied(Perm.EXPENSE_APPROVE)
            db.withTransaction {
                val payment = PaymentRow(
                    expenseId = expense.id,
                    amount = amount,
                    payDate = uz.buildcontrol.mobile.core.Fmt.today(),
                    method = method,
                    createdById = actor.id,
                )
                dao.insert(payment)
                recorder.upsert("Payment", payment.uid)

                val total = dao.paidTotal(expense.id)
                if (total >= expense.amount - 0.01) {
                    val closed = expense.copy(
                        status = ExpenseStatus.PAID,
                        approvedById = expense.approvedById ?: actor.id,
                        approvedAt = expense.approvedAt ?: now(),
                        syncTs = now(),
                        updatedAt = now(),
                    )
                    dao.update(closed)
                    recorder.upsert("Expense", closed.uid)
                }
                auth.audit(
                    actor, "payment", "Payment", expense.id, expense.projectId,
                    "payment for expense #${expense.id}", newValue = amount.toString(),
                )
            }
            expense.projectId?.let { estimates.recalcActuals(it) }
        }

    /** The system warns but never blocks — the manager decides. */
    suspend fun wouldExceedBudget(projectId: Long, amount: Double): Boolean =
        withContext(Dispatchers.IO) {
            val totals = projects.totals(projectId)
            totals.plannedBudget > 0 && (totals.actual + amount) > totals.plannedBudget
        }
}

/** Suppliers and contractors. */
class CounterpartyRepository(
    private val db: BcDatabase,
    private val recorder: SyncRecorder,
) {
    private val dao = db.dao()

    fun observe(kind: String): Flow<List<CounterpartyRow>> = dao.observeCounterparties(kind)

    suspend fun all(): List<CounterpartyRow> = withContext(Dispatchers.IO) { dao.counterparties() }

    suspend fun save(actor: CurrentUser, row: CounterpartyRow): Long = withContext(Dispatchers.IO) {
        if (!actor.can(Perm.COUNTERPARTY_EDIT)) throw PermissionDenied(Perm.COUNTERPARTY_EDIT)
        db.withTransaction {
            val rated = row.copy(
                rating = computeRating(
                    row.delayDays, row.contractAmount, row.paidAmount, row.qualityScore, row.disputes
                ),
                syncTs = now(),
                updatedAt = now(),
            )
            if (rated.id == 0L) {
                val id = dao.insert(rated)
                recorder.upsert("Counterparty", rated.uid)
                id
            } else {
                dao.update(rated)
                recorder.upsert("Counterparty", rated.uid)
                rated.id
            }
        }
    }
}
