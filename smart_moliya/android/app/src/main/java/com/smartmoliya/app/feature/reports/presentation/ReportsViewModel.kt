package com.smartmoliya.app.feature.reports.presentation

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smartmoliya.app.BuildConfig
import com.smartmoliya.app.core.network.ApiService
import com.smartmoliya.app.core.network.dto.CategoryBreakdownItemDto
import com.smartmoliya.app.core.network.dto.DailyCashFlowItemDto
import com.smartmoliya.app.feature.expense.domain.CategoryRepository
import com.smartmoliya.app.feature.expense.domain.TransactionRepository
import com.smartmoliya.app.feature.expense.domain.TransactionType
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.launch
import java.io.File
import java.util.Calendar
import javax.inject.Inject

data class ReportsUiState(
    val isLoading: Boolean = false,
    val totalIncome: Double = 0.0,
    val totalExpense: Double = 0.0,
    val byCategory: List<CategoryBreakdownItemDto> = emptyList(),
    val dailyCashFlow: List<DailyCashFlowItemDto> = emptyList(),
    /** PDF/Excel eksport server tomonida tayyorlanadi - offline flavor'da mavjud emas. */
    val exportsAvailable: Boolean = !BuildConfig.OFFLINE_MODE,
    val exportedFilePath: String? = null,
    val errorMessage: String? = null
)

@HiltViewModel
class ReportsViewModel @Inject constructor(
    private val api: ApiService,
    private val transactionRepository: TransactionRepository,
    private val categoryRepository: CategoryRepository,
    @ApplicationContext private val context: Context
) : ViewModel() {

    private val _uiState = MutableStateFlow(ReportsUiState())
    val uiState: StateFlow<ReportsUiState> = _uiState.asStateFlow()

    init {
        if (BuildConfig.OFFLINE_MODE) {
            // Offline: hisobot Room'dagi ma'lumotlardan real vaqtda hisoblanadi
            viewModelScope.launch { categoryRepository.ensureSeedData() }
            combine(
                transactionRepository.observeTransactions(),
                categoryRepository.observeCategories()
            ) { transactions, categories ->
                val monthStart = currentMonthStartMillis()
                val monthly = transactions.filter { it.occurredAt >= monthStart }
                val income = monthly.filter { it.type == TransactionType.INCOME }.sumOf { it.amount }
                val expenses = monthly.filter { it.type == TransactionType.EXPENSE }
                val totalExpense = expenses.sumOf { it.amount }
                val names = categories.associate { it.id to it.name }

                val byCategory = expenses.groupBy { it.categoryId ?: "other" }
                    .map { (categoryId, items) ->
                        val amount = items.sumOf { it.amount }
                        CategoryBreakdownItemDto(
                            category_id = categoryId,
                            category_name = names[categoryId] ?: "Boshqa",
                            amount = amount,
                            percent = if (totalExpense > 0) {
                                Math.round(amount / totalExpense * 1000.0) / 10.0
                            } else 0.0
                        )
                    }
                    .sortedByDescending { it.amount }

                ReportsUiState(
                    totalIncome = income,
                    totalExpense = totalExpense,
                    byCategory = byCategory,
                    exportsAvailable = false
                )
            }
                .onEach { _uiState.value = it }
                .launchIn(viewModelScope)
        } else {
            refresh()
        }
    }

    fun refresh() {
        if (BuildConfig.OFFLINE_MODE) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            runCatching { api.getReportSummary() }
                .onSuccess { summary ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        totalIncome = summary.total_income,
                        totalExpense = summary.total_expense,
                        byCategory = summary.by_category,
                        dailyCashFlow = summary.daily_cash_flow
                    )
                }
                .onFailure {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = "Hisobotni yuklab bo'lmadi (offline yoki server xatosi)"
                    )
                }
        }
    }

    fun exportPdf() = export(fileName = "smart_moliya_hisobot.pdf") { api.exportReportPdf() }

    fun exportExcel() = export(fileName = "smart_moliya_hisobot.xlsx") { api.exportReportExcel() }

    /** Offline: barcha tranzaksiyalarni CSV faylga yozadi (Excel'da ochiladi). */
    fun exportCsv() {
        viewModelScope.launch {
            runCatching {
                val transactions = transactionRepository.observeTransactions().first()
                val categories = categoryRepository.observeCategories().first()
                val names = categories.associate { it.id to it.name }
                val dateFormat = java.text.SimpleDateFormat("yyyy-MM-dd HH:mm", java.util.Locale.US)

                val file = File(context.getExternalFilesDir(null), "smart_moliya_tranzaksiyalar.csv")
                file.bufferedWriter().use { writer ->
                    writer.appendLine("Sana,Turi,Kategoriya,Summa,Valyuta,Izoh")
                    transactions.forEach { txn ->
                        val category = names[txn.categoryId] ?: ""
                        val note = (txn.note ?: "").replace(",", ";").replace("\n", " ")
                        writer.appendLine(
                            "${dateFormat.format(java.util.Date(txn.occurredAt))},${txn.type}," +
                                "$category,${txn.amount},${txn.currency},$note"
                        )
                    }
                }
                file.absolutePath
            }.onSuccess { path ->
                _uiState.value = _uiState.value.copy(exportedFilePath = path)
            }.onFailure {
                _uiState.value = _uiState.value.copy(errorMessage = "CSV eksport qilib bo'lmadi")
            }
        }
    }

    private fun export(fileName: String, request: suspend () -> okhttp3.ResponseBody) {
        if (BuildConfig.OFFLINE_MODE) return
        viewModelScope.launch {
            runCatching {
                val body = request()
                val file = File(context.getExternalFilesDir(null), fileName)
                body.byteStream().use { input ->
                    file.outputStream().use { output -> input.copyTo(output) }
                }
                file.absolutePath
            }.onSuccess { path ->
                _uiState.value = _uiState.value.copy(exportedFilePath = path)
            }.onFailure {
                _uiState.value = _uiState.value.copy(errorMessage = "Eksport qilib bo'lmadi")
            }
        }
    }
}

private fun currentMonthStartMillis(): Long {
    val calendar = Calendar.getInstance()
    calendar.set(Calendar.DAY_OF_MONTH, 1)
    calendar.set(Calendar.HOUR_OF_DAY, 0)
    calendar.set(Calendar.MINUTE, 0)
    calendar.set(Calendar.SECOND, 0)
    calendar.set(Calendar.MILLISECOND, 0)
    return calendar.timeInMillis
}
