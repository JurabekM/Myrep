package com.smartmoliya.app.app

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.PieChart
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.fragment.app.FragmentActivity
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.smartmoliya.app.core.security.BiometricAuthenticator
import com.smartmoliya.app.feature.auth.presentation.LoginScreen
import com.smartmoliya.app.feature.auth.presentation.OtpLoginScreen
import com.smartmoliya.app.feature.auth.presentation.PinScreen
import com.smartmoliya.app.feature.auth.presentation.PinScreenMode
import com.smartmoliya.app.feature.auth.presentation.RegisterScreen
import com.smartmoliya.app.feature.dashboard.presentation.DashboardScreen
import com.smartmoliya.app.feature.expense.presentation.ExpenseScreen
import com.smartmoliya.app.feature.familymode.presentation.FamilyScreen
import com.smartmoliya.app.feature.gamification.presentation.GamificationScreen
import com.smartmoliya.app.feature.menu.presentation.MenuScreen
import com.smartmoliya.app.feature.payments.presentation.PaymentsScreen
import com.smartmoliya.app.feature.profile.presentation.ProfileScreen
import com.smartmoliya.app.feature.reports.presentation.ReportsScreen
import com.smartmoliya.app.feature.wallets.presentation.WalletsScreen

/** Ilova qaysi bosqichda ekanini bildiradi: auth -> (pin) -> asosiy ilova. */
private enum class AppSession { AUTH_REQUIRED, PIN_REQUIRED, PIN_SETUP, UNLOCKED }

private sealed class BottomDestination(val route: String, val label: String) {
    data object Dashboard : BottomDestination("dashboard", "Bosh sahifa")
    data object Wallets : BottomDestination("wallets", "Hamyonlar")
    data object Expense : BottomDestination("expense", "Tranzaksiyalar")
    data object Reports : BottomDestination("reports", "Hisobotlar")
    data object Menu : BottomDestination("menu", "Menyu")
}

private val bottomDestinations = listOf(
    BottomDestination.Dashboard,
    BottomDestination.Wallets,
    BottomDestination.Expense,
    BottomDestination.Reports,
    BottomDestination.Menu
)

/** Menyu ichidan ochiladigan sahifalar (bottom bar'da ko'rinmaydi). */
private object InnerRoutes {
    const val PROFILE = "profile"
    const val PAYMENTS = "payments"
    const val GAMIFICATION = "gamification"
    const val FAMILY = "family"
}

@Composable
fun SmartMoliyaNavHost(activity: FragmentActivity) {
    val rootViewModel: AppRootViewModel = hiltViewModel()
    var session by remember {
        mutableStateOf(
            when {
                // Offline flavor: server/hisob yo'q - to'g'ridan-to'g'ri PIN bosqichidan boshlanadi
                com.smartmoliya.app.BuildConfig.OFFLINE_MODE ->
                    if (rootViewModel.isPinConfigured()) AppSession.PIN_REQUIRED else AppSession.PIN_SETUP
                !rootViewModel.isLoggedIn() -> AppSession.AUTH_REQUIRED
                rootViewModel.isPinConfigured() -> AppSession.PIN_REQUIRED
                else -> AppSession.PIN_SETUP
            }
        )
    }

    when (session) {
        AppSession.AUTH_REQUIRED -> AuthNavGraph(
            onAuthenticated = {
                session = if (rootViewModel.isPinConfigured()) AppSession.PIN_REQUIRED else AppSession.PIN_SETUP
            }
        )

        AppSession.PIN_REQUIRED -> PinScreen(
            mode = PinScreenMode.UNLOCK,
            biometricAuthenticator = remember { BiometricAuthenticator(activity) },
            onUnlocked = { session = AppSession.UNLOCKED }
        )

        AppSession.PIN_SETUP -> PinScreen(
            mode = PinScreenMode.SETUP,
            biometricAuthenticator = null,
            onUnlocked = { session = AppSession.UNLOCKED }
        )

        AppSession.UNLOCKED -> MainNavGraph(
            onLoggedOut = { session = AppSession.AUTH_REQUIRED }
        )
    }
}

@Composable
private fun AuthNavGraph(onAuthenticated: () -> Unit) {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = "login") {
        composable("login") {
            LoginScreen(
                onLoginSuccess = onAuthenticated,
                onNavigateToRegister = { navController.navigate("register") },
                onNavigateToOtp = { navController.navigate("otp") }
            )
        }
        composable("register") {
            RegisterScreen(
                onRegisterSuccess = onAuthenticated,
                onNavigateToLogin = { navController.popBackStack() }
            )
        }
        composable("otp") {
            OtpLoginScreen(
                onLoginSuccess = onAuthenticated,
                onNavigateBack = { navController.popBackStack() }
            )
        }
    }
}

@Composable
private fun MainNavGraph(onLoggedOut: () -> Unit) {
    val navController = rememberNavController()

    Scaffold(
        bottomBar = {
            NavigationBar {
                val backStackEntry by navController.currentBackStackEntryAsState()
                val currentDestination = backStackEntry?.destination

                bottomDestinations.forEach { destination ->
                    val icon = when (destination) {
                        BottomDestination.Dashboard -> Icons.Default.Home
                        BottomDestination.Wallets -> Icons.Default.AccountBalanceWallet
                        BottomDestination.Expense -> Icons.Default.SwapHoriz
                        BottomDestination.Reports -> Icons.Default.PieChart
                        BottomDestination.Menu -> Icons.Default.Menu
                    }
                    NavigationBarItem(
                        selected = currentDestination?.hierarchy?.any { it.route == destination.route } == true,
                        onClick = {
                            navController.navigate(destination.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(icon, contentDescription = destination.label) },
                        label = { Text(destination.label) }
                    )
                }
            }
        }
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = BottomDestination.Dashboard.route,
            modifier = androidx.compose.ui.Modifier.padding(padding)
        ) {
            composable(BottomDestination.Dashboard.route) { DashboardScreen() }
            composable(BottomDestination.Wallets.route) { WalletsScreen() }
            composable(BottomDestination.Expense.route) { ExpenseScreen() }
            composable(BottomDestination.Reports.route) { ReportsScreen() }
            composable(BottomDestination.Menu.route) {
                MenuScreen(
                    onNavigateToPayments = { navController.navigate(InnerRoutes.PAYMENTS) },
                    onNavigateToGamification = { navController.navigate(InnerRoutes.GAMIFICATION) },
                    onNavigateToFamily = { navController.navigate(InnerRoutes.FAMILY) },
                    onNavigateToProfile = { navController.navigate(InnerRoutes.PROFILE) }
                )
            }
            composable(InnerRoutes.PROFILE) { ProfileScreen(onLoggedOut = onLoggedOut) }
            composable(InnerRoutes.PAYMENTS) { PaymentsScreen() }
            composable(InnerRoutes.GAMIFICATION) { GamificationScreen() }
            composable(InnerRoutes.FAMILY) { FamilyScreen() }
        }
    }
}
