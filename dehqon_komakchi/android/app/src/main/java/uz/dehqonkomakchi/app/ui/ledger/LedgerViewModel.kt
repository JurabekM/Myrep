package uz.dehqonkomakchi.app.ui.ledger

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import uz.dehqonkomakchi.app.data.db.entity.ExpenseEntity
import uz.dehqonkomakchi.app.data.db.entity.HarvestEntity
import uz.dehqonkomakchi.app.data.db.entity.SaleEntity
import uz.dehqonkomakchi.app.data.repo.LedgerRepository
import uz.dehqonkomakchi.app.data.repo.LedgerSummary
import java.time.LocalDate
import javax.inject.Inject

@HiltViewModel
class LedgerViewModel @Inject constructor(
    private val repository: LedgerRepository,
) : ViewModel() {

    val expenses: StateFlow<List<ExpenseEntity>> =
        repository.observeExpenses().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val harvests: StateFlow<List<HarvestEntity>> =
        repository.observeHarvests().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val sales: StateFlow<List<SaleEntity>> =
        repository.observeSales().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val summary: StateFlow<LedgerSummary> =
        repository.observeSummary().stateIn(
            viewModelScope,
            SharingStarted.WhileSubscribed(5000),
            LedgerSummary(0.0, 0.0, 0.0),
        )

    fun addExpense(category: String, amount: Double, note: String, dateEpochDay: Long = LocalDate.now().toEpochDay()) {
        viewModelScope.launch { repository.addExpense(category, amount, note, dateEpochDay) }
    }

    fun addHarvest(quantity: Double, unit: String, dateEpochDay: Long = LocalDate.now().toEpochDay()) {
        viewModelScope.launch { repository.addHarvest(quantity, unit, dateEpochDay) }
    }

    fun addSale(product: String, quantity: Double, price: Double, buyerType: String, dateEpochDay: Long = LocalDate.now().toEpochDay()) {
        viewModelScope.launch { repository.addSale(product, quantity, price, buyerType, dateEpochDay) }
    }

    fun deleteExpense(entity: ExpenseEntity) = viewModelScope.launch { repository.deleteExpense(entity) }
    fun deleteHarvest(entity: HarvestEntity) = viewModelScope.launch { repository.deleteHarvest(entity) }
    fun deleteSale(entity: SaleEntity) = viewModelScope.launch { repository.deleteSale(entity) }

    suspend fun exportCsv(): String = repository.buildCsvExport()
}
