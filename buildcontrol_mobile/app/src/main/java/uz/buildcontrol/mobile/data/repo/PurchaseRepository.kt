package uz.buildcontrol.mobile.data.repo

import androidx.room.withTransaction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import uz.buildcontrol.mobile.data.db.BcDatabase
import uz.buildcontrol.mobile.data.db.PurchaseRequestRow
import uz.buildcontrol.mobile.data.db.SupplierQuoteRow
import uz.buildcontrol.mobile.data.db.now
import uz.buildcontrol.mobile.data.sync.SyncRecorder
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.Perm
import uz.buildcontrol.mobile.domain.PermissionDenied
import uz.buildcontrol.mobile.domain.PurchaseStatus

class PurchaseRuleException(val key: String) : Exception(key)

/** Purchase requests and supplier quotes. */
class PurchaseRepository(
    private val db: BcDatabase,
    private val recorder: SyncRecorder,
    private val auth: AuthRepository,
) {
    private val dao = db.dao()

    /** Quote enriched with the ranking flags shown in the interface. */
    data class RankedQuote(
        val quote: SupplierQuoteRow,
        val totalValue: Double,
        val isCheapest: Boolean = false,
        val isFastest: Boolean = false,
        val isBest: Boolean = false,
    )

    fun observeRequests(projectId: Long?): Flow<List<PurchaseRequestRow>> =
        dao.observeRequests(projectId)

    fun observeQuotes(requestId: Long): Flow<List<SupplierQuoteRow>> = dao.observeQuotes(requestId)

    suspend fun quotes(request: PurchaseRequestRow): List<RankedQuote> =
        withContext(Dispatchers.IO) { rank(dao.quotes(request.id), request.quantity) }

    /**
     * "Best" balances price and lead time with the desktop weights:
     * `0.7 * price + 0.3 * time`, lower is better.
     */
    fun rank(quotes: List<SupplierQuoteRow>, quantity: Double): List<RankedQuote> {
        if (quotes.isEmpty()) return emptyList()
        val totals = quotes.associateWith { it.totalValue(quantity) }
        val minTotal = totals.values.min()
        val maxTotal = totals.values.max()
        val minDays = quotes.minOf { it.deliveryDays }
        val maxDays = quotes.maxOf { it.deliveryDays }
        val spanTotal = (maxTotal - minTotal).takeIf { it != 0.0 } ?: 1.0
        val spanDays = (maxDays - minDays).takeIf { it != 0 }?.toDouble() ?: 1.0

        var best: SupplierQuoteRow? = null
        var bestScore = Double.MAX_VALUE
        for (quote in quotes) {
            val score = 0.7 * ((totals.getValue(quote) - minTotal) / spanTotal) +
                0.3 * ((quote.deliveryDays - minDays) / spanDays)
            if (score < bestScore) {
                bestScore = score
                best = quote
            }
        }
        return quotes.map { quote ->
            RankedQuote(
                quote = quote,
                totalValue = totals.getValue(quote),
                isCheapest = totals.getValue(quote) == minTotal,
                isFastest = quote.deliveryDays == minDays,
                isBest = quote === best,
            )
        }.sortedBy { it.totalValue }
    }

    /**
     * A request must reference an estimate item unless it is explicitly flagged
     * as an off-estimate purchase — the same rule the desktop enforces.
     */
    suspend fun saveRequest(actor: CurrentUser, row: PurchaseRequestRow): Long =
        withContext(Dispatchers.IO) {
            if (!actor.can(Perm.PURCHASE_EDIT)) throw PermissionDenied(Perm.PURCHASE_EDIT)
            if (row.estimateItemId == null && !row.offEstimate) {
                throw PurchaseRuleException("estimate_item_required")
            }
            db.withTransaction {
                val stamped = row.copy(syncTs = now(), updatedAt = now())
                val id: Long
                if (stamped.id == 0L) {
                    val numbered = stamped.copy(
                        number = stamped.number?.ifBlank { nextNumber() } ?: nextNumber()
                    )
                    id = dao.insert(numbered)
                    recorder.upsert("PurchaseRequest", numbered.uid)
                } else {
                    dao.update(stamped)
                    recorder.upsert("PurchaseRequest", stamped.uid)
                    id = stamped.id
                }
                auth.audit(
                    actor, if (row.id == 0L) "create" else "update",
                    "PurchaseRequest", id, stamped.projectId, stamped.title,
                )
                id
            }
        }

    /** Mobile-issued numbers use an `M` marker so they never clash with desktop ones. */
    private suspend fun nextNumber(): String = "XT-M%05d".format(dao.requestCount() + 1)

    suspend fun setStatus(actor: CurrentUser, request: PurchaseRequestRow, status: String) =
        withContext(Dispatchers.IO) {
            val permission =
                if (status in listOf(PurchaseStatus.APPROVED, PurchaseStatus.REJECTED)) {
                    Perm.PURCHASE_APPROVE
                } else {
                    Perm.PURCHASE_EDIT
                }
            if (!actor.can(permission)) throw PermissionDenied(permission)
            db.withTransaction {
                val updated = request.copy(status = status, syncTs = now(), updatedAt = now())
                dao.update(updated)
                recorder.upsert("PurchaseRequest", updated.uid)
                auth.audit(
                    actor,
                    when (status) {
                        PurchaseStatus.APPROVED -> "approve"
                        PurchaseStatus.REJECTED -> "reject"
                        else -> "update"
                    },
                    "PurchaseRequest", request.id, request.projectId, request.title,
                    request.status, status,
                )
            }
        }

    suspend fun saveQuote(actor: CurrentUser, row: SupplierQuoteRow): Long =
        withContext(Dispatchers.IO) {
            if (!actor.can(Perm.PURCHASE_EDIT)) throw PermissionDenied(Perm.PURCHASE_EDIT)
            db.withTransaction {
                val stamped = row.copy(syncTs = now(), updatedAt = now())
                if (stamped.id == 0L) {
                    val id = dao.insert(stamped)
                    recorder.upsert("SupplierQuote", stamped.uid)
                    id
                } else {
                    dao.update(stamped)
                    recorder.upsert("SupplierQuote", stamped.uid)
                    stamped.id
                }
            }
        }

    suspend fun selectQuote(actor: CurrentUser, requestId: Long, quoteId: Long) =
        withContext(Dispatchers.IO) {
            if (!actor.can(Perm.PURCHASE_EDIT)) throw PermissionDenied(Perm.PURCHASE_EDIT)
            db.withTransaction {
                for (quote in dao.quotes(requestId)) {
                    val selected = quote.id == quoteId
                    if (quote.isSelected != selected) {
                        val updated =
                            quote.copy(isSelected = selected, syncTs = now(), updatedAt = now())
                        dao.update(updated)
                        recorder.upsert("SupplierQuote", updated.uid)
                    }
                }
            }
        }
}
