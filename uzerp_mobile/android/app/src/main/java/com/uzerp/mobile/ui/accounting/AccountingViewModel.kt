package com.uzerp.mobile.ui.accounting

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.data.local.dao.JournalEntryWithAmount
import com.uzerp.mobile.data.local.entity.AccountEntity
import com.uzerp.mobile.data.repository.AccountingRepository
import com.uzerp.mobile.data.repository.AuthRepository
import com.uzerp.mobile.data.repository.BalanceSheetResult
import com.uzerp.mobile.data.repository.JournalLineInput
import com.uzerp.mobile.data.repository.ProfitLossResult
import com.uzerp.mobile.data.repository.TrialBalanceEntry
import com.uzerp.mobile.data.repository.VatReportResult
import dagger.hilt.android.lifecycle.HiltViewModel
import java.math.BigDecimal
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

val ACCOUNT_TYPE_LABELS = mapOf(
    "asset" to "Aktiv", "contra_asset" to "Kontr-aktiv", "liability" to "Majburiyat",
    "equity" to "Kapital", "income" to "Daromad", "expense" to "Xarajat",
)

data class AccountBalanceRow(val account: AccountEntity, val balance: BigDecimal)

data class AccountingUiState(
    val accounts: List<AccountBalanceRow> = emptyList(),
    val entries: List<JournalEntryWithAmount> = emptyList(),
    val trialBalance: List<TrialBalanceEntry> = emptyList(),
    val profitLoss: ProfitLossResult? = null,
    val balanceSheet: BalanceSheetResult? = null,
    val vatReport: VatReportResult? = null,
    val isLoading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class AccountingViewModel @Inject constructor(
    private val repository: AccountingRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AccountingUiState())
    val state: StateFlow<AccountingUiState> = _state.asStateFlow()

    fun reload() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                val monthStart = DateUtils.todayStr().substring(0, 7) + "-01"
                val today = DateUtils.todayStr()
                // observeAll Flow'dan birinchi qiymatni olamiz (bir martalik yuklash —
                // .collect{} ISHLATILMAYDI, chunki Room Flow tugamaydi va collect
                // abadiy kutib qolar edi; .first() bitta qiymat olib to'xtaydi).
                val accountList = repository.accounts().first()
                val accounts = accountList.map { a -> AccountBalanceRow(a, repository.accountBalance(a.code)) }
                _state.value = _state.value.copy(
                    accounts = accounts,
                    entries = repository.listEntries().items,
                    trialBalance = repository.trialBalance(today),
                    profitLoss = repository.profitLoss(monthStart, today),
                    balanceSheet = repository.balanceSheet(today),
                    vatReport = repository.vatReport(monthStart, today),
                    isLoading = false, error = null,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun createManualEntry(memo: String, lines: List<JournalLineInput>) {
        viewModelScope.launch {
            try {
                repository.createEntry(memo, lines, userId = authRepository.currentUser.value?.id)
                reload()
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }
}
