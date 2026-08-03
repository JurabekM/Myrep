package uz.dehqonkomakchi.app.data.repo

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import uz.dehqonkomakchi.app.data.db.dao.ExpenseDao
import uz.dehqonkomakchi.app.data.db.dao.HarvestDao
import uz.dehqonkomakchi.app.data.db.dao.SaleDao
import uz.dehqonkomakchi.app.data.db.entity.ExpenseEntity
import uz.dehqonkomakchi.app.data.db.entity.HarvestEntity
import uz.dehqonkomakchi.app.data.db.entity.SaleEntity
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

data class LedgerSummary(
    val totalExpense: Double,
    val totalRevenue: Double,
    val totalHarvestKg: Double,
) {
    val profit: Double get() = totalRevenue - totalExpense
    val costPerKg: Double? get() = if (totalHarvestKg > 0) totalExpense / totalHarvestKg else null
}

@Singleton
class LedgerRepository @Inject constructor(
    private val expenseDao: ExpenseDao,
    private val harvestDao: HarvestDao,
    private val saleDao: SaleDao,
) {
    fun observeExpenses(): Flow<List<ExpenseEntity>> = expenseDao.observeAll()
    fun observeHarvests(): Flow<List<HarvestEntity>> = harvestDao.observeAll()
    fun observeSales(): Flow<List<SaleEntity>> = saleDao.observeAll()

    fun observeSummary(): Flow<LedgerSummary> = combine(
        expenseDao.observeTotal(),
        saleDao.observeTotalRevenue(),
        harvestDao.observeTotalQuantity(),
    ) { expense, revenue, harvestKg ->
        LedgerSummary(totalExpense = expense, totalRevenue = revenue, totalHarvestKg = harvestKg)
    }

    suspend fun addExpense(category: String, amount: Double, note: String, dateEpochDay: Long) {
        expenseDao.insert(
            ExpenseEntity(
                id = UUID.randomUUID().toString(),
                category = category,
                amount = amount,
                note = note,
                dateEpochDay = dateEpochDay,
                createdAtEpochMillis = System.currentTimeMillis(),
            ),
        )
    }

    suspend fun addHarvest(quantity: Double, unit: String, dateEpochDay: Long) {
        harvestDao.insert(
            HarvestEntity(
                id = UUID.randomUUID().toString(),
                quantity = quantity,
                unit = unit,
                dateEpochDay = dateEpochDay,
                createdAtEpochMillis = System.currentTimeMillis(),
            ),
        )
    }

    suspend fun addSale(product: String, quantity: Double, price: Double, buyerType: String, dateEpochDay: Long) {
        saleDao.insert(
            SaleEntity(
                id = UUID.randomUUID().toString(),
                product = product,
                quantity = quantity,
                price = price,
                buyerType = buyerType,
                dateEpochDay = dateEpochDay,
                createdAtEpochMillis = System.currentTimeMillis(),
            ),
        )
    }

    suspend fun deleteExpense(entity: ExpenseEntity) = expenseDao.delete(entity)
    suspend fun deleteHarvest(entity: HarvestEntity) = harvestDao.delete(entity)
    suspend fun deleteSale(entity: SaleEntity) = saleDao.delete(entity)

    /** Builds a CSV string covering all three ledgers; caller decides where to write it. */
    suspend fun buildCsvExport(): String {
        val sb = StringBuilder()
        sb.appendLine("turi,sana,kategoriya_yoki_mahsulot,miqdor,narx_yoki_summasi,birlik_yoki_xaridor,izoh")

        expenseDao.observeAll().first().forEach { e ->
            sb.appendLine("xarajat,${e.dateEpochDay},${e.category},,${e.amount},,${e.note.replace(",", ";")}")
        }
        harvestDao.observeAll().first().forEach { h ->
            sb.appendLine("hosil,${h.dateEpochDay},,${h.quantity},,${h.unit},")
        }
        saleDao.observeAll().first().forEach { s ->
            sb.appendLine("sotuv,${s.dateEpochDay},${s.product},${s.quantity},${s.price},${s.buyerType},")
        }
        return sb.toString()
    }
}
