package com.uzerp.mobile.ui.accounting

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.uzerp.mobile.core.money
import com.uzerp.mobile.ui.common.EmptyState
import com.uzerp.mobile.ui.common.ErrorBanner
import com.uzerp.mobile.ui.common.ListRowCard
import com.uzerp.mobile.ui.common.LoadingState
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.theme.UzGreen
import com.uzerp.mobile.ui.theme.UzMuted
import com.uzerp.mobile.ui.theme.UzRed

private val TABS = listOf("Hisoblar", "Jurnal", "Balans", "Foyda-zarar", "QQS")

@Composable
fun AccountingScreen(onBack: () -> Unit, viewModel: AccountingViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var tab by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) { viewModel.reload() }

    ScreenScaffold(title = "Buxgalteriya", onBack = onBack) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            TabRow(selectedTabIndex = tab, containerColor = MaterialTheme.colorScheme.surface) {
                TABS.forEachIndexed { index, label ->
                    Tab(selected = tab == index, onClick = { tab = index }, text = { Text(label) })
                }
            }
            state.error?.let { ErrorBanner(it) }
            if (state.isLoading) {
                LoadingState()
            } else {
                when (tab) {
                    0 -> AccountsTab(state)
                    1 -> JournalTab(state)
                    2 -> BalanceSheetTab(state)
                    3 -> ProfitLossTab(state)
                    else -> VatTab(state)
                }
            }
        }
    }
}

@Composable
private fun AccountsTab(state: AccountingUiState) {
    if (state.accounts.isEmpty()) {
        EmptyState("Hisoblar yo'q.")
        return
    }
    LazyColumn {
        items(state.accounts, key = { it.account.id }) { row ->
            ListRowCard(
                title = "${row.account.code}  ${row.account.name}",
                subtitle = ACCOUNT_TYPE_LABELS[row.account.type] ?: row.account.type,
                trailing = money(row.balance),
            )
        }
    }
}

@Composable
private fun JournalTab(state: AccountingUiState) {
    if (state.entries.isEmpty()) {
        EmptyState("O'tkazmalar yo'q.")
        return
    }
    LazyColumn {
        items(state.entries, key = { it.id }) { entry ->
            ListRowCard(title = entry.number, subtitle = "${entry.entryDate} · ${entry.memo}", trailing = money(entry.amount ?: java.math.BigDecimal.ZERO))
        }
    }
}

@Composable
private fun BalanceSheetTab(state: AccountingUiState) {
    val bs = state.balanceSheet ?: return
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Row(modifier = Modifier.fillMaxWidth()) {
            Text(
                if (bs.balanced) "Balans TENG ✓" else "Balans BUZILGAN!",
                color = if (bs.balanced) UzGreen else UzRed,
                fontWeight = FontWeight.Bold,
            )
        }
        Text("Aktiv: ${money(bs.totalAssets)}", modifier = Modifier.padding(top = 8.dp))
        Text("Majburiyat: ${money(bs.totalLiabilities)}")
        Text("Kapital: ${money(bs.totalEquity)}")
        LazyColumn(modifier = Modifier.padding(top = 12.dp)) {
            item { SectionTitle("Aktivlar") }
            items(bs.assets) { BalanceRow(it.code, it.name, it.balance) }
            item { SectionTitle("Majburiyatlar") }
            items(bs.liabilities) { BalanceRow(it.code, it.name, it.balance) }
            item { SectionTitle("Kapital") }
            items(bs.equity) { BalanceRow(it.code, it.name, it.balance) }
        }
    }
}

@Composable
private fun ProfitLossTab(state: AccountingUiState) {
    val pl = state.profitLoss ?: return
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("Davr: ${pl.dateFrom} — ${pl.dateTo}", color = UzMuted, style = MaterialTheme.typography.bodyMedium)
        Text("Daromad: ${money(pl.totalIncome)}", modifier = Modifier.padding(top = 8.dp), color = UzGreen)
        Text("Xarajat: ${money(pl.totalExpense)}", color = UzRed)
        Text(
            "SOF FOYDA: ${money(pl.netProfit)}",
            fontWeight = FontWeight.Bold,
            color = if (pl.netProfit.signum() >= 0) UzGreen else UzRed,
        )
        LazyColumn(modifier = Modifier.padding(top = 12.dp)) {
            item { SectionTitle("Daromadlar") }
            items(pl.income) { (label, amount) -> BalanceRow(label.code, label.name, amount) }
            item { SectionTitle("Xarajatlar") }
            items(pl.expenses) { (label, amount) -> BalanceRow(label.code, label.name, amount) }
        }
    }
}

@Composable
private fun VatTab(state: AccountingUiState) {
    val vat = state.vatReport ?: return
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("Davr: ${vat.dateFrom} — ${vat.dateTo}", color = UzMuted, style = MaterialTheme.typography.bodyMedium)
        Text("Chiqim QQS (savdo): ${money(vat.outputVat)}", modifier = Modifier.padding(top = 8.dp))
        Text("Kirim QQS (xarid): ${money(vat.inputVat)}")
        Text("TO'LANADIGAN QQS: ${money(vat.payable)}", fontWeight = FontWeight.Bold, color = UzGreen)
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(text, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(vertical = 6.dp), color = MaterialTheme.colorScheme.onSurface)
}

@Composable
private fun BalanceRow(code: String, name: String, balance: java.math.BigDecimal) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Text("$code  $name", modifier = Modifier.weight(1f), color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(money(balance))
    }
}
