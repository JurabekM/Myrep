package uz.qarzsiz.app.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.listSaver
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import uz.qarzsiz.app.AppViewModel

/** Ekranlar. Matn ko'rinishida — aylantirishda (rotation) saqlanadi. */
sealed interface Route {
    val key: String

    data object Home : Route { override val key = "home" }
    data object Debts : Route { override val key = "debts" }
    data object Plan : Route { override val key = "plan" }
    data object Calc : Route { override val key = "calc" }
    data object More : Route { override val key = "more" }
    data class DebtDetail(val id: String) : Route { override val key = "detail:$id" }
    data class DebtEdit(val id: String?) : Route { override val key = "edit:${id ?: ""}" }
    data object Guide : Route { override val key = "guide" }
    data object Habits : Route { override val key = "habits" }
    data object Help : Route { override val key = "help" }
    data object Rates : Route { override val key = "rates" }
    data object Backup : Route { override val key = "backup" }
    data object About : Route { override val key = "about" }
    data object Reminders : Route { override val key = "reminders" }

    companion object {
        val tabs = listOf(Home, Debts, Plan, Calc, More)
        fun parse(key: String): Route = when {
            key.startsWith("detail:") -> DebtDetail(key.removePrefix("detail:"))
            key.startsWith("edit:") -> DebtEdit(key.removePrefix("edit:").ifEmpty { null })
            else -> listOf(Home, Debts, Plan, Calc, More, Guide, Habits, Help, Rates, Backup, About, Reminders)
                .firstOrNull { it.key == key } ?: Home
        }
    }
}

class Nav(initial: List<Route>) {
    val stack = mutableStateListOf<Route>().apply { addAll(initial) }
    val current: Route get() = stack.last()
    fun go(r: Route) { stack.add(r) }
    fun tab(r: Route) { stack.clear(); stack.add(r) }
    fun back(): Boolean = if (stack.size > 1) { stack.removeAt(stack.lastIndex); true } else false
    /** Joriy ekranni almashtirish (masalan, saqlangandan keyin tahrirdan kartochkaga). */
    fun replace(r: Route) { stack[stack.lastIndex] = r }

    companion object {
        val saver = listSaver<Nav, String>(
            save = { nav -> nav.stack.map { it.key } },
            restore = { keys -> Nav(keys.map(Route::parse).ifEmpty { listOf(Route.Home) }) },
        )
    }
}

@Composable
fun QarzsizApp(vm: AppViewModel) {
    val status by vm.status.collectAsStateWithLifecycle()
    val state by vm.state.collectAsStateWithLifecycle()
    CompositionLocalProvider(LocalScript provides state.script) {
    Box(Modifier.fillMaxSize().background(Tok.paper).safeDrawingPadding()) {
        when (val s = status) {
            AppViewModel.Status.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = Tok.accent)
            }
            is AppViewModel.Status.Broken -> BrokenScreen(s.reason, onWipe = vm::wipeAll)
            AppViewModel.Status.Ready ->
                if (!state.onboardingDone) OnboardingScreen(vm) else MainShell(vm)
        }
    }
    }
}

@Composable
private fun MainShell(vm: AppViewModel) {
    val nav = rememberSaveable(saver = Nav.saver) { Nav(listOf(Route.Home)) }
    BackHandler(enabled = nav.stack.size > 1) { nav.back() }
    val current = nav.current
    val saveFailed by vm.saveFailed.collectAsStateWithLifecycle()
    Column(Modifier.fillMaxSize()) {
        if (saveFailed) {
            Text(
                "Ma'lumot saqlanmadi: telefon xotirasi to'lgan bo'lishi mumkin. Joy bo'shatib, qaytadan urinib ko'ring.",
                style = MaterialTheme.typography.bodySmall,
                color = Tok.accentInk,
                modifier = Modifier.fillMaxWidth().background(Tok.danger).padding(12.dp),
            )
        }
        Box(Modifier.weight(1f)) {
            when (current) {
                Route.Home -> HomeScreen(vm, nav)
                Route.Debts -> DebtsScreen(vm, nav)
                Route.Plan -> PlanScreen(vm, nav)
                Route.Calc -> CalculatorScreen()
                Route.More -> MoreScreen(vm, nav)
                is Route.DebtDetail -> DebtDetailScreen(vm, nav, current.id)
                is Route.DebtEdit -> DebtEditScreen(vm, nav, current.id)
                Route.Guide -> GuideScreen(vm, nav)
                Route.Habits -> HabitsScreen(vm, nav)
                Route.Help -> HelpScreen(nav)
                Route.Rates -> RatesScreen(vm, nav)
                Route.Backup -> BackupScreen(vm, nav)
                Route.About -> AboutScreen(nav)
                Route.Reminders -> RemindersScreen(vm, nav)
            }
        }
        val rootTab = nav.stack.first()
        NavigationBar(containerColor = Tok.sidebar) {
            tabItem(nav, rootTab, Route.Home, "Bosh", Icons.Filled.Home)
            tabItem(nav, rootTab, Route.Debts, "Qarzlar", Icons.AutoMirrored.Filled.List)
            tabItem(nav, rootTab, Route.Plan, "Reja", Icons.Filled.DateRange)
            tabItem(nav, rootTab, Route.Calc, "Nasiya", Icons.Filled.ShoppingCart)
            tabItem(nav, rootTab, Route.More, "Yana", Icons.Filled.Menu)
        }
    }
}

@Composable
private fun androidx.compose.foundation.layout.RowScope.tabItem(
    nav: Nav,
    rootTab: Route,
    tab: Route,
    label: String,
    icon: ImageVector,
) {
    NavigationBarItem(
        selected = rootTab == tab,
        onClick = { nav.tab(tab) },
        modifier = Modifier.testTag("tab_${tab.key}"),
        icon = { Icon(icon, contentDescription = null) },
        label = { Text(label, style = MaterialTheme.typography.labelSmall) },
        colors = NavigationBarItemDefaults.colors(
            selectedIconColor = Tok.accentInk,
            selectedTextColor = Tok.accentText,
            indicatorColor = Tok.accent,
            unselectedIconColor = Tok.inkMuted,
            unselectedTextColor = Tok.inkMuted,
        ),
    )
}

@Composable
private fun BrokenScreen(reason: String, onWipe: () -> Unit) {
    val confirm = remember { mutableStateListOf<Boolean>() }
    Column(
        Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
    ) {
        Text("Ma'lumotni ochib bo'lmadi", style = MaterialTheme.typography.headlineSmall, color = Tok.ink)
        Muted(
            "Shifrlangan fayl o'qilmadi ($reason). Bu odatda ilova boshqa qurilmadan tiklanganda yoki " +
                "qurilma xavfsizlik sozlamalari o'zgarganda bo'ladi. Zaxira nusxangiz bo'lsa, ma'lumotni " +
                "o'chirib, keyin «Yana → Zaxira nusxa» orqali tiklang.",
        )
        if (confirm.isEmpty()) {
            SecondaryButton("Ma'lumotni o'chirib, qaytadan boshlash", color = Tok.danger) { confirm.add(true) }
        } else {
            Notice("Hamma qarz va to'lov yozuvlari o'chadi. Davom etasizmi?", Tok.danger)
            PrimaryButton("Ha, o'chirish") { onWipe() }
            SecondaryButton("Bekor qilish") { confirm.clear() }
        }
    }
}
