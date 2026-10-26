package uz.sectorverify.feature.survey.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.sp
import kotlin.math.max
import kotlin.math.min
import uz.sectorverify.analysis.Geo
import uz.sectorverify.feature.survey.R
import uz.sectorverify.feature.survey.TrackPoint
import uz.sectorverify.model.SitePlan
import uz.sectorverify.ui.components.pciColor
import uz.sectorverify.ui.components.polarPoint
import uz.sectorverify.ui.theme.LocalSvPalette

/**
 * ADR-005: no base map. Site, 150/400 m rings, the track coloured by serving PCI, a north arrow and a scale bar
 * on a local azimuthal projection around the site.
 */
@Composable
fun MapCanvas(plan: SitePlan, track: List<TrackPoint>, modifier: Modifier = Modifier) {
    val p = LocalSvPalette.current
    val measurer = rememberTextMeasurer()
    val description = stringResource(R.string.live_map_description, track.size)
    val polar = track.map { Geo.distanceM(plan.lat, plan.lon, it.lat, it.lon) to Geo.bearingDeg(plan.lat, plan.lon, it.lat, it.lon) }
    val extentM = max(OUTER_RING_M, polar.maxOfOrNull { it.first } ?: 0.0) * 1.1
    Canvas(modifier.fillMaxWidth().aspectRatio(1f).semantics { contentDescription = description }) {
        val c = center
        val pxPerM = (min(size.width, size.height) / 2f / extentM).toFloat()
        for (ring in listOf(INNER_RING_M, OUTER_RING_M)) drawCircle(p.line, (ring * pxPerM).toFloat(), c, style = Stroke(2f))
        polar.zipWithNext().forEachIndexed { i, (a, b) ->
            val color = track[i + 1].servingPci?.let { p.pciColor(it) } ?: p.inkMuted
            drawLine(
                color,
                polarPoint(c, (a.first * pxPerM).toFloat(), a.second),
                polarPoint(c, (b.first * pxPerM).toFloat(), b.second),
                6f,
            )
        }
        polar.lastOrNull()?.let { (d, b) -> drawCircle(p.ink, 10f, polarPoint(c, (d * pxPerM).toFloat(), b)) }
        drawCircle(p.accent, 14f, c)
        // North arrow (top-right corner).
        val n = Offset(size.width - 40f, 70f)
        drawPath(
            Path().apply {
                moveTo(n.x, n.y - 40f)
                lineTo(n.x - 14f, n.y)
                lineTo(n.x + 14f, n.y)
                close()
            },
            p.ink,
        )
        drawText(measurer.measure("N", TextStyle(color = p.ink, fontSize = 14.sp)), topLeft = Offset(n.x - 6f, n.y + 4f))
        // Scale bar: 100 m.
        val bar = (SCALE_M * pxPerM).toFloat()
        val y = size.height - 30f
        drawLine(p.ink, Offset(30f, y), Offset(30f + bar, y), 4f)
        drawText(measurer.measure("${SCALE_M.toInt()} m", TextStyle(color = p.ink, fontSize = 12.sp)), topLeft = Offset(30f, y - 34f))
    }
}

private const val INNER_RING_M = 150.0
private const val OUTER_RING_M = 400.0
private const val SCALE_M = 100.0
