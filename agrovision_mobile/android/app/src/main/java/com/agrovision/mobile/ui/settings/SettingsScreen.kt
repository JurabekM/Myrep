package com.agrovision.mobile.ui.settings

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.agrovision.mobile.config.BuildInfo
import com.agrovision.mobile.ui.common.SectionTitle
import com.agrovision.mobile.ui.nav.AppScaffold
import com.agrovision.mobile.ui.nav.logoutAndReturn

@Composable
fun SettingsScreen(navController: NavHostController, viewModel: SettingsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    AppScaffold(navController, "Sozlamalar", onLogout = { navController.logoutAndReturn() }) { padding ->
        Column(Modifier.padding(padding).padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            SectionTitle("Ko'rinish")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(selected = state.theme == "light", onClick = { viewModel.setTheme("light") }, label = { Text("Kunduzgi") })
                FilterChip(selected = state.theme == "dark", onClick = { viewModel.setTheme("dark") }, label = { Text("Tungi") })
            }

            SectionTitle("Til")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(selected = state.language == "uz", onClick = { viewModel.setLanguage("uz") }, label = { Text("O'zbekcha") })
                FilterChip(selected = state.language == "ru", onClick = { viewModel.setLanguage("ru") }, label = { Text("Русский") })
                FilterChip(selected = state.language == "en", onClick = { viewModel.setLanguage("en") }, label = { Text("English") })
            }

            Button(onClick = viewModel::save) { Text("Saqlash") }
            if (state.saved) Text("Sozlamalar saqlandi.", color = MaterialTheme.colorScheme.primary)

            HorizontalDivider(Modifier.padding(vertical = 8.dp))
            SectionTitle("Ilova haqida")
            Text("AgroVision Mobile v${BuildInfo.VERSION_NAME}")
            Text(
                "Fermer/xo'jalik/dala/hosildorlik/sug'orish/moliya/bozor ma'lumotlari qurilma ichida " +
                    "saqlanadi — hech qanday serverga yuborilmaydi. Faqat Ob-havo bo'limi haqiqiy " +
                    "tarixiy/joriy ma'lumot uchun Open-Meteo (bepul, kalitsiz) ochiq API'siga ulanadi; " +
                    "internet bo'lmasa ilova qolgan barcha bo'limlarda to'liq ishlayveradi.",
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}
