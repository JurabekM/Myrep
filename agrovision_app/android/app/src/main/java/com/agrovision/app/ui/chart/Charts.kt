package com.agrovision.app.ui.chart

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
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agrovision.app.core.Fmt
import com.agrovision.app.ui.theme.ChartPalette
import com.agrovision.app.ui.theme.MetricHigh
import com.agrovision.app.ui.theme.MetricLow
import com.agrovision.app.ui.theme.MetricMid
import kotlin.math.abs
import kotlin.math.max

/**
 * Native grafik dvigateli — barchasi Compose `Canvas` bilan chiziladi
 * (WebView/JS kutubxonalari yo'q). Desktop ECharts panelining ekvivalenti:
 * chiziq + ishonch oralig'i, ustun, gorizontal ustun, donut, heatmap,
 * scatter va gauge.
 */

data class LineSeries(
    val name: String,
    /** null qiymatlar uzilish (prognoz chizig'i uchun). */
    val values: List<Double?>,
    val color: Color? = null,
    val dashed: Boolean = false,
)

data class ConfidenceBand(val lower: List<Double?>, val upper: List<Double?>, val color: Color? = null)

private val LabelStyle = TextStyle(fontSize = 9.sp)

@Composable
private fun ChartFrame(
    height: Int,
    legend: List<Pair<String, Color>> = emptyList(),
    content: @Composable () -> Unit,
) {
    Column(Modifier.fillMaxWidth()) {
        Box(Modifier.fillMaxWidth().height(height.dp)) { content() }
        if (legend.isNotEmpty()) {
            Row(
                Modifier.fillMaxWidth().padding(top = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                legend.forEach { (label, color) -> LegendDot(color, label) }
            }
        }
    }
}

@Composable
fun LegendDot(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(9.dp).background(color, CircleShape))
        Spacer(Modifier.width(5.dp))
        Text(label, style = MaterialTheme.typography.labelSmall)
    }
}

// ---------------------------------------------------------------------------
// Chiziqli grafik (ko'p seriya + ishonch oralig'i)
// ---------------------------------------------------------------------------
@Composable
fun LineChart(
    labels: List<String>,
    series: List<LineSeries>,
    band: ConfidenceBand? = null,
    height: Int = 220,
    valueFormatter: (Double) -> String = { Fmt.dec(it, 1) },
) {
    val measurer = rememberTextMeasurer()
    val axisColor = MaterialTheme.colorScheme.onSurfaceVariant
    val gridColor = MaterialTheme.colorScheme.surfaceVariant
    val resolved = series.mapIndexed { index, item ->
        item.copy(color = item.color ?: ChartPalette[index % ChartPalette.size])
    }
    val allValues = resolved.flatMap { it.values }.filterNotNull() +
        (band?.lower?.filterNotNull() ?: emptyList()) + (band?.upper?.filterNotNull() ?: emptyList())

    if (allValues.isEmpty()) {
        EmptyChart("Ma'lumot yo'q", height)
        return
    }

    ChartFrame(height, resolved.map { it.name to (it.color ?: ChartPalette[0]) }) {
        Canvas(Modifier.fillMaxSize().clipToBounds()) {
            val pointCount = maxOf(labels.size, resolved.maxOfOrNull { it.values.size } ?: 0)
            val scale = AxisScale(allValues, size, measurer, axisColor, gridColor, labels, pointCount)
            scale.drawGrid(this, valueFormatter)
            scale.drawXLabels(this, labels)

            band?.let { confidence ->
                val bandColor = (confidence.color ?: resolved.lastOrNull()?.color ?: ChartPalette[1]).copy(alpha = 0.18f)
                val upperPoints = confidence.upper.mapIndexedNotNull { i, v -> v?.let { i to it } }
                val lowerPoints = confidence.lower.mapIndexedNotNull { i, v -> v?.let { i to it } }
                if (upperPoints.size >= 2 && lowerPoints.size >= 2) {
                    val path = Path()
                    upperPoints.forEachIndexed { index, (i, value) ->
                        val point = scale.point(i, value)
                        if (index == 0) path.moveTo(point.x, point.y) else path.lineTo(point.x, point.y)
                    }
                    lowerPoints.reversed().forEach { (i, value) ->
                        val point = scale.point(i, value)
                        path.lineTo(point.x, point.y)
                    }
                    path.close()
                    drawPath(path, bandColor)
                }
            }

            resolved.forEach { line ->
                val color = line.color ?: ChartPalette[0]
                val effect = if (line.dashed) PathEffect.dashPathEffect(floatArrayOf(12f, 8f)) else null
                var previous: Offset? = null
                line.values.forEachIndexed { index, value ->
                    if (value == null) { previous = null; return@forEachIndexed }
                    val point = scale.point(index, value)
                    previous?.let { start ->
                        drawLine(color, start, point, strokeWidth = 3.5f, pathEffect = effect)
                    }
                    if (line.values.size <= 40) drawCircle(color, radius = 3.5f, center = point)
                    previous = point
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Vertikal ustunli grafik
// ---------------------------------------------------------------------------
@Composable
fun BarChart(
    labels: List<String>,
    values: List<Double>,
    height: Int = 200,
    color: Color? = null,
    valueFormatter: (Double) -> String = { Fmt.dec(it, 1) },
) {
    val measurer = rememberTextMeasurer()
    val axisColor = MaterialTheme.colorScheme.onSurfaceVariant
    val gridColor = MaterialTheme.colorScheme.surfaceVariant
    val barColor = color ?: MaterialTheme.colorScheme.primary

    if (values.isEmpty() || values.all { it == 0.0 }) {
        EmptyChart("Ma'lumot yo'q", height)
        return
    }

    ChartFrame(height) {
        Canvas(Modifier.fillMaxSize().clipToBounds()) {
            val scale = AxisScale(values + 0.0, size, measurer, axisColor, gridColor, labels, labels.size)
            scale.drawGrid(this, valueFormatter)
            scale.drawXLabels(this, labels)
            val slot = scale.plotWidth / values.size.coerceAtLeast(1)
            val barWidth = (slot * 0.62f).coerceAtMost(46f)
            values.forEachIndexed { index, value ->
                val centerX = scale.left + slot * (index + 0.5f)
                val top = scale.yFor(value)
                val bottom = scale.yFor(0.0)
                drawRoundRect(
                    color = barColor,
                    topLeft = Offset(centerX - barWidth / 2, minOf(top, bottom)),
                    size = Size(barWidth, abs(bottom - top).coerceAtLeast(2f)),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(4f, 4f),
                )
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Gorizontal ustunli grafik (viloyatlar reytingi)
// ---------------------------------------------------------------------------
@Composable
fun HorizontalBarChart(
    labels: List<String>,
    values: List<Double>,
    color: Color? = null,
    valueFormatter: (Double) -> String = { Fmt.num(it, 0) },
) {
    if (values.isEmpty()) {
        EmptyChart("Ma'lumot yo'q", 120)
        return
    }
    val barColor = color ?: MaterialTheme.colorScheme.primary
    val maxValue = values.maxOf { abs(it) }.coerceAtLeast(1e-9)
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        labels.indices.forEach { index ->
            val value = values.getOrElse(index) { 0.0 }
            val fraction = (abs(value) / maxValue).toFloat().coerceIn(0.02f, 1f)
            Column {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(labels[index], style = MaterialTheme.typography.labelMedium, maxLines = 1)
                    Text(valueFormatter(value), style = MaterialTheme.typography.labelSmall)
                }
                Spacer(Modifier.height(3.dp))
                Box(
                    Modifier.fillMaxWidth().height(10.dp)
                        .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(5.dp)),
                ) {
                    Box(
                        Modifier.fillMaxWidth(fraction).fillMaxHeight()
                            .background(
                                if (value < 0) MetricLow else barColor,
                                RoundedCornerShape(5.dp),
                            ),
                    )
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Donut (ekinlar taqsimoti / sug'orish usullari)
// ---------------------------------------------------------------------------
@Composable
fun DonutChart(data: List<Pair<String, Double>>, height: Int = 170) {
    val positive = data.filter { it.second > 0 }
    if (positive.isEmpty()) {
        EmptyChart("Ma'lumot yo'q", height)
        return
    }
    val total = positive.sumOf { it.second }
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Canvas(Modifier.size(height.dp)) {
            val diameter = minOf(size.width, size.height) * 0.92f
            val topLeft = Offset((size.width - diameter) / 2, (size.height - diameter) / 2)
            var startAngle = -90f
            positive.forEachIndexed { index, (_, value) ->
                val sweep = (value / total * 360.0).toFloat()
                drawArc(
                    color = ChartPalette[index % ChartPalette.size],
                    startAngle = startAngle, sweepAngle = sweep, useCenter = false,
                    topLeft = topLeft, size = Size(diameter, diameter),
                    style = Stroke(width = diameter * 0.28f),
                )
                startAngle += sweep
            }
        }
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            positive.take(8).forEachIndexed { index, (label, value) ->
                LegendDot(
                    ChartPalette[index % ChartPalette.size],
                    "$label — ${Fmt.dec(value / total * 100, 0)}%",
                )
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Heatmap (hudud × ekin hosildorligi)
// ---------------------------------------------------------------------------
@Composable
fun HeatmapChart(
    rowLabels: List<String>,
    columnLabels: List<String>,
    values: List<List<Double?>>,
    cellHeight: Int = 26,
) {
    if (rowLabels.isEmpty() || columnLabels.isEmpty()) {
        EmptyChart("Ma'lumot yo'q", 120)
        return
    }
    val flat = values.flatten().filterNotNull()
    val min = flat.minOrNull() ?: 0.0
    val max = flat.maxOrNull() ?: 1.0
    val emptyCell = MaterialTheme.colorScheme.surfaceVariant

    Column(Modifier.fillMaxWidth()) {
        // Ustun sarlavhalari
        Row(Modifier.fillMaxWidth()) {
            Spacer(Modifier.width(86.dp))
            columnLabels.forEach { label ->
                Text(
                    label.take(6),
                    style = MaterialTheme.typography.labelSmall,
                    modifier = Modifier.weight(1f),
                    maxLines = 1,
                )
            }
        }
        Spacer(Modifier.height(3.dp))
        rowLabels.forEachIndexed { rowIndex, rowLabel ->
            Row(Modifier.fillMaxWidth().height(cellHeight.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(
                    rowLabel.take(12),
                    style = MaterialTheme.typography.labelSmall,
                    modifier = Modifier.width(86.dp),
                    maxLines = 1,
                )
                columnLabels.indices.forEach { columnIndex ->
                    val value = values.getOrNull(rowIndex)?.getOrNull(columnIndex)
                    Box(
                        Modifier.weight(1f).fillMaxHeight().padding(1.dp)
                            .background(
                                value?.let { metricColor(it, min, max) } ?: emptyCell,
                                RoundedCornerShape(3.dp),
                            ),
                        contentAlignment = Alignment.Center,
                    ) {
                        if (value != null) {
                            Text(
                                Fmt.dec(value, 1),
                                style = MaterialTheme.typography.labelSmall,
                                color = Color.White,
                                maxLines = 1,
                            )
                        }
                    }
                }
            }
        }
        Row(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            LegendDot(MetricLow, "past (${Fmt.dec(min, 1)})")
            LegendDot(MetricMid, "o'rta")
            LegendDot(MetricHigh, "yuqori (${Fmt.dec(max, 1)})")
        }
    }
}

// ---------------------------------------------------------------------------
// Scatter (korrelyatsiya)
// ---------------------------------------------------------------------------
@Composable
fun ScatterChart(
    points: List<Pair<Double, Double>>,
    xName: String,
    yName: String,
    height: Int = 220,
) {
    val measurer = rememberTextMeasurer()
    val axisColor = MaterialTheme.colorScheme.onSurfaceVariant
    val gridColor = MaterialTheme.colorScheme.surfaceVariant
    val pointColor = MaterialTheme.colorScheme.primary

    if (points.size < 2) {
        EmptyChart("Ma'lumot yetarli emas", height)
        return
    }

    ChartFrame(height) {
        Canvas(Modifier.fillMaxSize().clipToBounds()) {
            val ys = points.map { it.second }
            val xs = points.map { it.first }
            val scale = AxisScale(ys, size, measurer, axisColor, gridColor, emptyList(), points.size)
            scale.drawGrid(this) { Fmt.dec(it, 1) }

            val xMin = xs.min()
            val xMax = xs.max().let { if (it - xMin < 1e-9) xMin + 1 else it }
            points.forEach { (x, y) ->
                val px = scale.left + ((x - xMin) / (xMax - xMin)).toFloat() * scale.plotWidth
                drawCircle(pointColor.copy(alpha = 0.6f), radius = 4f, center = Offset(px, scale.yFor(y)))
            }
            // O'q nomlari
            drawText(
                measurer, xName,
                topLeft = Offset(size.width - 100f, size.height - 12f),
                style = LabelStyle.copy(color = axisColor),
            )
            drawText(
                measurer, yName,
                topLeft = Offset(2f, 0f),
                style = LabelStyle.copy(color = axisColor),
            )
        }
    }
}

// ---------------------------------------------------------------------------
// Gauge (kasallik xavfi)
// ---------------------------------------------------------------------------
@Composable
fun GaugeChart(value: Double, maxValue: Double = 100.0, unit: String = "%", size: Int = 160) {
    val trackColor = MaterialTheme.colorScheme.surfaceVariant
    val fraction = (value / maxValue).coerceIn(0.0, 1.0)
    val color = when {
        fraction > 0.66 -> MetricLow
        fraction > 0.33 -> MetricMid
        else -> MetricHigh
    }
    Box(Modifier.size(size.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize().clipToBounds()) {
            val stroke = this.size.minDimension * 0.13f
            val diameter = this.size.minDimension - stroke
            val topLeft = Offset(stroke / 2, stroke / 2)
            drawArc(
                color = trackColor, startAngle = 140f, sweepAngle = 260f, useCenter = false,
                topLeft = topLeft, size = Size(diameter, diameter), style = Stroke(width = stroke),
            )
            drawArc(
                color = color, startAngle = 140f, sweepAngle = (260 * fraction).toFloat(), useCenter = false,
                topLeft = topLeft, size = Size(diameter, diameter), style = Stroke(width = stroke),
            )
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("${Fmt.dec(value, 1)}$unit", style = MaterialTheme.typography.titleLarge)
        }
    }
}

// ---------------------------------------------------------------------------
// Yordamchi: o'q masshtabi va to'r
// ---------------------------------------------------------------------------
private class AxisScale(
    values: List<Double>,
    private val canvasSize: Size,
    private val measurer: TextMeasurer,
    private val axisColor: Color,
    private val gridColor: Color,
    xLabels: List<String>,
    /** X o'qidagi nuqtalar soni — chiziq/scatter koordinatasi shunga bo'linadi. */
    private val pointCount: Int = xLabels.size,
) {
    val left = 46f
    private val right = 8f
    private val top = 10f

    /**
     * Yorliq balandligi qurilma zichligiga bog'liq — qat'iy piksel qoldirilsa
     * yuqori DPI'da X o'qi yozuvlari kesilib qoladi. Shuning uchun haqiqiy
     * o'lchangan balandlik bo'yicha joy ajratiladi.
     */
    private val labelHeight: Float = measurer.measure("0", LabelStyle).size.height.toFloat()
    private val bottom = if (xLabels.isEmpty()) labelHeight * 0.5f else labelHeight + 6f

    private val min: Double
    private val max: Double

    init {
        val rawMin = values.minOrNull() ?: 0.0
        val rawMax = values.maxOrNull() ?: 1.0
        // 0 dan boshlansa ustunlar to'g'ri ko'rinadi; manfiy qiymat bo'lsa saqlanadi
        val lower = minOf(rawMin, 0.0)
        val upper = if (rawMax - lower < 1e-9) lower + 1.0 else rawMax
        val padding = (upper - lower) * 0.08
        min = lower
        max = upper + padding
    }

    val plotWidth: Float get() = canvasSize.width - left - right
    private val plotHeight: Float get() = canvasSize.height - top - bottom

    fun yFor(value: Double): Float =
        top + plotHeight - (((value - min) / (max - min)).toFloat() * plotHeight)

    /** index → ekran koordinatasi (0 va oxirgi nuqta plot chegaralariga tegadi). */
    fun point(index: Int, value: Double): Offset =
        Offset(left + plotWidth * index / max(1, pointCount - 1), yFor(value))

    fun drawGrid(scope: DrawScope, formatter: (Double) -> String) = with(scope) {
        val steps = 4
        for (i in 0..steps) {
            val value = min + (max - min) * i / steps
            val y = yFor(value)
            drawLine(gridColor, Offset(left, y), Offset(left + plotWidth, y), strokeWidth = 1f)
            drawText(
                measurer, formatter(value),
                topLeft = Offset(0f, y - labelHeight / 2f),
                style = LabelStyle.copy(color = axisColor),
            )
        }
    }

    fun drawXLabels(scope: DrawScope, labels: List<String>) = with(scope) {
        if (labels.isEmpty()) return@with
        val step = max(1, labels.size / 7)
        labels.forEachIndexed { index, label ->
            if (index % step != 0 || label.isBlank()) return@forEachIndexed
            val x = left + plotWidth * index / max(1, labels.size - 1)
            val laid = measurer.measure(label, LabelStyle)
            // Yorliq nuqta ustida markazlanadi va o'ng chekkadan chiqib ketmaydi
            val labelX = (x - laid.size.width / 2f)
                .coerceIn(0f, (canvasSize.width - laid.size.width).coerceAtLeast(0f))
            drawText(
                measurer, label,
                topLeft = Offset(labelX, canvasSize.height - labelHeight - 1f),
                style = LabelStyle.copy(color = axisColor),
            )
        }
    }
}

@Composable
fun EmptyChart(message: String, height: Int = 160) {
    Box(
        Modifier.fillMaxWidth().height(height.dp)
            .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(10.dp)),
        contentAlignment = Alignment.Center,
    ) {
        Text(message, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

/** Qiymatni past→yuqori shkalada rangga aylantirish (heatmap va xarita uchun). */
fun metricColor(value: Double, min: Double, max: Double): Color {
    if (max - min < 1e-9) return MetricHigh
    val t = ((value - min) / (max - min)).coerceIn(0.0, 1.0).toFloat()
    return if (t < 0.5f) {
        lerpColor(MetricLow, MetricMid, t * 2)
    } else {
        lerpColor(MetricMid, MetricHigh, (t - 0.5f) * 2)
    }
}

private fun lerpColor(from: Color, to: Color, t: Float): Color = Color(
    red = from.red + (to.red - from.red) * t,
    green = from.green + (to.green - from.green) * t,
    blue = from.blue + (to.blue - from.blue) * t,
    alpha = 1f,
)
