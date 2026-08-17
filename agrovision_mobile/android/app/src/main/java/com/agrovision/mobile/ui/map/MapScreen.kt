package com.agrovision.mobile.ui.map

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.agrovision.mobile.ui.common.DataTable
import com.agrovision.mobile.ui.common.LoadingState
import com.agrovision.mobile.ui.common.SectionTitle
import com.agrovision.mobile.ui.nav.AppScaffold
import com.agrovision.mobile.ui.nav.logoutAndReturn
import com.agrovision.mobile.ui.theme.ChartPalette

// O'zbekiston taxminiy chegaralari — normallashtirish uchun
private const val LAT_MIN = 37.0
private const val LAT_MAX = 45.5
private const val LON_MIN = 55.5
private const val LON_MAX = 73.5

@Composable
fun MapScreen(navController: NavHostController, viewModel: MapViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    val textMeasurer = rememberTextMeasurer()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Xarita (offlayn sxematik)", onLogout = { navController.logoutAndReturn() }) { padding ->
        if (state.loading) { LoadingState(); return@AppScaffold }

        Column(Modifier.padding(padding).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(
                "Bu — viloyatlarning nisbiy joylashuvi va hosildorligini ko'rsatuvchi sxematik xarita " +
                    "(haqiqiy xarita plitkalari mobil ilovaga ulanmagan).",
                style = MaterialTheme.typography.bodySmall,
            )

            ElevatedCard {
                Canvas(
                    Modifier
                        .fillMaxWidth()
                        .height(280.dp)
                        .padding(12.dp),
                ) {
                    val maxYield = (state.points.maxOfOrNull { it.avgYield } ?: 1.0).coerceAtLeast(0.1)
                    state.points.forEachIndexed { i, point ->
                        val nx = ((point.region.lon - LON_MIN) / (LON_MAX - LON_MIN)).toFloat().coerceIn(0.05f, 0.95f)
                        val ny = (1 - (point.region.lat - LAT_MIN) / (LAT_MAX - LAT_MIN)).toFloat().coerceIn(0.05f, 0.95f)
                        val center = Offset(nx * size.width, ny * size.height)
                        val radius = 10f + (point.avgYield / maxYield * 16f).toFloat()
                        val color = ChartPalette[i % ChartPalette.size]
                        drawCircle(color, radius = radius, center = center, alpha = 0.85f)
                        drawText(textMeasurer, point.region.name, topLeft = Offset(center.x - 24f, center.y + radius + 2f))
                    }
                }
            }

            SectionTitle("Viloyatlar (hosildorlik bo'yicha)")
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
                FilterChip(selected = state.selectedRegionId == null, onClick = { viewModel.selectRegion(null) }, label = { Text("Barchasi") })
            }
            state.points.sortedByDescending { it.avgYield }.forEach { point ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .background(if (state.selectedRegionId == point.region.id) MaterialTheme.colorScheme.surfaceVariant else Color.Transparent)
                        .padding(vertical = 6.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    TextButton(onClick = { viewModel.selectRegion(point.region.id) }) {
                        Text(point.region.name)
                    }
                    Text("${point.avgYield} t/ga  •  ${"%.0f".format(point.production)} t", style = MaterialTheme.typography.bodySmall)
                }
            }

            SectionTitle("Dalalar (konturlar)")
            ElevatedCard {
                Column(Modifier.padding(12.dp)) {
                    DataTable(
                        headers = listOf("Dala", "Maydon (ga)", "Tuproq"),
                        rows = state.fields.map { listOf(it.name, "${it.areaHa}", it.soilType) },
                    )
                }
            }
        }
    }
}
