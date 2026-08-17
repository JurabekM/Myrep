package com.uzerp.mobile.data.repository

import androidx.room.withTransaction
import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.ValidationException
import com.uzerp.mobile.core.d
import com.uzerp.mobile.data.local.AppDatabase
import com.uzerp.mobile.data.local.dao.PaymentDao
import com.uzerp.mobile.data.local.dao.SequenceDao
import com.uzerp.mobile.data.local.entity.PaymentEntity
import java.math.BigDecimal
import java.time.Year
import javax.inject.Inject
import javax.inject.Singleton

val PAYMENT_METHODS = listOf("cash" to "Naqd", "card" to "Karta", "click" to "Click", "payme" to "Payme", "bank" to "Bank")
private const val CASH_CODE = "5010"
private const val BANK_CODE = "5110"

data class CashFlowResult(
    val dateFrom: String,
    val dateTo: String,
    val inflow: BigDecimal,
    val outflow: BigDecimal,
    val net: BigDecimal,
    val cashBalance: BigDecimal,
    val bankBalance: BigDecimal,
)

/**
 * To'lovlar servisi — Python `PaymentService` bilan bir xil: har to'lov
 * kassa kitobi yozuvi + jurnal o'tkazmasi + hujjat holati yangilanishi.
 */
@Singleton
class PaymentRepository @Inject constructor(
    private val db: AppDatabase,
    private val paymentDao: PaymentDao,
    private val sequenceDao: SequenceDao,
    private val accountingRepository: AccountingRepository,
    private val salesRepository: SalesRepository,
    private val purchaseRepository: PurchaseRepository,
) {
    private fun moneyAccountCode(method: String): String = if (method == "cash") CASH_CODE else BANK_CODE

    suspend fun createPayment(
        paymentType: String,
        amount: BigDecimal,
        method: String = "cash",
        corrAccountCode: String? = null,
        partnerType: String = "",
        partnerId: Long? = null,
        refType: String = "",
        refId: Long? = null,
        note: String = "",
        userId: Long? = null,
    ): Long {
        if (paymentType !in setOf("in", "out")) throw ValidationException("Noma'lum to'lov turi: $paymentType")
        val pay = d(amount)
        if (pay <= BigDecimal.ZERO) throw ValidationException("To'lov summasi musbat bo'lishi kerak.")
        val moneyCode = moneyAccountCode(method)
        val moneyAccount = accountingRepository.accountByCode(moneyCode)
        val corrAccount = corrAccountCode?.let { accountingRepository.accountByCode(it) }

        var paymentId = 0L
        db.withTransaction {
            val year = Year.now().value
            val number = "PAY-$year-%06d".format(sequenceDao.next("PAY", year))
            paymentId = paymentDao.insert(
                PaymentEntity(
                    number = number, paymentType = paymentType, method = method,
                    accountId = moneyAccount.id, corrAccountId = corrAccount?.id,
                    partnerType = partnerType, partnerId = partnerId,
                    refType = refType, refId = refId, amount = pay,
                    paymentDate = DateUtils.todayStr(), note = note, userId = userId,
                    createdAt = DateUtils.nowStr(),
                ),
            )
            if (corrAccount != null) {
                val lines = if (paymentType == "in") {
                    listOf(
                        JournalLineInput(moneyCode, debit = pay),
                        JournalLineInput(corrAccount.code, credit = pay, partnerType = partnerType, partnerId = partnerId),
                    )
                } else {
                    listOf(
                        JournalLineInput(corrAccount.code, debit = pay, partnerType = partnerType, partnerId = partnerId),
                        JournalLineInput(moneyCode, credit = pay),
                    )
                }
                accountingRepository.createEntry(
                    "To'lov $number" + (if (note.isNotBlank()) " ($note)" else ""),
                    lines, DateUtils.todayStr(), "payment", paymentId, userId,
                )
            }
        }
        return paymentId
    }

    suspend fun receiveForSale(docId: Long, amount: BigDecimal, method: String, userId: Long?): Long {
        val doc = salesRepository.getDoc(docId).doc
        val paymentId = createPayment(
            "in", amount, method, "4010", "customer", doc.customerId, "sale", docId,
            "${doc.number} bo'yicha to'lov", userId,
        )
        salesRepository.registerPayment(docId, amount, userId)
        return paymentId
    }

    suspend fun payForPurchase(purchaseId: Long, amount: BigDecimal, method: String, userId: Long?): Long {
        val doc = purchaseRepository.get(purchaseId).purchase
        val paymentId = createPayment(
            "out", amount, method, "6010", "supplier", doc.supplierId, "purchase", purchaseId,
            "${doc.number} bo'yicha to'lov", userId,
        )
        purchaseRepository.registerPayment(purchaseId, amount, userId)
        return paymentId
    }

    suspend fun expense(amount: BigDecimal, note: String, method: String = "cash", expenseAccountCode: String = "9410", userId: Long? = null): Long =
        createPayment("out", amount, method, expenseAccountCode, refType = "expense", note = note, userId = userId)

    suspend fun otherIncome(amount: BigDecimal, note: String, method: String = "cash", incomeAccountCode: String = "9010", userId: Long? = null): Long =
        createPayment("in", amount, method, incomeAccountCode, refType = "income", note = note, userId = userId)

    suspend fun cashBalance(): BigDecimal = accountingRepository.accountBalance(CASH_CODE)
    suspend fun bankBalance(): BigDecimal = accountingRepository.accountBalance(BANK_CODE)

    suspend fun cashbook(page: Int = 1, method: String? = null, paymentType: String? = null): PageResult<PaymentEntity> {
        val offset = (page - 1) * PAGE_SIZE
        return PageResult(paymentDao.search(method, paymentType, PAGE_SIZE, offset), page, PAGE_SIZE, Int.MAX_VALUE)
    }

    suspend fun cashFlow(dateFrom: String, dateTo: String): CashFlowResult {
        // Sodda mobil versiya: umumiy naqd/bank aylanmasi (sana filtri
        // hozircha jami hisobga olinadi — batafsil davr kesimi keyingi
        // bosqichda kengaytiriladi).
        val cashNet = paymentDao.cashNet()
        val bankNet = paymentDao.bankNet()
        return CashFlowResult(
            dateFrom, dateTo,
            inflow = BigDecimal.ZERO, outflow = BigDecimal.ZERO, net = d(cashNet.add(bankNet)),
            cashBalance = cashBalance(), bankBalance = bankBalance(),
        )
    }
}
