package com.uzerp.mobile.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.automirrored.filled.TrendingUp
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.Backup
import androidx.compose.material.icons.filled.Badge
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.ManageAccounts
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.PointOfSale
import androidx.compose.material.icons.filled.ReceiptLong
import androidx.compose.material.icons.filled.RequestQuote
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material.icons.filled.TrackChanges
import androidx.compose.material.icons.filled.Wallet
import androidx.compose.material.icons.filled.Warehouse
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.uzerp.mobile.core.Rbac
import com.uzerp.mobile.core.money
import com.uzerp.mobile.data.repository.DashboardKpis
import com.uzerp.mobile.ui.auth.AuthViewModel
import com.uzerp.mobile.ui.nav.Routes
import com.uzerp.mobile.ui.theme.UzAccent
import com.uzerp.mobile.ui.theme.UzAmber
import com.uzerp.mobile.ui.theme.UzCyan
import com.uzerp.mobile.ui.theme.UzGradEnd
import com.uzerp.mobile.ui.theme.UzGradMid
import com.uzerp.mobile.ui.theme.UzGradStart
import com.uzerp.mobile.ui.theme.UzGreen
import com.uzerp.mobile.ui.theme.UzIndigo
import com.uzerp.mobile.ui.theme.UzMuted
import com.uzerp.mobile.ui.theme.UzOrange
import com.uzerp.mobile.ui.theme.UzPink
import com.uzerp.mobile.ui.theme.UzTeal
import com.uzerp.mobile.ui.theme.UzViolet

/** [route] null bo'lsa modul hali keyingi versiyada qo'shiladi. */
private data class ModuleTile(
    val title: String,
    val permission: String,
    val icon: ImageVector,
    val tint: Color,
    val route: String?,
)

private val ALL_MODULES = listOf(
    ModuleTile("Savdo hujjatlari", "sales.view", Icons.Filled.ReceiptLong, UzAccent, Routes.SALES_LIST),
    ModuleTile("POS kassa", "pos.operate", Icons.Filled.PointOfSale, UzGreen, Routes.POS),
    ModuleTile("Mahsulotlar", "inventory.view", Icons.Filled.Inventory2, UzViolet, Routes.PRODUCTS),
    ModuleTile("Ombor qoldiqlari", "inventory.view", Icons.Filled.Warehouse, UzTeal, Routes.STOCK),
    ModuleTile("Xaridlar", "purchases.view", Icons.Filled.LocalShipping, UzOrange, Routes.PURCHASES_LIST),
    ModuleTile("Mijozlar", "customers.view", Icons.Filled.People, UzCyan, Routes.CUSTOMERS),
    ModuleTile("Ta'minotchilar", "suppliers.view", Icons.Filled.Storefront, UzIndigo, Routes.SUPPLIERS),
    ModuleTile("CRM (leadlar)", "crm.view", Icons.Filled.TrackChanges, UzPink, Routes.CRM_LEADS),
    ModuleTile("Kassa / Bank", "cash.view", Icons.Filled.Wallet, UzGreen, Routes.CASH),
    ModuleTile("Buxgalteriya", "accounting.view", Icons.Filled.AccountBalance, UzAccent, Routes.ACCOUNTING),
    ModuleTile("Xodimlar / HR", "hr.view", Icons.Filled.Badge, UzViolet, Routes.HR),
    ModuleTile("Ish haqi", "payroll.view", Icons.Filled.RequestQuote, UzAmber, Routes.PAYROLL_LIST),
    ModuleTile("Hisobotlar", "reports.view", Icons.Filled.Assessment, UzTeal, Routes.REPORTS),
    ModuleTile("Analitika", "analytics.view", Icons.Filled.Analytics, UzOrange, Routes.ANALYTICS),
    ModuleTile("Zaxira nusxa", "backup.manage", Icons.Filled.Backup, UzCyan, Routes.BACKUP),
    ModuleTile("Foydalanuvchilar", "users.manage", Icons.Filled.ManageAccounts, UzMuted, null),
)

@Composable
fun DashboardScreen(
    authViewModel: AuthViewModel,
    onNavigate: (String) -> Unit,
    dashboardViewModel: DashboardViewModel = hiltViewModel(),
) {
    val user by authViewModel.currentUser.collectAsState()
    val role = user?.role ?: "guest"
    val visibleModules = ALL_MODULES.filter { Rbac.hasPermission(role, it.permission) }
    val dashboardState by dashboardViewModel.state.collectAsState()
    LaunchedEffect(Unit) { dashboardViewModel.reload() }

    LazyVerticalGrid(
        columns = GridCells.Fixed(2),
        modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
    ) {
        item(span = { GridItemSpan(2) }) {
            GradientHeader(
                fullName = user?.fullName?.ifBlank { user?.username } ?: "",
                roleLabel = Rbac.roleLabels[role] ?: role,
                onLogout = { authViewModel.logout() },
            )
        }

        dashboardState.kpis?.let { kpis ->
            item { KpiCard("Bugungi savdo", money(kpis.todaySales), Icons.AutoMirrored.Filled.TrendingUp, UzGreen) }
            item { KpiCard("Shu oy savdo", money(kpis.monthSales), Icons.Filled.CalendarMonth, UzAccent) }
            item { KpiCard("Kassa", money(kpis.cashBalance), Icons.Filled.Payments, UzTeal) }
            item { KpiCard("Bank", money(kpis.bankBalance), Icons.Filled.AccountBalance, UzIndigo) }
            item {
                KpiCard(
                    "Kam qolgan mahsulot", kpis.lowStockCount.toString(),
                    Icons.Filled.WarningAmber, if (kpis.lowStockCount > 0) UzAmber else UzGreen,
                )
            }
            item { KpiCard("Faol xodimlar", kpis.activeEmployees.toString(), Icons.Filled.Groups, UzViolet) }
        }

        item(span = { GridItemSpan(2) }) {
            Column(modifier = Modifier.padding(top = 8.dp)) {
                Text("Modullar", style = MaterialTheme.typography.titleMedium)
                Text(
                    "${Rbac.roleLabels[role]} roli uchun ${visibleModules.size} ta modul",
                    style = MaterialTheme.typography.bodyMedium,
                    color = UzMuted,
                )
            }
        }

        items(visibleModules, key = { it.title }) { module ->
            ModuleCard(module) { route -> onNavigate(route) }
        }
    }
}

/** Gradientli sarlavha: foydalanuvchi avatari, ism, rol va chiqish tugmasi. */
@Composable
private fun GradientHeader(fullName: String, roleLabel: String, onLogout: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                brush = Brush.linearGradient(listOf(UzGradStart, UzGradMid, UzGradEnd)),
                shape = RoundedCornerShape(24.dp),
            )
            .padding(20.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(52.dp)
                    .background(Color.White.copy(alpha = 0.22f), CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    fullName.trim().take(1).uppercase().ifBlank { "U" },
                    style = MaterialTheme.typography.headlineSmall,
                    color = Color.White,
                )
            }
            Column(modifier = Modifier.weight(1f).padding(start = 14.dp)) {
                Text("UzERP", style = MaterialTheme.typography.labelMedium, color = Color.White.copy(alpha = 0.75f))
                Text(
                    fullName,
                    style = MaterialTheme.typography.titleMedium,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(6.dp))
                Surface(color = Color.White.copy(alpha = 0.18f), shape = RoundedCornerShape(20.dp)) {
                    Text(
                        roleLabel,
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.White,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                    )
                }
            }
            IconButton(onClick = onLogout) {
                Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = "Chiqish", tint = Color.White)
            }
        }
    }
}

/** KPI kartochkasi: rangli ikonka konteyneri + qiymat + yorliq. */
@Composable
private fun KpiCard(label: String, value: String, icon: ImageVector, tint: Color) {
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .background(tint.copy(alpha = 0.16f), RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(22.dp))
            }
            Spacer(Modifier.height(12.dp))
            Text(
                value,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
            )
            Text(label, style = MaterialTheme.typography.labelSmall, color = UzMuted, maxLines = 1)
        }
    }
}

/** Modul kartochkasi: rangli ikonka + nom. */
@Composable
private fun ModuleCard(module: ModuleTile, onOpen: (String) -> Unit) {
    val enabled = module.route != null
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        onClick = { module.route?.let(onOpen) },
        enabled = enabled,
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .background(module.tint.copy(alpha = 0.16f), RoundedCornerShape(14.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(module.icon, contentDescription = null, tint = module.tint, modifier = Modifier.size(24.dp))
            }
            Spacer(Modifier.height(12.dp))
            Text(
                module.title,
                style = MaterialTheme.typography.titleSmall,
                color = if (enabled) MaterialTheme.colorScheme.onSurface else UzMuted,
                maxLines = 1,
            )
            if (!enabled) {
                Text("Tez orada", style = MaterialTheme.typography.labelSmall, color = UzMuted)
            }
        }
    }
}
