package com.uzerp.mobile.ui.reports

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.FileExport
import com.uzerp.mobile.data.local.dao.DebtRow
import com.uzerp.mobile.data.local.dao.LowStockRow
import com.uzerp.mobile.data.local.dao.TopProductRow
import com.uzerp.mobile.data.repository.PurchasesReportResult
import com.uzerp.mobile.data.repository.ReportsRepository
import com.uzerp.mobile.data.repository.SalesReportResult
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import java.time.LocalDate
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ReportsUiState(
    val dateFrom: String = DateUtils.monthBounds(LocalDate.now().year, LocalDate.now().monthValue).first,
    val dateTo: String = DateUtils.monthBounds(LocalDate.now().year, LocalDate.now().monthValue).second,
    val sales: SalesReportResult? = null,
    val purchases: PurchasesReportResult? = null,
    val lowStock: List<LowStockRow> = emptyList(),
    val topProducts: List<TopProductRow> = emptyList(),
    val customerDebts: List<DebtRow> = emptyList(),
    val supplierDebts: List<DebtRow> = emptyList(),
    val isLoading: Boolean = true,
    val error: String? = null,
    val message: String? = null,
)

@HiltViewModel
class ReportsViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val reportsRepository: ReportsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ReportsUiState())
    val state: StateFlow<ReportsUiState> = _state.asStateFlow()

    fun setDateFrom(value: String) {
        _state.value = _state.value.copy(dateFrom = value)
    }

    fun setDateTo(value: String) {
        _state.value = _state.value.copy(dateTo = value)
    }

    fun reload() {
        viewModelScope.launch {
            val s = _state.value
            _state.value = s.copy(isLoading = true, error = null)
            try {
                _state.value = _state.value.copy(
                    sales = reportsRepository.salesReport(s.dateFrom, s.dateTo),
                    purchases = reportsRepository.purchasesReport(s.dateFrom, s.dateTo),
                    lowStock = reportsRepository.lowStock(),
                    topProducts = reportsRepository.topProducts(s.dateFrom, s.dateTo),
                    customerDebts = reportsRepository.customerDebts(),
                    supplierDebts = reportsRepository.supplierDebts(),
                    isLoading = false,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun exportSales() {
        val s = _state.value.sales ?: return
        val csv = FileExport.toCsv(
            listOf("Davr boshi", "Davr oxiri", "Hujjatlar soni", "Sof summa"),
            listOf(listOf(s.dateFrom, s.dateTo, s.count.toString(), s.netTotal.toPlainString())),
        )
        export("savdo_hisobot_${s.dateFrom}_${s.dateTo}.csv", csv)
    }

    fun exportPurchases() {
        val s = _state.value.purchases ?: return
        val csv = FileExport.toCsv(
            listOf("Davr boshi", "Davr oxiri", "Hujjatlar soni", "Jami summa"),
            listOf(listOf(s.dateFrom, s.dateTo, s.count.toString(), s.total.toPlainString())),
        )
        export("xaridlar_hisobot_${s.dateFrom}_${s.dateTo}.csv", csv)
    }

    fun exportLowStock() {
        val items = _state.value.lowStock
        val csv = FileExport.toCsv(
            listOf("Mahsulot", "SKU", "Birlik", "Joriy qoldiq", "Min. zaxira"),
            items.map { listOf(it.name, it.sku ?: "", it.unit, it.currentStock.toPlainString(), it.minStock.toPlainString()) },
        )
        export("kam_qolgan_mahsulotlar.csv", csv)
    }

    fun exportTopProducts() {
        val s = _state.value
        val items = s.topProducts
        val csv = FileExport.toCsv(
            listOf("Mahsulot", "Birlik", "Sotilgan miqdor", "Daromad"),
            items.map { listOf(it.productName, it.unit, it.totalQty.toPlainString(), it.totalRevenue.toPlainString()) },
        )
        export("top_mahsulotlar_${s.dateFrom}_${s.dateTo}.csv", csv)
    }

    fun exportCustomerDebts() {
        val items = _state.value.customerDebts
        val csv = FileExport.toCsv(
            listOf("Mijoz", "Qarz summasi"),
            items.map { listOf(it.partnerName, it.debt.toPlainString()) },
        )
        export("mijozlar_qarzi.csv", csv)
    }

    fun exportSupplierDebts() {
        val items = _state.value.supplierDebts
        val csv = FileExport.toCsv(
            listOf("Ta'minotchi", "Qarz summasi"),
            items.map { listOf(it.partnerName, it.debt.toPlainString()) },
        )
        export("taminotchilar_qarzi.csv", csv)
    }

    private fun export(fileName: String, csv: String) {
        viewModelScope.launch {
            val uri = FileExport.exportText(context, fileName, "text/csv", csv)
            _state.value = _state.value.copy(
                message = if (uri != null) "Eksport qilindi: Yuklab olinganlar/UzERP/$fileName" else "Eksport qilib bo'lmadi.",
            )
        }
    }
}
