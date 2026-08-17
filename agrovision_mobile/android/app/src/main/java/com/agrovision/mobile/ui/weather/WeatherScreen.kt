package com.agrovision.mobile.ui.weather

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudDownload
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.agrovision.mobile.ui.common.EmptyState
import com.agrovision.mobile.ui.common.LoadingState
import com.agrovision.mobile.ui.common.SectionTitle
import com.agrovision.mobile.ui.common.SimpleBarChart
import com.agrovision.mobile.ui.common.SimpleDropdown
import com.agrovision.mobile.ui.common.SimpleLineChart
import com.agrovision.mobile.ui.nav.AppScaffold
import com.agrovision.mobile.ui.nav.logoutAndReturn
import java.time.LocalDate

@Composable
fun WeatherScreen(navController: NavHostController, viewModel: WeatherViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    AppScaffold(navController, "Ob-havo monitoringi", onLogout = { navController.logoutAndReturn() }) { padding ->
        Column(Modifier.padding(padding).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            SimpleDropdown("Tuman", state.districts, state.selected, { it.label }, { viewModel.select(it) })

            ElevatedCard {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        "Tarixiy ma'lumot Open-Meteo (bepul, kalitsiz ochiq API) orqali internetdan yuklanadi va " +
                            "qurilmada keshlanadi. Internet bo'lmasa — so'nggi keshlangan ma'lumot ko'rsatiladi.",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Button(onClick = viewModel::refreshFromInternet, enabled = !state.loading) {
                        Icon(Icons.Filled.CloudDownload, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Internetdan yangilash")
                    }
                    state.statusMessage?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                }
            }

            if (state.loading) { LoadingState(); return@AppScaffold }

            SectionTitle("7 kunlik prognoz")
            when {
                state.forecastLoading -> LoadingState()
                state.forecast.isNullOrEmpty() -> EmptyState("Prognoz mavjud emas (internetga ulaning yoki keyinroq urinib ko'ring).")
                else -> LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(state.forecast!!) { day ->
                        ElevatedCard {
                            Column(Modifier.padding(10.dp).widthIn(min = 84.dp), horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
                                Text(day.date.toString().takeLast(5), style = MaterialTheme.typography.labelSmall)
                                Text("${day.tMax.toInt()}°/${day.tMin.toInt()}°", style = MaterialTheme.typography.titleSmall)
                                Text("${"%.1f".format(day.precip)} mm", style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                }
            }

            if (!state.hasCachedData) {
                EmptyState("Bu tuman uchun hali tarixiy ma'lumot yuklanmagan. \"Internetdan yangilash\" tugmasini bosing.")
                return@AppScaffold
            }

            val monthly = state.history.groupBy { LocalDate.ofEpochDay(it.epochDay).let { d -> "${d.year}-%02d".format(d.monthValue) } }
                .toSortedMap()
                .mapValues { (_, rows) -> Triple(rows.map { it.tMax }.average(), rows.map { it.tMin }.average(), rows.sumOf { it.precipitationMm }) }

            if (monthly.isNotEmpty()) {
                SectionTitle("Harorat, so'nggi 12 oy (°C)")
                SimpleLineChart(
                    labels = monthly.keys.toList(),
                    series = mapOf("Maks" to monthly.values.map { it.first }, "Min" to monthly.values.map { it.second }),
                )
                SectionTitle("Oylik yog'ingarchilik (mm)")
                SimpleBarChart(labels = monthly.keys.map { it.takeLast(2) }, values = monthly.values.map { it.third })
            }

            if (state.climate.isNotEmpty()) {
                SectionTitle("Ko'p yillik iqlim profili")
                SimpleLineChart(
                    labels = state.climate.map { viewModel.monthLabel(it.month) },
                    series = mapOf("Maks" to state.climate.map { it.tMax }, "Min" to state.climate.map { it.tMin }),
                )
                SimpleBarChart(labels = state.climate.map { viewModel.monthLabel(it.month) }, values = state.climate.map { it.precip })
            }
        }
    }
}
