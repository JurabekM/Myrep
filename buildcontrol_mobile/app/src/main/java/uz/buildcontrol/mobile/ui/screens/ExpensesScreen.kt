package uz.buildcontrol.mobile.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.launch
import uz.buildcontrol.mobile.BuildControlApp
import uz.buildcontrol.mobile.core.Fmt
import uz.buildcontrol.mobile.core.I18n
import uz.buildcontrol.mobile.core.tr
import uz.buildcontrol.mobile.data.db.ExpenseRow
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.ExpenseCategory
import uz.buildcontrol.mobile.domain.ExpenseStatus
import uz.buildcontrol.mobile.domain.PaymentMethod
import uz.buildcontrol.mobile.domain.Perm
import uz.buildcontrol.mobile.ui.SyncAction
import uz.buildcontrol.mobile.ui.components.Badge
import uz.buildcontrol.mobile.ui.components.BcCard
import uz.buildcontrol.mobile.ui.components.ConfirmDialog
import uz.buildcontrol.mobile.ui.components.EmptyState
import uz.buildcontrol.mobile.ui.components.Field
import uz.buildcontrol.mobile.ui.components.FormSheet
import uz.buildcontrol.mobile.ui.components.GhostButton
import uz.buildcontrol.mobile.ui.components.KeyValue
import uz.buildcontrol.mobile.ui.components.Picker
import uz.buildcontrol.mobile.ui.components.PrimaryButton
import uz.buildcontrol.mobile.ui.theme.BcColors

fun expenseKind(status: String): String = when (status) {
    ExpenseStatus.PAID -> "success"
    ExpenseStatus.APPROVED -> "info"
    ExpenseStatus.PENDING -> "warning"
    else -> "danger"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ExpensesScreen(user: CurrentUser, projectId: Long?, embedded: Boolean = false) {
    val container = BuildControlApp.container
    var statusFilter by remember { mutableStateOf("") }
    var adding by remember { mutableStateOf(false) }
    var approving by remember { mutableStateOf<ExpenseRow?>(null) }
    var overBudget by remember { mutableStateOf(false) }

    val expenses by container.expenses.observeExpenses(projectId, statusFilter)
        .collectAsStateWithLifecycle(initialValue = emptyList())

    val body: @Composable (Modifier) -> Unit = { modifier ->
        Column(modifier.fillMaxSize().padding(horizontal = 14.dp)) {
            Spacer(Modifier.height(8.dp))
            Picker(
                tr("status"),
                listOf("" to tr("all")) + ExpenseStatus.all.map { it to I18n.enum("xstatus", it) },
                statusFilter,
                { statusFilter = it },
            )
            Spacer(Modifier.height(4.dp))
            Text(
                "${tr("total")}: ${Fmt.money(expenses.sumOf { it.amount })}",
                style = MaterialTheme.typography.labelMedium,
                color = BcColors.TextMuted,
            )
            Spacer(Modifier.height(8.dp))
            if (expenses.isEmpty()) EmptyState()
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(expenses, key = { it.id }) { expense ->
                    ExpenseCard(expense, user) { approving = expense }
                }
                item { Spacer(Modifier.height(90.dp)) }
            }
        }
    }

    val fab: @Composable () -> Unit = {
        if (user.can(Perm.EXPENSE_EDIT)) {
            FloatingActionButton(
                onClick = { adding = true },
                containerColor = BcColors.Accent,
            ) { Icon(Icons.Default.Add, contentDescription = tr("new_expense")) }
        }
    }

    if (embedded) {
        Scaffold(containerColor = BcColors.Background, floatingActionButton = fab) { padding ->
            body(Modifier.padding(padding))
        }
    } else {
        Scaffold(
            containerColor = BcColors.Background,
            topBar = {
                TopAppBar(
                    title = { Text(tr("expenses")) },
                    actions = { SyncAction() },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = BcColors.BackgroundAlt,
                        titleContentColor = BcColors.Text,
                    ),
                )
            },
            floatingActionButton = fab,
        ) { padding -> body(Modifier.padding(padding)) }
    }

    if (adding) {
        ExpenseSheet(user, projectId) { adding = false }
    }

    val pending = approving
    if (pending != null) {
        LaunchedEffect(pending.id) {
            overBudget = pending.projectId?.let {
                container.expenses.wouldExceedBudget(it, pending.amount)
            } ?: false
        }
        val scope = rememberCoroutineScope()
        ConfirmDialog(
            title = tr("approve"),
            text = if (overBudget) {
                "${tr("budget_exceed_warning")}\n\n${Fmt.money(pending.amount)}"
            } else {
                Fmt.money(pending.amount)
            },
            onConfirm = {
                scope.launch {
                    runCatching {
                        container.expenses.setStatus(user, pending, ExpenseStatus.APPROVED)
                    }
                    approving = null
                }
            },
            onDismiss = { approving = null },
        )
    }
}

@Composable
private fun ExpenseCard(expense: ExpenseRow, user: CurrentUser, onApprove: () -> Unit) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    var paid by remember(expense.id) { mutableStateOf(0.0) }
    LaunchedEffect(expense.id, expense.status) { paid = container.expenses.paid(expense.id) }

    BcCard {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    Fmt.money(expense.amount),
                    style = MaterialTheme.typography.titleMedium,
                    color = BcColors.Text,
                )
                Text(
                    "${I18n.enum("xcat", expense.category)} · ${Fmt.date(expense.payDate)}",
                    style = MaterialTheme.typography.labelSmall,
                    color = BcColors.TextFaint,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Badge(I18n.enum("xstatus", expense.status), expenseKind(expense.status))
        }
        if (!expense.note.isNullOrBlank()) {
            Spacer(Modifier.height(4.dp))
            Text(
                expense.note,
                style = MaterialTheme.typography.bodySmall,
                color = BcColors.TextMuted,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        if (paid > 0) {
            KeyValue(tr("paid_amount"), Fmt.money(paid), BcColors.Success)
        }
        if (expense.status == ExpenseStatus.PENDING && user.can(Perm.EXPENSE_APPROVE)) {
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                PrimaryButton(tr("approve"), onClick = onApprove, modifier = Modifier.weight(1f))
                GhostButton(
                    tr("reject"),
                    onClick = {
                        scope.launch {
                            runCatching {
                                container.expenses.setStatus(user, expense, ExpenseStatus.REJECTED)
                            }
                        }
                    },
                    modifier = Modifier.weight(1f),
                )
            }
        }
        if (expense.status == ExpenseStatus.APPROVED && user.can(Perm.EXPENSE_APPROVE)) {
            Spacer(Modifier.height(8.dp))
            PrimaryButton(
                tr("mark_paid"),
                onClick = {
                    scope.launch {
                        runCatching {
                            container.expenses.addPayment(
                                user, expense, expense.amount - paid, expense.method
                            )
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun ExpenseSheet(user: CurrentUser, projectId: Long?, onDone: () -> Unit) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    var amount by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("material") }
    var method by remember { mutableStateOf("transfer") }
    var note by remember { mutableStateOf("") }
    var invoice by remember { mutableStateOf("") }
    var chosenProject by remember { mutableStateOf(projectId) }
    var counterpartyId by remember { mutableStateOf<Long?>(null) }
    var itemId by remember { mutableStateOf<Long?>(null) }
    var projects by remember { mutableStateOf(listOf<Pair<Long?, String>>()) }
    var counterparties by remember { mutableStateOf(listOf<Pair<Long?, String>>()) }
    var items by remember { mutableStateOf(listOf<Pair<Long?, String>>()) }
    var error by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        projects = listOf<Pair<Long?, String>>(null to "—") +
            container.projects.projects().map { it.id as Long? to it.name }
        counterparties = listOf<Pair<Long?, String>>(null to "—") +
            container.counterparties.all().map { it.id as Long? to it.name }
    }
    LaunchedEffect(chosenProject) {
        items = listOf<Pair<Long?, String>>(null to "—") +
            (chosenProject?.let { pid ->
                container.estimates.items(pid).map { it.id as Long? to it.name }
            } ?: emptyList())
    }

    FormSheet(
        title = tr("new_expense"),
        onDismiss = onDone,
        error = error,
        onSave = {
            val project = chosenProject
            if (project == null || amount.isBlank()) {
                error = tr("required_field")
                return@FormSheet
            }
            scope.launch {
                try {
                    container.expenses.save(
                        user,
                        ExpenseRow(
                            projectId = project,
                            category = category,
                            amount = Fmt.parseNumber(amount),
                            payDate = Fmt.today(),
                            method = method,
                            invoiceNo = invoice.trim(),
                            note = note.trim(),
                            counterpartyId = counterpartyId,
                            estimateItemId = itemId,
                        ),
                    )
                    onDone()
                } catch (exc: Exception) {
                    error = exc.message ?: "error"
                }
            }
        },
    ) {
        if (projectId == null) {
            Picker(tr("project"), projects, chosenProject, { chosenProject = it })
        }
        Field(tr("amount"), amount, { amount = it }, numeric = true, required = true)
        Picker(
            tr("category"),
            ExpenseCategory.all.map { it to I18n.enum("xcat", it) },
            category,
            { category = it },
        )
        Picker(tr("counterparty"), counterparties, counterpartyId, { counterpartyId = it })
        Picker(tr("estimate_item"), items, itemId, { itemId = it })
        Picker(
            tr("method"),
            PaymentMethod.all.map { it to I18n.enum("method", it) },
            method,
            { method = it },
        )
        Field(tr("invoice_no"), invoice, { invoice = it })
        Field(tr("note"), note, { note = it }, singleLine = false)
    }
}
