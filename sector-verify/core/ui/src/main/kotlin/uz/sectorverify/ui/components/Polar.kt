package uz.sectorverify.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.sp
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin
import uz.sectorverify.ui.R
import uz.sectorverify.ui.theme.LocalSvPalette

/** Polar diagrammadagi bitta sektor: reja (punktir) va 95 % yoyi bilan o'lchov. Burchaklar — kompas gradusida. */
data class PolarItem(
    val label: String,
    val planDeg: Double?,
    val estDeg: Double? = null,
    val ciLowDeg: Double? = null,
    val ciHighDeg: Double? = null,
    val color: Color,
)

/** Kompas azimuti → canvas burchagi (0° = shimol/yuqori, soat yo'nalishi bo'yicha). */
fun polarPoint(center: Offset, radius: Float, bearingDeg: Double): Offset {
    val r = Math.toRadians(bearingDeg)
    return Offset(center.x + radius * sin(r).toFloat(), center.y - radius * cos(r).toFloat())
}

@Composable
fun PolarDiagram(items: List<PolarItem>, modifier: Modifier = Modifier) {
    val p = LocalSvPalette.current
    val measurer = rememberTextMeasurer()
    val north = stringResource(R.string.common_north).take(1)
    val description = stringResource(
        R.string.polar_description,
        items.joinToString { "${it.label}: ${it.planDeg?.toInt() ?: "—"}° / ${it.estDeg?.toInt() ?: "—"}°" },
    )
    Canvas(modifier.fillMaxWidth().aspectRatio(1f).semantics { contentDescription = description }) {
        val c = center
        val r = min(size.width, size.height) / 2f * 0.82f
        drawGrid(c, r, p.line, p.inkMuted, measurer, north)
        for (it in items) {
            it.planDeg?.let { a ->
                drawLine(it.color, c, polarPoint(c, r, a), strokeWidth = 4f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(18f, 12f)))
            }
            val est = it.estDeg ?: continue
            val lo = it.ciLowDeg
            val hi = it.ciHighDeg
            if (lo != null && hi != null) {
                val sweep = ((hi - lo) % 360 + 360) % 360
                drawArc(
                    color = it.color.copy(alpha = 0.35f),
                    startAngle = (lo - 90).toFloat(),
                    sweepAngle = sweep.toFloat(),
                    useCenter = true,
                    topLeft = Offset(c.x - r * 0.9f, c.y - r * 0.9f),
                    size = Size(r * 1.8f, r * 1.8f),
                )
            }
            drawLine(it.color, c, polarPoint(c, r * 0.95f, est), strokeWidth = 8f, cap = StrokeCap.Round)
            drawLabel(measurer, it.label, polarPoint(c, r * 1.1f, est), it.color)
        }
    }
}

internal fun DrawScope.drawGrid(c: Offset, r: Float, line: Color, text: Color, measurer: TextMeasurer, north: String) {
    for (f in listOf(1f, 0.66f, 0.33f)) drawCircle(line, radius = r * f, center = c, style = Stroke(2f))
    for (deg in 0 until 360 step 30) drawLine(line, c, polarPoint(c, r, deg.toDouble()), strokeWidth = 1f)
    drawLabel(measurer, north, polarPoint(c, r * 1.1f, 0.0), text)
}

internal fun DrawScope.drawLabel(measurer: TextMeasurer, s: String, at: Offset, color: Color) {
    val layout = measurer.measure(s, TextStyle(color = color, fontSize = 13.sp))
    drawText(layout, topLeft = Offset(at.x - layout.size.width / 2f, at.y - layout.size.height / 2f))
}

/** 36 bin'li qamrov radari (§8.1, 4-ekran): qoplangan bin'lar to'ldiriladi, yetishmaganlari warn rangida chiziladi. */
@Composable
fun CoverageRadar(covered: List<Boolean>, modifier: Modifier = Modifier) {
    val p = LocalSvPalette.current
    val measurer = rememberTextMeasurer()
    val north = stringResource(R.string.common_north).take(1)
    val pct = if (covered.isEmpty()) 0 else covered.count { it } * 100 / covered.size
    val missing = covered.indices.filterNot { covered[it] }.joinToString { "${it * 10}°" }
    val description = stringResource(R.string.radar_description, pct, missing.ifEmpty { "—" })
    Canvas(modifier.fillMaxWidth().aspectRatio(1f).semantics { contentDescription = description }) {
        val c = center
        val r = min(size.width, size.height) / 2f * 0.82f
        val n = covered.size.coerceAtLeast(1)
        val step = 360f / n
        covered.forEachIndexed { i, ok ->
            drawArc(
                color = if (ok) p.ok else p.warn.copy(alpha = 0.35f),
                startAngle = i * step - 90f + 1f,
                sweepAngle = step - 2f,
                useCenter = false,
                topLeft = Offset(c.x - r * 0.85f, c.y - r * 0.85f),
                size = Size(r * 1.7f, r * 1.7f),
                style = Stroke(width = r * 0.25f),
            )
        }
        drawLabel(measurer, north, polarPoint(c, r * 1.1f, 0.0), p.inkMuted)
        drawLabel(measurer, "$pct%", c, p.ink)
    }
}
