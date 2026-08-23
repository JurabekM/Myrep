package uz.distribos.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Inventory
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import uz.distribos.core.Formatting

/**
 * Ekranlar — har biri ANIQ bir vazifa uchun.
 *
 * Bu dashboard EMAS: agent «bugungi mijozlar» ni ochadi va buyurtma
 * yozadi; omborchi «qabul qilish» ni ochadi va skanerlaydi. Har ekran
 * bitta ish oqimiga xizmat qiladi.
 *
 * Ekranlar to'plami ROLGA qarab o'zgaradi (`RoleTabs`).
 */

data class TabItem(val key: String, val title: String, val icon: ImageVector)

/** Rolga mos ekranlar. Kassirga ombor kerak emas, omborchiga to'lov. */
object RoleTabs {
    private val ORDERS = TabItem("orders", "Buyurtmalar", Icons.Filled.Receipt)
    private val CUSTOMERS = TabItem("customers", "Mijozlar", Icons.Filled.People)
    private val INVENTORY = TabItem("inventory", "Ombor", Icons.Filled.Inventory)
    private val PAYMENTS = TabItem("payments", "To'lovlar", Icons.Filled.Payments)
    private val SYNC = TabItem("sync", "Holat", Icons.Filled.Sync)
    private val JOIN = TabItem("join", "Ulash", Icons.Filled.QrCodeScanner)

    /**
     * @param provisioned qurilma kompyuterga ulanganmi.
     *
     * Ulanmagan telefonda FAQAT «Ulash» ekrani ko'rsatiladi: bo'sh
     * ro'yxatlarni ko'rsatish foydalanuvchini chalg'itadi va u dastur
     * buzilgan deb o'ylaydi.
     */
    fun forRole(role: String, provisioned: Boolean = true): List<TabItem> {
        if (!provisioned) return listOf(JOIN)
        return when (role) {
            "warehouse" -> listOf(INVENTORY, ORDERS, SYNC)
            "cashier" -> listOf(PAYMENTS, CUSTOMERS, SYNC)
            "manager", "owner" -> listOf(ORDERS, CUSTOMERS, INVENTORY, PAYMENTS, SYNC)
            else -> listOf(ORDERS, CUSTOMERS, PAYMENTS, SYNC)   // agent
        }
    }
}

@Composable
fun StatusChip(text: String, tone: StatusTone, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        color = StatusColors.of(tone).copy(alpha = 0.16f),
        shape = MaterialTheme.shapes.small,
    ) {
        Text(
            text = text,
            color = StatusColors.of(tone),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
        )
    }
}

@Composable
fun EmptyState(title: String, hint: String, modifier: Modifier = Modifier) {
    Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.padding(32.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(
                hint,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
fun ListRow(
    title: String,
    subtitle: String,
    trailing: String,
    tone: StatusTone? = null,
    trailingLabel: String? = null,
) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp)) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                title,
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.weight(1f),
            )
            Text(trailing, style = MaterialTheme.typography.titleMedium)
        }
        Row(
            Modifier.fillMaxWidth().padding(top = 4.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.weight(1f),
            )
            if (tone != null && trailingLabel != null) {
                StatusChip(trailingLabel, tone)
            }
        }
    }
    HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f))
}

// --- ekranlar -------------------------------------------------------------

data class OrderRow(
    val number: String,
    val customerName: String,
    val stateLabel: String,
    val tone: StatusTone,
    val total: Long,
    val syncLabel: String,
)

@Composable
fun OrdersScreen(orders: List<OrderRow>, modifier: Modifier = Modifier) {
    if (orders.isEmpty()) {
        EmptyState(
            "Buyurtma yo'q",
            "Mijozni tanlab birinchi buyurtmani yozing. Internet bo'lmasa " +
                "ham buyurtma telefonda saqlanadi.",
            modifier,
        )
        return
    }
    LazyColumn(modifier.fillMaxSize()) {
        items(orders, key = { it.number }) { order ->
            ListRow(
                title = order.number,
                subtitle = "${order.customerName} · ${order.syncLabel}",
                trailing = Formatting.money(order.total),
                tone = order.tone,
                trailingLabel = order.stateLabel,
            )
        }
    }
}

data class CustomerRow(
    val code: String,
    val name: String,
    val phone: String?,
    val debt: Long,
    val overLimit: Boolean,
)

@Composable
fun CustomersScreen(customers: List<CustomerRow>, modifier: Modifier = Modifier) {
    var query by remember { mutableStateOf("") }
    val filtered = remember(customers, query) {
        if (query.isBlank()) customers
        else customers.filter {
            it.name.contains(query, true) || it.code.contains(query, true) ||
                it.phone.orEmpty().contains(query)
        }
    }

    Column(modifier.fillMaxSize()) {
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            label = { Text("Mijoz qidirish") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth().padding(16.dp),
        )
        if (filtered.isEmpty()) {
            EmptyState("Mijoz topilmadi", "Boshqa nom yoki kod bilan qidirib ko'ring")
            return@Column
        }
        LazyColumn(Modifier.fillMaxSize()) {
            items(filtered, key = { it.code }) { customer ->
                ListRow(
                    title = customer.name,
                    subtitle = "${customer.code} · ${customer.phone ?: "telefon yo'q"}",
                    trailing = Formatting.money(customer.debt),
                    // Qarz yo'q bo'lsa yorliq umuman ko'rsatilmaydi —
                    // "0 UZS · Qarz" chalkash ko'rinadi.
                    tone = when {
                        customer.overLimit -> StatusTone.ERROR
                        customer.debt > 0 -> StatusTone.WARNING
                        customer.debt < 0 -> StatusTone.OK
                        else -> null
                    },
                    trailingLabel = when {
                        customer.overLimit -> "Limit oshgan"
                        customer.debt > 0 -> "Qarz"
                        customer.debt < 0 -> "Avans"
                        else -> null
                    },
                )
            }
        }
    }
}

data class StockRow(
    val sku: String,
    val name: String,
    val quantity: String,
    val minStock: String,
    val belowMinimum: Boolean,
)

@Composable
fun InventoryScreen(stock: List<StockRow>, modifier: Modifier = Modifier) {
    if (stock.isEmpty()) {
        EmptyState("Qoldiq ma'lumoti yo'q", "Ombor kirimini yozing yoki sinxronizatsiyani kuting", modifier)
        return
    }
    LazyColumn(modifier.fillMaxSize()) {
        items(stock, key = { it.sku }) { row ->
            ListRow(
                title = row.name,
                subtitle = "${row.sku} · minimal ${Formatting.quantity(row.minStock)}",
                trailing = Formatting.quantity(row.quantity),
                tone = if (row.belowMinimum) StatusTone.WARNING else StatusTone.OK,
                trailingLabel = if (row.belowMinimum) "Kam qoldi" else "Yetarli",
            )
        }
    }
}

data class PaymentRow(
    val number: String,
    val customerName: String,
    val amount: Long,
    val direction: String,
    val isReversed: Boolean,
)

@Composable
fun PaymentsScreen(payments: List<PaymentRow>, modifier: Modifier = Modifier) {
    if (payments.isEmpty()) {
        EmptyState("To'lov yo'q", "Mijozdan to'lov qabul qilganingizda shu yerda ko'rinadi", modifier)
        return
    }
    LazyColumn(modifier.fillMaxSize()) {
        items(payments, key = { it.number }) { payment ->
            ListRow(
                title = payment.customerName,
                subtitle = "${payment.number} · ${if (payment.direction == "IN") "Kirim" else "Chiqim"}",
                trailing = Formatting.money(payment.amount),
                tone = if (payment.isReversed) StatusTone.WARNING else StatusTone.OK,
                trailingLabel = if (payment.isReversed) "Bekor qilingan" else "Amalda",
            )
        }
    }
}

data class SyncState(
    val connected: Boolean,
    val queued: Int,
    val deadLetters: Int,
    val devices: Int,
    val publicPilot: Boolean,
    val protocolVersion: String,
    val epoch: Int,
)

@Composable
fun SyncScreen(state: SyncState, modifier: Modifier = Modifier) {
    Column(
        modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        val (label, tone) = when {
            // Muammo bo'lsa «hammasi joyida» DEYILMAYDI. Aks holda
            // foydalanuvchi pastdagi sonni ko'radi va yuqoridagi yashil
            // yozuvga ishonmay qoladi.
            state.deadLetters > 0 ->
                "${state.deadLetters} ta yozuv qabul qilinmadi" to StatusTone.WARNING
            state.connected && state.queued == 0 -> "Hammasi sinxronlangan" to StatusTone.OK
            state.connected -> "Yuborilmoqda (${state.queued})" to StatusTone.PROGRESS
            state.queued > 0 ->
                "Ulanish yo'q — ${state.queued} ta yozuv navbatda" to StatusTone.WARNING
            else -> "Ulanish yo'q" to StatusTone.WARNING
        }

        Card(colors = CardDefaults.cardColors()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                StatusChip(label, tone)
                Text(
                    if (state.connected) {
                        "Ma'lumotlar boshqa qurilmalar bilan almashinmoqda."
                    } else {
                        "Ishlashda davom eting — hamma narsa telefonda saqlanadi va " +
                            "internet paydo bo'lishi bilan avtomatik yuboriladi."
                    },
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                InfoLine("Ulangan qurilmalar", state.devices.toString())
                InfoLine("Navbatdagi yozuvlar", state.queued.toString())
                // «Yuborilmagan» EMAS: bu bizdan chiqmagan yozuvlar
                // emas, bizga kelib rad etilganlari. Ikkisi butunlay
                // boshqa muammo va ularni chalkashtirish diagnostikani
                // noto'g'ri yo'nalishga buradi.
                InfoLine("Qabul qilinmagan", state.deadLetters.toString())
                InfoLine("Xavfsizlik protokoli", "AETHER-Q ${state.protocolVersion}")
                InfoLine("Kalit avlodi", "#${state.epoch}")
            }
        }

        if (state.publicPilot) {
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = StatusColors.warning.copy(alpha = 0.14f)
                )
            ) {
                Text(
                    "Ochiq (sinov) broker ishlatilmoqda. Xabar mazmuni himoyalangan, " +
                        "biroq brokerning mavjudligi kafolatlanmaydi. Haqiqiy mijoz " +
                        "ma'lumotlari uchun xususiy broker sozlang.",
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(16.dp),
                )
            }
        }
    }
}

@Composable
private fun InfoLine(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(
            label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
    }
}

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun DistribosApp(
    role: String,
    orders: List<OrderRow>,
    customers: List<CustomerRow>,
    stock: List<StockRow>,
    payments: List<PaymentRow>,
    syncState: SyncState,
    provisioned: Boolean = true,
    joinState: JoinUiState = JoinUiState.Idle,
    onQrScanned: (ByteArray) -> Unit = {},
    onManualCode: (String) -> Unit = {},
    onStartScan: () -> Unit = {},
    onCancelJoin: () -> Unit = {},
) {
    val tabs = remember(role, provisioned) { RoleTabs.forRole(role, provisioned) }
    var selected by remember(role, provisioned) { mutableStateOf(tabs.first().key) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("DistribOS AI", style = MaterialTheme.typography.titleLarge)
                        Text(
                            tabs.firstOrNull { it.key == selected }?.title.orEmpty(),
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                ),
            )
        },
        bottomBar = {
            NavigationBar {
                for (tab in tabs) {
                    NavigationBarItem(
                        selected = selected == tab.key,
                        onClick = { selected = tab.key },
                        icon = { Icon(tab.icon, contentDescription = tab.title) },
                        label = { Text(tab.title) },
                    )
                }
            }
        },
    ) { padding ->
        Box(Modifier.padding(padding)) {
            when (selected) {
                "orders" -> OrdersScreen(orders)
                "customers" -> CustomersScreen(customers)
                "inventory" -> InventoryScreen(stock)
                "payments" -> PaymentsScreen(payments)
                "sync" -> SyncScreen(syncState)
                "join" -> JoinScreen(
                    state = joinState,
                    onQrScanned = onQrScanned,
                    onManualCode = onManualCode,
                    onStartScan = onStartScan,
                    onCancel = onCancelJoin,
                )
            }
        }
    }
}
