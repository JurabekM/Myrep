package com.agrovision.mobile.ui.common

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.agrovision.mobile.ui.theme.ChartPalette

/** Vertikal ustunli diagramma — Compose Column/height texnikasi, Canvas'siz (barqaror va sinash oson). */
@Composable
fun SimpleBarChart(labels: List<String>, values: List<Double>, modifier: Modifier = Modifier, barColor: Color = MaterialTheme.colorScheme.primary) {
    val maxValue = (values.maxOrNull() ?: 1.0).let { if (it <= 0) 1.0 else it }
    Row(
        modifier.fillMaxWidth().height(180.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalAlignment = Alignment.Bottom,
    ) {
        labels.forEachIndexed { i, label ->
            val value = values.getOrElse(i) { 0.0 }
            val fraction = (value / maxValue).toFloat().coerceIn(0.02f, 1f)
            Column(Modifier.weight(1f).fillMaxHeight(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Bottom) {
                Box(
                    Modifier
                        .weight(1f)
                        .fillMaxWidth(0.6f)
                        .fillMaxHeight(fraction)
                        .background(barColor, RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp)),
                )
                Spacer(Modifier.height(4.dp))
                Text(label, style = MaterialTheme.typography.labelSmall, maxLines = 1)
            }
        }
    }
}

/** Chiziqli grafik (bitta yoki bir nechta seriya) — sof Canvas chizmasi. */
@Composable
fun SimpleLineChart(
    labels: List<String>,
    series: Map<String, List<Double?>>,
    modifier: Modifier = Modifier,
) {
    val colors = ChartPalette
    val allValues = series.values.flatten().filterNotNull()
    if (allValues.isEmpty()) {
        EmptyState("Ma'lumot yo'q")
        return
    }
    val minV = allValues.minOrNull() ?: 0.0
    val maxV = (allValues.maxOrNull() ?: 1.0).let { if (it - minV < 1e-6) it + 1.0 else it }

    Column(modifier.fillMaxWidth()) {
        Canvas(Modifier.fillMaxWidth().height(200.dp).padding(8.dp)) {
            val n = labels.size.coerceAtLeast(2)
            val stepX = size.width / (n - 1).coerceAtLeast(1)
            fun yFor(v: Double): Float = size.height - ((v - minV) / (maxV - minV) * size.height).toFloat()

            series.entries.forEachIndexed { seriesIdx, entry ->
                val color = colors[seriesIdx % colors.size]
                var prev: Offset? = null
                entry.value.forEachIndexed { i, v ->
                    if (v == null) {
                        prev = null
                        return@forEachIndexed
                    }
                    val point = Offset(i * stepX, yFor(v))
                    prev?.let { start -> drawLine(color, start, point, strokeWidth = 4f) }
                    drawCircle(color, radius = 4f, center = point)
                    prev = point
                }
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            series.keys.forEachIndexed { i, name ->
                LegendDot(colors[i % colors.size], name)
            }
        }
    }
}

@Composable
private fun LegendDot(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(10.dp).background(color, CircleShape))
        Spacer(Modifier.width(4.dp))
        Text(label, style = MaterialTheme.typography.labelSmall)
    }
}

/** Doiraviy (pie/donut) diagramma. */
@Composable
fun SimplePieChart(data: List<Pair<String, Double>>, modifier: Modifier = Modifier) {
    val total = data.sumOf { it.second }.let { if (it <= 0) 1.0 else it }
    val colors = ChartPalette
    Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Canvas(Modifier.size(150.dp)) {
            var startAngle = -90f
            data.forEachIndexed { i, pair ->
                val sweep = (pair.second / total * 360.0).toFloat()
                drawArc(color = colors[i % colors.size], startAngle = startAngle, sweepAngle = sweep, useCenter = true)
                startAngle += sweep
            }
        }
        Spacer(Modifier.width(16.dp))
        Column {
            data.take(8).forEachIndexed { i, pair ->
                val pct = "%.0f".format(pair.second / total * 100)
                LegendDot(colors[i % colors.size], "${pair.first} ($pct%)")
            }
        }
    }
}
