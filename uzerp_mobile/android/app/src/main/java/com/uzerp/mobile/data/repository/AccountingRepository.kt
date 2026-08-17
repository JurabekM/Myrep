package com.uzerp.mobile.data.repository

import androidx.room.withTransaction
import com.uzerp.mobile.core.AppEvent
import com.uzerp.mobile.core.AppEventBus
import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.NotFoundException
import com.uzerp.mobile.core.ValidationException
import com.uzerp.mobile.core.d
import com.uzerp.mobile.data.local.AppDatabase
import com.uzerp.mobile.data.local.dao.AccountDao
import com.uzerp.mobile.data.local.dao.JournalDao
import com.uzerp.mobile.data.local.dao.JournalEntryWithAmount
import com.uzerp.mobile.data.local.dao.JournalLineWithAccount
import com.uzerp.mobile.data.local.dao.ProductDao
import com.uzerp.mobile.data.local.dao.TrialBalanceRow
import com.uzerp.mobile.data.local.entity.AccountEntity
import com.uzerp.mobile.data.local.entity.JournalEntryEntity
import com.uzerp.mobile.data.local.entity.JournalLineEntity
import java.math.BigDecimal
import java.time.Year
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

/** Debet-normal hisob turlari (qoldiq = debet - kredit). */
private val DEBIT_NORMAL = setOf("asset", "expense")

data class JournalLineInput(
    val accountCode: String,
    val debit: BigDecimal = BigDecimal.ZERO,
    val credit: BigDecimal = BigDecimal.ZERO,
    val partnerType: String = "",
    val partnerId: Long? = null,
)

data class JournalEntryDetail(val entry: JournalEntryEntity, val lines: List<JournalLineWithAccount>)

data class TrialBalanceEntry(
    val code: String,
    val name: String,
    val type: String,
    val totalDebit: BigDecimal,
    val totalCredit: BigDecimal,
    val balance: BigDecimal,
)

data class ProfitLossResult(
    val dateFrom: String,
    val dateTo: String,
    val income: List<Pair<AccountLabel, BigDecimal>>,
    val expenses: List<Pair<AccountLabel, BigDecimal>>,
    val totalIncome: BigDecimal,
    val totalExpense: BigDecimal,
    val netProfit: BigDecimal,
)

data class AccountLabel(val code: String, val name: String)

data class BalanceSheetResult(
    val dateTo: String,
    val assets: List<TrialBalanceEntry>,
    val liabilities: List<TrialBalanceEntry>,
    val equity: List<TrialBalanceEntry>,
    val totalAssets: BigDecimal,
    val totalLiabilities: BigDecimal,
    val totalEquity: BigDecimal,
    val balanced: Boolean,
)

data class VatReportResult(
    val dateFrom: String,
    val dateTo: String,
    val outputVat: BigDecimal,
    val inputVat: BigDecimal,
    val payable: BigDecimal,
)

/**
 * Buxgalteriya servisi — Python `AccountingService` bilan bir xil: dvoyna
 * zapis (debet=kredit majburiy), NAS-21 hisoblar rejasi, savdo/xarid
 * tasdiqlanganda avtomatik o'tkazmalar ([AppEventBus] orqali — Observer
 * pattern, savdo/ombor modullari buxgalteriyani bilishi shart emas).
 */
@Singleton
class AccountingRepository @Inject constructor(
    private val db: AppDatabase,
    private val accountDao: AccountDao,
    private val journalDao: JournalDao,
    private val productDao: ProductDao,
    private val salesRepository: SalesRepository,
    private val purchaseRepository: PurchaseRepository,
    private val eventBus: AppEventBus,
) {
    /**
     * Hodisalarga obuna bo'lishni boshlaydi — ilova ishga tushganda
     * ([com.uzerp.mobile.UzErpApplication] dan) bir marta chaqiriladi,
     * shunda savdo/xarid tasdiqlanishi doim avto-o'tkazma bilan kuzatiladi.
     */
    fun startListening(scope: CoroutineScope) {
        scope.launch {
            eventBus.events.collect { event ->
                when (event) {
                    is AppEvent.SaleConfirmed -> handleSaleConfirmed(event)
                    is AppEvent.PurchaseReceived -> handlePurchaseReceived(event)
                    else -> Unit
                }
            }
        }
    }

    // ------------------------------------------------------------------ //
    //  Hisoblar rejasi
    // ------------------------------------------------------------------ //

    fun accounts() = accountDao.observeAll()

    suspend fun accountByCode(code: String): AccountEntity =
        accountDao.getByCode(code) ?: throw NotFoundException("Hisob topilmadi (kod=$code).")

    suspend fun createAccount(code: String, name: String, type: String): Long {
        if (code.isBlank() || name.isBlank()) throw ValidationException("Hisob kodi va nomi bo'sh bo'lishi mumkin emas.")
        if (type !in setOf("asset", "contra_asset", "liability", "equity", "income", "expense")) {
            throw ValidationException("Noma'lum hisob turi: $type")
        }
        if (accountDao.getByCode(code) != null) throw ValidationException("$code kodli hisob allaqachon mavjud.")
        return accountDao.insert(AccountEntity(code = code, name = name, type = type))
    }

    // ------------------------------------------------------------------ //
    //  Jurnal o'tkazmalari
    // ------------------------------------------------------------------ //

    suspend fun createEntry(
        memo: String,
        lines: List<JournalLineInput>,
        entryDate: String? = null,
        refType: String = "",
        refId: Long? = null,
        userId: Long? = null,
    ): Long {
        if (lines.size < 2) throw ValidationException("O'tkazmada kamida ikkita satr bo'lishi kerak.")
        var totalDebit = BigDecimal.ZERO
        var totalCredit = BigDecimal.ZERO
        val resolved = lines.map { line ->
            val account = accountByCode(line.accountCode)
            val debit = d(line.debit)
            val credit = d(line.credit)
            if (debit < BigDecimal.ZERO || credit < BigDecimal.ZERO) {
                throw ValidationException("Debet/kredit manfiy bo'lishi mumkin emas.")
            }
            if ((debit > BigDecimal.ZERO) == (credit > BigDecimal.ZERO)) {
                throw ValidationException("Har bir satrda faqat debet YOKI kredit bo'lishi kerak.")
            }
            totalDebit = d(totalDebit.add(debit))
            totalCredit = d(totalCredit.add(credit))
            Triple(account.id, debit, credit) to line
        }
        if (totalDebit != totalCredit) {
            throw ValidationException("Balans buzildi: debet $totalDebit != kredit $totalCredit.")
        }
        if (totalDebit == BigDecimal.ZERO) throw ValidationException("O'tkazma summasi nolga teng bo'lishi mumkin emas.")

        var entryId = 0L
        db.withTransaction {
            val year = Year.now().value
            val number = "JRN-$year-%06d".format(
                db.sequenceDao().next("JRN", year),
            )
            entryId = journalDao.insertEntry(
                JournalEntryEntity(
                    number = number,
                    entryDate = entryDate ?: DateUtils.todayStr(),
                    memo = memo,
                    refType = refType,
                    refId = refId,
                    userId = userId,
                    createdAt = DateUtils.nowStr(),
                ),
            )
            for ((triple, line) in resolved) {
                val (accountId, debit, credit) = triple
                journalDao.insertLine(
                    JournalLineEntity(
                        entryId = entryId, accountId = accountId, debit = debit, credit = credit,
                        partnerType = line.partnerType, partnerId = line.partnerId,
                    ),
                )
            }
        }
        return entryId
    }

    suspend fun getEntry(entryId: Long): JournalEntryDetail {
        val entry = journalDao.getEntryById(entryId) ?: throw NotFoundException("O'tkazma topilmadi (id=$entryId).")
        return JournalEntryDetail(entry, journalDao.linesForEntry(entryId))
    }

    suspend fun listEntries(page: Int = 1, dateFrom: String? = null, dateTo: String? = null): PageResult<JournalEntryWithAmount> {
        val offset = (page - 1) * PAGE_SIZE
        return PageResult(journalDao.search(dateFrom, dateTo, PAGE_SIZE, offset), page, PAGE_SIZE, Int.MAX_VALUE)
    }

    // ------------------------------------------------------------------ //
    //  Qoldiqlar va hisobotlar
    // ------------------------------------------------------------------ //

    suspend fun accountBalance(code: String, dateTo: String? = null): BigDecimal {
        val account = accountByCode(code)
        val debit = accountDao.sumDebit(account.id, dateTo)
        val credit = accountDao.sumCredit(account.id, dateTo)
        return if (account.type in DEBIT_NORMAL) d(debit.subtract(credit)) else d(credit.subtract(debit))
    }

    suspend fun trialBalance(dateTo: String? = null): List<TrialBalanceEntry> =
        journalDao.trialBalanceRaw(dateTo).map { row: TrialBalanceRow ->
            val balance = if (row.type in DEBIT_NORMAL) {
                d(row.totalDebit.subtract(row.totalCredit))
            } else {
                d(row.totalCredit.subtract(row.totalDebit))
            }
            TrialBalanceEntry(row.code, row.name, row.type, row.totalDebit, row.totalCredit, balance)
        }

    suspend fun profitLoss(dateFrom: String, dateTo: String): ProfitLossResult {
        val rows = journalDao.profitLossRaw(dateFrom, dateTo)
        val income = mutableListOf<Pair<AccountLabel, BigDecimal>>()
        val expenses = mutableListOf<Pair<AccountLabel, BigDecimal>>()
        var totalIncome = BigDecimal.ZERO
        var totalExpense = BigDecimal.ZERO
        for (row in rows) {
            if (row.type == "income") {
                val amount = d(row.netCredit)
                totalIncome = d(totalIncome.add(amount))
                income.add(AccountLabel(row.code, row.name) to amount)
            } else {
                val amount = d(row.netCredit.negate())
                totalExpense = d(totalExpense.add(amount))
                expenses.add(AccountLabel(row.code, row.name) to amount)
            }
        }
        return ProfitLossResult(dateFrom, dateTo, income, expenses, totalIncome, totalExpense, d(totalIncome.subtract(totalExpense)))
    }

    suspend fun balanceSheet(dateTo: String? = null): BalanceSheetResult {
        val effectiveDate = dateTo ?: DateUtils.todayStr()
        val tb = trialBalance(effectiveDate)
        val assets = mutableListOf<TrialBalanceEntry>()
        val liabilities = mutableListOf<TrialBalanceEntry>()
        val equity = mutableListOf<TrialBalanceEntry>()
        var totalAssets = BigDecimal.ZERO
        var totalLiabilities = BigDecimal.ZERO
        var totalEquity = BigDecimal.ZERO
        var netProfit = BigDecimal.ZERO

        for (row in tb) {
            when (row.type) {
                "asset" -> {
                    if (row.balance.signum() != 0) assets.add(row)
                    totalAssets = d(totalAssets.add(row.balance))
                }
                "contra_asset" -> {
                    if (row.balance.signum() != 0) assets.add(row.copy(balance = row.balance.negate()))
                    totalAssets = d(totalAssets.subtract(row.balance))
                }
                "liability" -> {
                    if (row.balance.signum() != 0) liabilities.add(row)
                    totalLiabilities = d(totalLiabilities.add(row.balance))
                }
                "equity" -> {
                    if (row.balance.signum() != 0) equity.add(row)
                    totalEquity = d(totalEquity.add(row.balance))
                }
                "income" -> netProfit = d(netProfit.add(row.balance))
                "expense" -> netProfit = d(netProfit.subtract(row.balance))
            }
        }
        if (netProfit.signum() != 0) {
            equity.add(TrialBalanceEntry("----", "Joriy davr sof foydasi", "equity", BigDecimal.ZERO, BigDecimal.ZERO, netProfit))
        }
        totalEquity = d(totalEquity.add(netProfit))

        return BalanceSheetResult(
            effectiveDate, assets, liabilities, equity, totalAssets, totalLiabilities, totalEquity,
            balanced = totalAssets == d(totalLiabilities.add(totalEquity)),
        )
    }

    suspend fun vatReport(dateFrom: String, dateTo: String): VatReportResult {
        val output = d(db.salesDocDao().outputVat(dateFrom, dateTo))
        val input = d(db.purchaseDao().inputVat(dateFrom, dateTo))
        return VatReportResult(dateFrom, dateTo, output, input, d(output.subtract(input)))
    }

    // ------------------------------------------------------------------ //
    //  Avto-o'tkazmalar (hodisa ishlovchilari)
    // ------------------------------------------------------------------ //

    private suspend fun handleSaleConfirmed(event: AppEvent.SaleConfirmed) {
        if (event.docType !in setOf("invoice", "pos", "return")) return
        val detail = salesRepository.getDoc(event.docId)
        val doc = detail.doc
        val vat = d(doc.vatAmount)
        val total = d(doc.total)
        val net = d(total.subtract(vat))

        var cost = BigDecimal.ZERO
        for (item in detail.items) {
            val product = productDao.getById(item.productId) ?: continue
            cost = d(cost.add(item.quantity.multiply(product.costPrice)))
        }

        if (event.docType == "return") {
            val lines = buildList {
                add(JournalLineInput("9010", debit = net))
                if (vat.signum() > 0) add(JournalLineInput("6520", debit = vat))
                add(JournalLineInput("4010", credit = total, partnerType = "customer", partnerId = doc.customerId))
            }
            createEntry("Qaytarish ${doc.number}", lines, doc.docDate, "sale_return", event.docId, event.userId)
            if (cost.signum() > 0) {
                createEntry(
                    "Qaytarish tannarxi ${doc.number}",
                    listOf(JournalLineInput("2900", debit = cost), JournalLineInput("9110", credit = cost)),
                    doc.docDate, "sale_return_cogs", event.docId, event.userId,
                )
            }
            return
        }

        val lines = buildList {
            add(JournalLineInput("4010", debit = total, partnerType = "customer", partnerId = doc.customerId))
            add(JournalLineInput("9010", credit = net))
            if (vat.signum() > 0) add(JournalLineInput("6520", credit = vat))
        }
        createEntry("Savdo ${doc.number}", lines, doc.docDate, "sale", event.docId, event.userId)
        if (cost.signum() > 0) {
            createEntry(
                "Tannarx ${doc.number}",
                listOf(JournalLineInput("9110", debit = cost), JournalLineInput("2900", credit = cost)),
                doc.docDate, "sale_cogs", event.docId, event.userId,
            )
        }
    }

    private suspend fun handlePurchaseReceived(event: AppEvent.PurchaseReceived) {
        val detail = purchaseRepository.get(event.purchaseId)
        val doc = detail.purchase
        val total = d(doc.total)
        val vat = d(doc.vatAmount)
        val net = d(total.subtract(vat))

        val lines = buildList {
            add(JournalLineInput("2900", debit = net))
            if (vat.signum() > 0) add(JournalLineInput("4410", debit = vat))
            add(JournalLineInput("6010", credit = total, partnerType = "supplier", partnerId = doc.supplierId))
        }
        createEntry("Xarid ${doc.number}", lines, doc.docDate, "purchase", event.purchaseId, event.userId)
    }
}
