package com.smartmoliya.app.feature.reports.presentation

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.smartmoliya.app.core.network.dto.CategoryBreakdownItemDto
import com.smartmoliya.app.ui.components.EmptyState
import com.smartmoliya.app.ui.components.SectionHeader
import com.smartmoliya.app.ui.components.formatAmount

private val PieColors = listOf(
    Color(0xFF10B981), Color(0xFF3B82F6), Color(0xFFF59E0B), Color(0xFFA855F7),
    Color(0xFFEF4444), Color(0xFF06B6D4), Color(0xFFEC4899), Color(0xFF84CC16)
)

@Composable
fun ReportsScreen(viewModel: ReportsViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(text = "Joriy oy hisoboti", style = MaterialTheme.typography.headlineSmall)
        }

        item {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                StatCard(
                    label = "Daromad",
                    value = formatAmount(state.totalIncome),
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.weight(1f)
                )
                StatCard(
                    label = "Xarajat",
                    value = formatAmount(state.totalExpense),
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.weight(1f)
                )
            }
        }

        if (state.byCategory.isEmpty()) {
            item { EmptyState(emoji = "📊", text = "Bu davrda xarajat yozilmagan") }
        } else {
            item {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(20.dp))
                        .padding(16.dp)
                ) {
                    CategoryPieChart(items = state.byCategory)
                }
            }

            item { SectionHeader(title = "Kategoriyalar bo'yicha") }
            items(state.byCategory, key = { it.category_id }) { item ->
                CategoryBreakdownRow(
                    item = item,
                    color = PieColors[
                        Math.floorMod(item.category_id.hashCode(), PieColors.size)
                    ]
                )
            }
        }

        item {
            if (state.exportsAvailable) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 8.dp)) {
                    OutlinedButton(onClick = { viewModel.exportPdf() }) { Text("PDF eksport") }
                    OutlinedButton(onClick = { viewModel.exportExcel() }) { Text("Excel eksport") }
                }
            } else {
                OutlinedButton(onClick = { viewModel.exportCsv() }, modifier = Modifier.padding(top = 8.dp)) {
                    Text("CSV eksport (Excel'da ochiladi)")
                }
            }
            state.exportedFilePath?.let { path ->
                Text(
                    text = "Saqlandi: $path",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            state.errorMessage?.let { message ->
                Text(text = message, color = MaterialTheme.colorScheme.error)
            }
        }
    }
}

@Composable
private fun StatCard(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(20.dp))
            .padding(16.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Canvas(modifier = Modifier.size(10.dp)) { drawCircle(color = color) }
            Text(
                text = label,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(start = 6.dp)
            )
        }
        Text(
            text = value,
            style = MaterialTheme.typography.titleLarge,
            color = color,
            maxLines = 1,
            modifier = Modifier.padding(top = 6.dp)
        )
        Text(
            text = "UZS",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun CategoryPieChart(items: List<CategoryBreakdownItemDto>) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Canvas(modifier = Modifier.size(150.dp)) {
            var startAngle = -90f
            items.forEach { item ->
                val sweep = (item.percent / 100f * 360f).toFloat()
                drawArc(
                    color = PieColors[Math.floorMod(item.category_id.hashCode(), PieColors.size)],
                    startAngle = startAngle,
                    sweepAngle = sweep,
                    useCenter = true,
                    size = Size(size.width, size.height)
                )
                startAngle += sweep
            }
        }
        Column(modifier = Modifier.padding(start = 16.dp)) {
            items.take(6).forEach { item ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Canvas(modifier = Modifier.size(10.dp)) {
                        drawCircle(
                            color = PieColors[Math.floorMod(item.category_id.hashCode(), PieColors.size)]
                        )
                    }
                    Text(
                        text = " ${item.category_name}",
                        style = MaterialTheme.typography.labelMedium,
                        maxLines = 1
                    )
                }
            }
        }
    }
}

@Composable
private fun CategoryBreakdownRow(item: CategoryBreakdownItemDto, color: Color) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(16.dp))
            .padding(14.dp)
    ) {
        Row(
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Canvas(modifier = Modifier.size(10.dp)) { drawCircle(color = color) }
                Text(
                    text = " ${item.category_name}",
                    style = MaterialTheme.typography.titleSmall
                )
            }
            Text(
                text = "${formatAmount(item.amount)} (${item.percent}%)",
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Bold
            )
        }
        LinearProgressIndicator(
            progress = { (item.percent / 100f).toFloat().coerceIn(0f, 1f) },
            color = color,
            trackColor = MaterialTheme.colorScheme.surfaceVariant,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 8.dp)
        )
    }
}
