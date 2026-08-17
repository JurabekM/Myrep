package com.agrovision.mobile.ui.nav

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.agrovision.mobile.ui.admin.AdminScreen
import com.agrovision.mobile.ui.ai.AiScreen
import com.agrovision.mobile.ui.analytics.AnalyticsScreen
import com.agrovision.mobile.ui.dashboard.DashboardScreen
import com.agrovision.mobile.ui.finance.FinanceScreen
import com.agrovision.mobile.ui.irrigation.IrrigationScreen
import com.agrovision.mobile.ui.login.LoginScreen
import com.agrovision.mobile.ui.map.MapScreen
import com.agrovision.mobile.ui.market.MarketScreen
import com.agrovision.mobile.ui.ml.MlScreen
import com.agrovision.mobile.ui.records.RecordsScreen
import com.agrovision.mobile.ui.reports.ReportsScreen
import com.agrovision.mobile.ui.satellite.SatelliteScreen
import com.agrovision.mobile.ui.settings.SettingsScreen
import com.agrovision.mobile.ui.weather.WeatherScreen

@Composable
fun AppNavHost() {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = Routes.LOGIN) {
        composable(Routes.LOGIN) { LoginScreen(navController) }
        composable(Routes.DASHBOARD) { DashboardScreen(navController) }
        composable(Routes.RECORDS) { RecordsScreen(navController) }
        composable(Routes.MAP) { MapScreen(navController) }
        composable(Routes.ANALYTICS) { AnalyticsScreen(navController) }
        composable(Routes.ML) { MlScreen(navController) }
        composable(Routes.WEATHER) { WeatherScreen(navController) }
        composable(Routes.MARKET) { MarketScreen(navController) }
        composable(Routes.IRRIGATION) { IrrigationScreen(navController) }
        composable(Routes.FINANCE) { FinanceScreen(navController) }
        composable(Routes.SATELLITE) { SatelliteScreen(navController) }
        composable(Routes.AI) { AiScreen(navController) }
        composable(Routes.REPORTS) { ReportsScreen(navController) }
        composable(Routes.ADMIN) { AdminScreen(navController) }
        composable(Routes.SETTINGS) { SettingsScreen(navController) }
    }
}

fun NavHostController.logoutAndReturn() {
    com.agrovision.mobile.core.Session.logout()
    navigate(Routes.LOGIN) {
        popUpTo(0) { inclusive = true }
    }
}
