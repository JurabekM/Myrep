package com.uzerp.mobile.data.repository

import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.d
import com.uzerp.mobile.data.local.dao.CustomerDao
import com.uzerp.mobile.data.local.dao.DebtRow
import com.uzerp.mobile.data.local.dao.EmployeeDao
import com.uzerp.mobile.data.local.dao.LowStockRow
import com.uzerp.mobile.data.local.dao.MonthlySalesRow
import com.uzerp.mobile.data.local.dao.ProductDao
import com.uzerp.mobile.data.local.dao.PurchaseDao
import com.uzerp.mobile.data.local.dao.SalesDocDao
import com.uzerp.mobile.data.local.dao.SalesItemDao
import com.uzerp.mobile.data.local.dao.SupplierDao
import com.uzerp.mobile.data.local.dao.TopProductRow
import java.math.BigDecimal
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

data class SalesReportResult(val dateFrom: String, val dateTo: String, val count: Int, val netTotal: BigDecimal)

data class PurchasesReportResult(val dateFrom: String, val dateTo: String, val count: Int, val total: BigDecimal)

data class DashboardKpis(
    val todaySales: BigDecimal,
    val monthSales: BigDecimal,
    val cashBalance: BigDecimal,
    val bankBalance: BigDecimal,
    val lowStockCount: Int,
    val activeEmployees: Int,
)

/**
 * Hisobotlar/Analitika/Dashboard KPI agregatsiya servisi — mavjud
 * repozitoriylar/DAO ustidan faqat O'QISH, Python `reports.py`/
 * `analytics.py` hisob-kitoblarining mobil analogi.
 */
@Singleton
class ReportsRepository @Inject constructor(
    private val salesDocDao: SalesDocDao,
    private val salesItemDao: SalesItemDao,
    private val purchaseDao: PurchaseDao,
    private val productDao: ProductDao,
    private val customerDao: CustomerDao,
    private val supplierDao: SupplierDao,
    private val employeeDao: EmployeeDao,
    private val paymentRepository: PaymentRepository,
) {
    suspend fun dashboardKpis(): DashboardKpis {
        val today = DateUtils.todayStr()
        val (monthStart, monthEnd) = currentMonthBounds()
        return DashboardKpis(
            todaySales = d(salesDocDao.netSales(today, today)),
            monthSales = d(salesDocDao.netSales(monthStart, monthEnd)),
            cashBalance = paymentRepository.cashBalance(),
            bankBalance = paymentRepository.bankBalance(),
            lowStockCount = productDao.lowStockProducts().size,
            activeEmployees = employeeDao.activeCount(),
        )
    }

    suspend fun salesReport(dateFrom: String, dateTo: String): SalesReportResult =
        SalesReportResult(dateFrom, dateTo, salesDocDao.countInRange(dateFrom, dateTo), d(salesDocDao.netSales(dateFrom, dateTo)))

    suspend fun purchasesReport(dateFrom: String, dateTo: String): PurchasesReportResult =
        PurchasesReportResult(dateFrom, dateTo, purchaseDao.countInRange(dateFrom, dateTo), d(purchaseDao.totalInRange(dateFrom, dateTo)))

    suspend fun lowStock(): List<LowStockRow> = productDao.lowStockProducts()

    suspend fun topProducts(dateFrom: String, dateTo: String, limit: Int = 10): List<TopProductRow> =
        salesItemDao.topProducts(dateFrom, dateTo, limit)

    suspend fun customerDebts(): List<DebtRow> = customerDao.customerDebts()

    suspend fun supplierDebts(): List<DebtRow> = supplierDao.supplierDebts()

    /** So'nggi [months] oy uchun sof savdo dinamikasi — bo'sh oylar 0 bilan to'ldiriladi. */
    suspend fun monthlySales(months: Int = 6): List<MonthlySalesRow> {
        val from = LocalDate.now().minusMonths((months - 1).toLong()).withDayOfMonth(1).toString()
        val raw = salesDocDao.monthlySales(from)
        val map = raw.associateBy { it.ym }
        return DateUtils.lastNMonths(months).map { (y, m) ->
            val ym = "%04d-%02d".format(y, m)
            MonthlySalesRow(ym, map[ym]?.total ?: BigDecimal.ZERO)
        }
    }

    private fun currentMonthBounds(): Pair<String, String> {
        val now = LocalDate.now()
        return DateUtils.monthBounds(now.year, now.monthValue)
    }
}
