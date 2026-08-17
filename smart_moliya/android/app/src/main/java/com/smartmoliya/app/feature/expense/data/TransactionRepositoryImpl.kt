package com.smartmoliya.app.feature.expense.data

import android.util.Log
import com.smartmoliya.app.BuildConfig
import com.smartmoliya.app.core.database.dao.TransactionDao
import com.smartmoliya.app.core.database.dao.WalletDao
import com.smartmoliya.app.core.database.entity.TransactionEntity
import com.smartmoliya.app.core.network.ApiService
import com.smartmoliya.app.core.network.dto.TransactionCreateDto
import com.smartmoliya.app.feature.expense.domain.Transaction
import com.smartmoliya.app.feature.expense.domain.TransactionRepository
import com.smartmoliya.app.feature.expense.domain.TransactionType
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.util.UUID
import javax.inject.Inject

class TransactionRepositoryImpl @Inject constructor(
    private val api: ApiService,
    private val dao: TransactionDao,
    private val walletDao: WalletDao
) : TransactionRepository {

    override fun observeTransactions(): Flow<List<Transaction>> =
        dao.observeAll().map { entities -> entities.map { it.toDomain() } }

    override suspend fun refresh() {
        if (BuildConfig.OFFLINE_MODE) return
        val remote = api.listTransactions()
        remote.forEach { dao.upsert(it.toEntity()) }
    }

    override suspend fun addTransaction(
        walletId: String,
        categoryId: String?,
        type: TransactionType,
        amount: Double,
        note: String?
    ) {
        val id = UUID.randomUUID().toString()
        val occurredAt = System.currentTimeMillis()

        dao.upsert(
            TransactionEntity(
                id = id,
                walletId = walletId,
                categoryId = categoryId,
                type = type.name,
                amount = amount,
                currency = "UZS",
                note = note,
                source = "MANUAL",
                occurredAt = occurredAt,
                syncStatus = if (BuildConfig.OFFLINE_MODE) "SYNCED" else "PENDING",
                version = 1
            )
        )
        // Hamyon balansini darhol lokalda yangilaymiz (UI kutmasin). Online rejimda
        // server ham xuddi shu hisobni yuritadi va navbatdagi refresh'da tasdiqlanadi.
        applyBalanceChange(walletId, type, amount)

        if (BuildConfig.OFFLINE_MODE) return
        try {
            val created = api.createTransaction(
                TransactionCreateDto(
                    id = id,
                    wallet_id = walletId,
                    category_id = categoryId,
                    type = type.name.lowercase(),
                    amount = amount,
                    note = note,
                    occurred_at = millisToIso(occurredAt)
                )
            )
            dao.upsert(created.toEntity())
        } catch (e: Exception) {
            Log.w(TAG, "addTransaction: offline yoki server xatosi, keyinroq SyncWorker qayta urinadi", e)
        }
    }

    override suspend fun deleteTransaction(transactionId: String) {
        val existing = dao.getById(transactionId)
        dao.deleteById(transactionId)
        // O'chirilgan tranzaksiya balans ta'sirini teskari qaytaramiz
        if (existing != null) {
            val reverseType = when (existing.type) {
                TransactionType.INCOME.name -> TransactionType.EXPENSE
                TransactionType.EXPENSE.name -> TransactionType.INCOME
                else -> null
            }
            if (reverseType != null) {
                applyBalanceChange(existing.walletId, reverseType, existing.amount)
            }
        }

        if (BuildConfig.OFFLINE_MODE) return
        try {
            api.deleteTransaction(transactionId)
        } catch (e: Exception) {
            Log.w(TAG, "deleteTransaction: server bilan sinxronlanmadi", e)
        }
    }

    private suspend fun applyBalanceChange(walletId: String, type: TransactionType, amount: Double) {
        val wallet = walletDao.getById(walletId) ?: return
        val delta = when (type) {
            TransactionType.INCOME -> amount
            TransactionType.EXPENSE -> -amount
            TransactionType.TRANSFER -> 0.0
        }
        walletDao.upsert(
            wallet.copy(balance = wallet.balance + delta, updatedAt = System.currentTimeMillis())
        )
    }

    companion object {
        private const val TAG = "TransactionRepository"
    }
}
