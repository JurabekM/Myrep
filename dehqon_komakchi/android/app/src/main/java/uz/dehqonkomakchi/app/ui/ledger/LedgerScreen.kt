package uz.dehqonkomakchi.app.ui.ledger

import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.hilt.navigation.compose.hiltViewModel
import kotlinx.coroutines.launch
import uz.dehqonkomakchi.app.R
import java.io.File
import java.time.LocalDate

private val expenseCategories = listOf(
    "seed" to R.string.expense_category_seed,
    "fertilizer" to R.string.expense_category_fertilizer,
    "pesticide" to R.string.expense_category_pesticide,
    "water" to R.string.expense_category_water,
    "labor" to R.string.expense_category_labor,
    "transport" to R.string.expense_category_transport,
    "other" to R.string.expense_category_other,
)

private val buyerTypes = listOf(
    "wholesaler" to R.string.buyer_type_wholesaler,
    "market" to R.string.buyer_type_market,
    "neighbor" to R.string.buyer_type_neighbor,
    "processor" to R.string.buyer_type_processor,
    "other" to R.string.buyer_type_other,
)

@Composable
fun LedgerScreen(viewModel: LedgerViewModel = hiltViewModel()) {
    var tab by remember { mutableIntStateOf(0) }
    var showAddDialog by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    val expenses by viewModel.expenses.collectAsState()
    val harvests by viewModel.harvests.collectAsState()
    val sales by viewModel.sales.collectAsState()
    val summary by viewModel.summary.collectAsState()

    val tabs = listOf(
        R.string.ledger_tab_expense,
        R.string.ledger_tab_harvest,
        R.string.ledger_tab_sale,
        R.string.ledger_tab_summary,
    )

    Scaffold(
        floatingActionButton = {
            if (tab != 3) {
                FloatingActionButton(onClick = { showAddDialog = true }) {
                    Icon(Icons.Filled.Add, contentDescription = stringResource(R.string.action_add))
                }
            }
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            Text(
                stringResource(R.string.ledger_title),
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.padding(16.dp),
            )
            ScrollableTabRow(selectedTabIndex = tab) {
                tabs.forEachIndexed { index, labelRes ->
                    Tab(selected = tab == index, onClick = { tab = index }, text = { Text(stringResource(labelRes)) })
                }
            }
            when (tab) {
                0 -> ExpenseList(expenses, onDelete = viewModel::deleteExpense)
                1 -> HarvestList(harvests, onDelete = viewModel::deleteHarvest)
                2 -> SaleList(sales, onDelete = viewModel::deleteSale)
                3 -> SummaryTab(
                    summary = summary,
                    onExport = {
                        scope.launch {
                            val csv = viewModel.exportCsv()
                            val file = File(context.cacheDir, "daftar_export.csv").apply { writeText(csv) }
                            val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
                            val intent = Intent(Intent.ACTION_SEND).apply {
                                type = "text/csv"
                                putExtra(Intent.EXTRA_STREAM, uri)
                                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                            }
                            context.startActivity(Intent.createChooser(intent, context.getString(R.string.ledger_export_csv)))
                        }
                    },
                )
            }
        }
    }

    if (showAddDialog) {
        when (tab) {
            0 -> AddExpenseDialog(onDismiss = { showAddDialog = false }) { category, amount, note ->
                viewModel.addExpense(category, amount, note)
                showAddDialog = false
            }
            1 -> AddHarvestDialog(onDismiss = { showAddDialog = false }) { qty, unit ->
                viewModel.addHarvest(qty, unit)
                showAddDialog = false
            }
            2 -> AddSaleDialog(onDismiss = { showAddDialog = false }) { product, qty, price, buyer ->
                viewModel.addSale(product, qty, price, buyer)
                showAddDialog = false
            }
        }
    }
}

@Composable
private fun ExpenseList(items: List<uz.dehqonkomakchi.app.data.db.entity.ExpenseEntity>, onDelete: (uz.dehqonkomakchi.app.data.db.entity.ExpenseEntity) -> Unit) {
    if (items.isEmpty()) {
        Text(stringResource(R.string.ledger_empty), modifier = Modifier.padding(16.dp))
        return
    }
    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
        items(items, key = { it.id }) { item ->
            Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("${item.category} — ${item.amount} ${stringResource(R.string.unit_som)}", style = MaterialTheme.typography.titleMedium)
                    Text(LocalDate.ofEpochDay(item.dateEpochDay).toString(), style = MaterialTheme.typography.bodyMedium)
                    if (item.note.isNotBlank()) Text(item.note, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
    }
}

@Composable
private fun HarvestList(items: List<uz.dehqonkomakchi.app.data.db.entity.HarvestEntity>, onDelete: (uz.dehqonkomakchi.app.data.db.entity.HarvestEntity) -> Unit) {
    if (items.isEmpty()) {
        Text(stringResource(R.string.ledger_empty), modifier = Modifier.padding(16.dp))
        return
    }
    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
        items(items, key = { it.id }) { item ->
            Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("${item.quantity} ${item.unit}", style = MaterialTheme.typography.titleMedium)
                    Text(LocalDate.ofEpochDay(item.dateEpochDay).toString(), style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
    }
}

@Composable
private fun SaleList(items: List<uz.dehqonkomakchi.app.data.db.entity.SaleEntity>, onDelete: (uz.dehqonkomakchi.app.data.db.entity.SaleEntity) -> Unit) {
    if (items.isEmpty()) {
        Text(stringResource(R.string.ledger_empty), modifier = Modifier.padding(16.dp))
        return
    }
    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
        items(items, key = { it.id }) { item ->
            Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("${item.product}: ${item.quantity}kg × ${item.price}", style = MaterialTheme.typography.titleMedium)
                    Text(LocalDate.ofEpochDay(item.dateEpochDay).toString(), style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
    }
}

@Composable
private fun SummaryTab(summary: uz.dehqonkomakchi.app.data.repo.LedgerSummary, onExport: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SummaryRow(stringResource(R.string.ledger_summary_total_expense), "${summary.totalExpense} ${stringResource(R.string.unit_som)}")
        SummaryRow(stringResource(R.string.ledger_summary_total_revenue), "${summary.totalRevenue} ${stringResource(R.string.unit_som)}")
        SummaryRow(stringResource(R.string.ledger_summary_profit), "${summary.profit} ${stringResource(R.string.unit_som)}")
        SummaryRow(
            stringResource(R.string.ledger_summary_cost_per_kg),
            summary.costPerKg?.let { "%.0f %s".format(it, stringResource(R.string.unit_som)) } ?: "—",
        )
        Button(onClick = onExport, modifier = Modifier.fillMaxWidth()) {
            Text(stringResource(R.string.ledger_export_csv))
        }
    }
}

@Composable
private fun SummaryRow(label: String, value: String) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(label, style = MaterialTheme.typography.bodyMedium)
            Text(value, style = MaterialTheme.typography.headlineMedium)
        }
    }
}

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
private fun AddExpenseDialog(onDismiss: () -> Unit, onConfirm: (String, Double, String) -> Unit) {
    var category by remember { mutableStateOf(expenseCategories.first().first) }
    var amount by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    var expanded by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.ledger_add_expense)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
                    OutlinedTextField(
                        value = stringResource(expenseCategories.first { it.first == category }.second),
                        onValueChange = {},
                        readOnly = true,
                        label = { Text(stringResource(R.string.ledger_expense_category)) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    SimpleDropdown(expanded = expanded, onDismissRequest = { expanded = false }) {
                        expenseCategories.forEach { (key, labelRes) ->
                            DropdownMenuItem(text = { Text(stringResource(labelRes)) }, onClick = { category = key; expanded = false })
                        }
                    }
                }
                OutlinedTextField(value = amount, onValueChange = { amount = it }, label = { Text(stringResource(R.string.ledger_expense_amount)) }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = note, onValueChange = { note = it }, label = { Text(stringResource(R.string.ledger_expense_note)) }, modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = {
            Button(onClick = { onConfirm(category, amount.toDoubleOrNull() ?: 0.0, note) }) { Text(stringResource(R.string.action_save)) }
        },
        dismissButton = { Button(onClick = onDismiss) { Text(stringResource(R.string.action_cancel)) } },
    )
}

@Composable
private fun SimpleDropdown(
    expanded: Boolean,
    onDismissRequest: () -> Unit,
    content: @Composable androidx.compose.foundation.layout.ColumnScope.() -> Unit,
) {
    DropdownMenu(expanded = expanded, onDismissRequest = onDismissRequest, content = content)
}

@Composable
private fun AddHarvestDialog(onDismiss: () -> Unit, onConfirm: (Double, String) -> Unit) {
    var quantity by remember { mutableStateOf("") }
    var unit by remember { mutableStateOf("kg") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.ledger_add_harvest)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(value = quantity, onValueChange = { quantity = it }, label = { Text(stringResource(R.string.ledger_harvest_quantity)) }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = unit, onValueChange = { unit = it }, label = { Text(stringResource(R.string.ledger_harvest_unit)) }, modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = { Button(onClick = { onConfirm(quantity.toDoubleOrNull() ?: 0.0, unit) }) { Text(stringResource(R.string.action_save)) } },
        dismissButton = { Button(onClick = onDismiss) { Text(stringResource(R.string.action_cancel)) } },
    )
}

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
private fun AddSaleDialog(onDismiss: () -> Unit, onConfirm: (String, Double, Double, String) -> Unit) {
    var product by remember { mutableStateOf("Pomidor") }
    var quantity by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var buyer by remember { mutableStateOf(buyerTypes.first().first) }
    var expanded by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.ledger_add_sale)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(value = product, onValueChange = { product = it }, label = { Text(stringResource(R.string.ledger_sale_product)) }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = quantity, onValueChange = { quantity = it }, label = { Text(stringResource(R.string.ledger_sale_quantity)) }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = price, onValueChange = { price = it }, label = { Text(stringResource(R.string.ledger_sale_price)) }, modifier = Modifier.fillMaxWidth())
                ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
                    OutlinedTextField(
                        value = stringResource(buyerTypes.first { it.first == buyer }.second),
                        onValueChange = {},
                        readOnly = true,
                        label = { Text(stringResource(R.string.ledger_sale_buyer_type)) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    SimpleDropdown(expanded = expanded, onDismissRequest = { expanded = false }) {
                        buyerTypes.forEach { (key, labelRes) ->
                            DropdownMenuItem(text = { Text(stringResource(labelRes)) }, onClick = { buyer = key; expanded = false })
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(onClick = { onConfirm(product, quantity.toDoubleOrNull() ?: 0.0, price.toDoubleOrNull() ?: 0.0, buyer) }) {
                Text(stringResource(R.string.action_save))
            }
        },
        dismissButton = { Button(onClick = onDismiss) { Text(stringResource(R.string.action_cancel)) } },
    )
}
