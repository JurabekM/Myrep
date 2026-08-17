package com.agrovision.mobile.ui.nav

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.ui.graphics.vector.ImageVector

data class NavItem(val route: String, val label: String, val icon: ImageVector, val permission: String)

object Routes {
    const val LOGIN = "login"
    const val DASHBOARD = "dashboard"
    const val RECORDS = "records"
    const val MAP = "map"
    const val ANALYTICS = "analytics"
    const val ML = "ml"
    const val WEATHER = "weather"
    const val MARKET = "market"
    const val IRRIGATION = "irrigation"
    const val FINANCE = "finance"
    const val SATELLITE = "satellite"
    const val AI = "ai"
    const val REPORTS = "reports"
    const val ADMIN = "admin"
    const val SETTINGS = "settings"
}

val NAV_ITEMS = listOf(
    NavItem(Routes.DASHBOARD, "Bosh sahifa", Icons.Filled.Dashboard, "view_dashboard"),
    NavItem(Routes.RECORDS, "Ma'lumotlar", Icons.Filled.PlaylistAdd, "edit_data"),
    NavItem(Routes.MAP, "Xarita", Icons.Filled.Map, "view_dashboard"),
    NavItem(Routes.ANALYTICS, "Analitika", Icons.Filled.Insights, "view_dashboard"),
    NavItem(Routes.ML, "Machine Learning", Icons.Filled.Psychology, "view_dashboard"),
    NavItem(Routes.SATELLITE, "Sun'iy yo'ldosh", Icons.Filled.SatelliteAlt, "view_dashboard"),
    NavItem(Routes.WEATHER, "Ob-havo", Icons.Filled.WbCloudy, "view_dashboard"),
    NavItem(Routes.MARKET, "Bozor", Icons.Filled.Storefront, "view_dashboard"),
    NavItem(Routes.IRRIGATION, "Sug'orish", Icons.Filled.WaterDrop, "view_dashboard"),
    NavItem(Routes.FINANCE, "Moliya", Icons.Filled.Payments, "view_finance"),
    NavItem(Routes.AI, "AI Yordamchi", Icons.Filled.SmartToy, "use_ai"),
    NavItem(Routes.REPORTS, "Hisobotlar", Icons.Filled.Description, "export_reports"),
    NavItem(Routes.ADMIN, "Administrator", Icons.Filled.AdminPanelSettings, "manage_users"),
    NavItem(Routes.SETTINGS, "Sozlamalar", Icons.Filled.Settings, "manage_settings"),
)
