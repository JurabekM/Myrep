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
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
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
import uz.buildcontrol.mobile.data.db.PurchaseRequestRow
import uz.buildcontrol.mobile.data.db.SupplierQuoteRow
import uz.buildcontrol.mobile.data.repo.PurchaseRepository
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.Perm
import uz.buildcontrol.mobile.domain.PurchaseStatus
import uz.buildcontrol.mobile.domain.Units
import uz.buildcontrol.mobile.ui.components.Badge
import uz.buildcontrol.mobile.ui.components.BcCard
import uz.buildcontrol.mobile.ui.components.EmptyState
import uz.buildcontrol.mobile.ui.components.Field
import uz.buildcontrol.mobile.ui.components.FormSheet
import uz.buildcontrol.mobile.ui.components.GhostButton
import uz.buildcontrol.mobile.ui.components.KeyValue
import uz.buildcontrol.mobile.ui.components.Picker
import uz.buildcontrol.mobile.ui.components.PrimaryButton
import uz.buildcontrol.mobile.ui.components.SwitchRow
import uz.buildcontrol.mobile.ui.theme.BcColors

fun purchaseKind(status: String): String = when (status) {
    PurchaseStatus.APPROVED, PurchaseStatus.COMPLETED -> "success"
    PurchaseStatus.SUBMITTED -> "warning"
    PurchaseStatus.REJECTED -> "danger"
    PurchaseStatus.ORDERED -> "accent"
    PurchaseStatus.PARTIAL -> "info"
    else -> "neutral"
}

@Composable
fun PurchasesTab(user: CurrentUser, projectId: Long) {
    val container = BuildControlApp.container
    val requests by container.purchases.observeRequests(projectId)
        .collectAsStateWithLifecycle(initialValue = emptyList())
    var editing by remember { mutableStateOf<PurchaseRequestRow?>(null) }
    var adding by remember { mutableStateOf(false) }
    var quotesFor by remember { mutableStateOf<PurchaseRequestRow?>(null) }

    Scaffold(
        containerColor = BcColors.Background,
        floatingActionButton = {
            if (user.can(Perm.PURCHASE_EDIT)) {
                FloatingActionButton(
                    onClick = { adding = true },
                    containerColor = BcColors.Accent,
                ) { Icon(Icons.Default.Add, contentDescription = tr("new_request")) }
            }
        },
    ) { padding ->
        if (requests.isEmpty()) {
            EmptyState()
        } else {
            LazyColumn(
                Modifier.fillMaxSize().padding(padding).padding(horizontal = 14.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                item { Spacer(Modifier.height(6.dp)) }
                items(requests, key = { it.id }) { request ->
                    RequestCard(
                        request = request,
                        user = user,
                        onEdit = { editing = request },
                        onQuotes = { quotesFor = request },
                    )
                }
                item { Spacer(Modifier.height(80.dp)) }
            }
        }
    }

    if (adding || editing != null) {
        RequestSheet(
            user = user,
            projectId = projectId,
            initial = editing,
            onDismiss = { adding = false; editing = null },
            onSaved = { adding = false; editing = null },
        )
    }
    quotesFor?.let { request ->
        QuotesSheet(user, request) { quotesFor = null }
    }
}

@Composable
private fun RequestCard(
    request: PurchaseRequestRow,
    user: CurrentUser,
    onEdit: () -> Unit,
    onQuotes: () -> Unit,
) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    BcCard {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    request.title,
                    style = MaterialTheme.typography.titleSmall,
                    color = BcColors.Text,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    request.number.orEmpty(),
                    style = MaterialTheme.typography.labelSmall,
                    color = BcColors.TextFaint,
                )
            }
            Badge(I18n.enum("purchase", request.status), purchaseKind(request.status))
        }
        Spacer(Modifier.height(6.dp))
        KeyValue(
            tr("quantity"),
            "${Fmt.qty(request.quantity)} ${I18n.enum("unit", request.unit)}",
        )
        KeyValue(tr("est_price"), Fmt.money(request.estTotal))
        KeyValue(tr("needed_date"), Fmt.date(request.neededDate))
        if (request.offEstimate) {
            Text(
                tr("off_estimate"),
                color = BcColors.Warning,
                style = MaterialTheme.typography.labelSmall,
            )
        }
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            GhostButton(tr("quotes"), onClick = onQuotes, modifier = Modifier.weight(1f))
            if (user.can(Perm.PURCHASE_EDIT)) {
                GhostButton(tr("edit"), onClick = onEdit, modifier = Modifier.weight(1f))
            }
        }
        if (request.status == PurchaseStatus.DRAFT && user.can(Perm.PURCHASE_EDIT)) {
            Spacer(Modifier.height(6.dp))
            PrimaryButton(
                tr("submit"),
                onClick = {
                    scope.launch {
                        runCatching {
                            container.purchases.setStatus(user, request, PurchaseStatus.SUBMITTED)
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            )
        }
        if (request.status == PurchaseStatus.SUBMITTED && user.can(Perm.PURCHASE_APPROVE)) {
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                PrimaryButton(
                    tr("approve"),
                    onClick = {
                        scope.launch {
                            runCatching {
                                container.purchases.setStatus(user, request, PurchaseStatus.APPROVED)
                            }
                        }
                    },
                    modifier = Modifier.weight(1f),
                )
                GhostButton(
                    tr("reject"),
                    onClick = {
                        scope.launch {
                            runCatching {
                                container.purchases.setStatus(user, request, PurchaseStatus.REJECTED)
                            }
                        }
                    },
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun RequestSheet(
    user: CurrentUser,
    projectId: Long,
    initial: PurchaseRequestRow?,
    onDismiss: () -> Unit,
    onSaved: () -> Unit,
) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    var title by remember { mutableStateOf(initial?.title ?: "") }
    var qty by remember { mutableStateOf(initial?.quantity?.let { Fmt.qty(it) } ?: "") }
    var price by remember { mutableStateOf(initial?.estPrice?.let { Fmt.qty(it) } ?: "") }
    var unit by remember { mutableStateOf(initial?.unit ?: "piece") }
    var needed by remember { mutableStateOf(initial?.neededDate ?: Fmt.plusDays(Fmt.today(), 7)) }
    var offEstimate by remember { mutableStateOf(initial?.offEstimate ?: false) }
    var itemId by remember { mutableStateOf(initial?.estimateItemId) }
    var items by remember { mutableStateOf(listOf<Pair<Long?, String>>()) }
    var error by remember { mutableStateOf("") }

    LaunchedEffect(projectId) {
        items = listOf<Pair<Long?, String>>(null to "—") +
            container.estimates.items(projectId).map { it.id as Long? to "${it.code.orEmpty()} ${it.name}".trim() }
    }

    FormSheet(
        title = if (initial == null) tr("new_request") else tr("purchase_request"),
        onDismiss = onDismiss,
        error = error,
        onSave = {
            if (title.isBlank()) {
                error = tr("required_field")
                return@FormSheet
            }
            scope.launch {
                try {
                    container.purchases.saveRequest(
                        user,
                        (initial ?: PurchaseRequestRow()).copy(
                            projectId = projectId,
                            title = title.trim(),
                            unit = unit,
                            quantity = Fmt.parseNumber(qty),
                            estPrice = Fmt.parseNumber(price),
                            neededDate = needed.ifBlank { null },
                            offEstimate = offEstimate,
                            estimateItemId = if (offEstimate) null else itemId,
                        ),
                    )
                    onSaved()
                } catch (exc: uz.buildcontrol.mobile.data.repo.PurchaseRuleException) {
                    error = tr(exc.key)
                } catch (exc: Exception) {
                    error = exc.message ?: "error"
                }
            }
        },
    ) {
        Field(tr("product_service"), title, { title = it }, required = true)
        Field(tr("quantity"), qty, { qty = it }, numeric = true, required = true)
        Picker(tr("unit"), Units.all.map { it to I18n.enum("unit", it) }, unit, { unit = it })
        Field(tr("est_price"), price, { price = it }, numeric = true)
        Field(tr("needed_date"), needed, { needed = it })
        SwitchRow(tr("off_estimate"), offEstimate, onChange = { offEstimate = it })
        if (!offEstimate) {
            Picker(tr("estimate_item"), items, itemId, { itemId = it })
        }
    }
}

@Composable
private fun QuotesSheet(user: CurrentUser, request: PurchaseRequestRow, onDismiss: () -> Unit) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    var ranked by remember { mutableStateOf(listOf<PurchaseRepository.RankedQuote>()) }
    var reload by remember { mutableStateOf(0) }
    var adding by remember { mutableStateOf(false) }

    LaunchedEffect(request.id, reload) { ranked = container.purchases.quotes(request) }

    FormSheet(
        title = "${tr("quotes")} · ${request.title}",
        onDismiss = onDismiss,
        saveLabel = tr("close"),
        onSave = onDismiss,
    ) {
        if (ranked.isEmpty()) EmptyState()
        ranked.forEach { entry ->
            BcCard {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        entry.quote.supplierName.orEmpty().ifBlank { "—" },
                        style = MaterialTheme.typography.titleSmall,
                        color = BcColors.Text,
                        modifier = Modifier.weight(1f),
                    )
                    when {
                        entry.quote.isSelected -> Badge(tr("select_quote"), "success")
                        entry.isBest -> Badge(tr("best_offer"), "accent")
                        entry.isCheapest -> Badge(tr("price"), "info")
                        else -> {}
                    }
                }
                KeyValue(tr("unit_price"), Fmt.money(entry.quote.unitPrice))
                KeyValue(tr("delivery_cost"), Fmt.money(entry.quote.deliveryCost))
                KeyValue(tr("total_value"), Fmt.money(entry.totalValue))
                KeyValue(tr("delivery_days"), entry.quote.deliveryDays.toString())
                if (user.can(Perm.PURCHASE_EDIT) && !entry.quote.isSelected) {
                    Spacer(Modifier.height(6.dp))
                    GhostButton(
                        tr("select_quote"),
                        onClick = {
                            scope.launch {
                                runCatching {
                                    container.purchases.selectQuote(user, request.id, entry.quote.id)
                                }
                                reload++
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
        }
        if (user.can(Perm.PURCHASE_EDIT)) {
            GhostButton(
                tr("add_quote"),
                onClick = { adding = true },
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }

    if (adding) {
        QuoteSheet(user, request) {
            adding = false
            reload++
        }
    }
}

@Composable
private fun QuoteSheet(user: CurrentUser, request: PurchaseRequestRow, onDone: () -> Unit) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    var supplier by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var delivery by remember { mutableStateOf("") }
    var days by remember { mutableStateOf("") }
    var terms by remember { mutableStateOf("") }
    var error by remember { mutableStateOf("") }

    FormSheet(
        title = tr("add_quote"),
        onDismiss = onDone,
        error = error,
        onSave = {
            if (supplier.isBlank() || price.isBlank()) {
                error = tr("required_field")
                return@FormSheet
            }
            scope.launch {
                try {
                    container.purchases.saveQuote(
                        user,
                        SupplierQuoteRow(
                            requestId = request.id,
                            supplierName = supplier.trim(),
                            unitPrice = Fmt.parseNumber(price),
                            deliveryCost = Fmt.parseNumber(delivery),
                            deliveryDays = Fmt.parseNumber(days).toInt(),
                            paymentTerms = terms.trim(),
                        ),
                    )
                    onDone()
                } catch (exc: Exception) {
                    error = exc.message ?: "error"
                }
            }
        },
    ) {
        Field(tr("supplier"), supplier, { supplier = it }, required = true)
        Field(tr("unit_price"), price, { price = it }, numeric = true, required = true)
        Field(tr("delivery_cost"), delivery, { delivery = it }, numeric = true)
        Field(tr("delivery_days"), days, { days = it }, numeric = true)
        Field(tr("method"), terms, { terms = it })
    }
}
