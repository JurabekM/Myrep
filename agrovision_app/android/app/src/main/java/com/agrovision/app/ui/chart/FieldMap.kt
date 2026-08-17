package com.agrovision.app.ui.chart

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agrovision.app.core.Fmt
import com.agrovision.app.data.local.MapFieldRow
import com.agrovision.app.data.repo.GeoRepository
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.cos
import kotlin.math.PI
import com.agrovision.app.data.local.GeoAssets
import androidx.compose.ui.platform.LocalContext
import androidx.compose.material3.Surface

/**
 * Interaktiv native xarita — dala poligonlari, viloyat markazlari, issiqlik
 * qatlami va klasterlar Compose `Canvas` bilan chiziladi. Barmoq bilan
 * surish (pan), ikki barmoq bilan masshtablash (zoom) va poligonga bosib
 * ma'lumot ko'rish ishlaydi. WebView yoki tashqi xarita SDK ishlatilmaydi —
 * shu sababli internet talab qilinmaydi.
 */

enum class MapMetric(val title: String) {
    YIELD("Hosildorlik (t/ga)"),
    NDVI("NDVI indeksi"),
    AREA("Maydon (ga)"),
}

enum class MapLayer(val title: String) {
    POLYGONS("Poligonlar"),
    HEATMAP("Issiqlik xaritasi"),
    CLUSTERS("Klasterlar"),
}

data class MapRegionMarker(val name: String, val lat: Double, val lon: Double, val value: Double)

@Composable
fun FieldMap(
    fields: List<MapFieldRow>,
    regions: List<MapRegionMarker>,
    metric: MapMetric,
    layer: MapLayer,
    modifier: Modifier = Modifier,
    /** Tanlangan viloyat nomi — dala bo'lmasa ham shu hududga yaqinlashtiriladi. */
    focusRegion: String? = null,
    onFieldSelected: (MapFieldRow?) -> Unit = {},
) {
    val context = LocalContext.current
    val measurer = rememberTextMeasurer()
    val surfaceColor = MaterialTheme.colorScheme.surfaceVariant
    val outline = MaterialTheme.colorScheme.onSurfaceVariant
    val labelColor = MaterialTheme.colorScheme.onSurface
    val landColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.10f)
    val landFocus = MaterialTheme.colorScheme.primary.copy(alpha = 0.22f)
    val borderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.55f)

    // O'zbekiston ma'muriy chegaralari (assets, geoBoundaries ADM1) — bir marta
    // o'qiladi va dala bo'lmasa ham har doim chiziladi.
    val shapes = remember { GeoAssets.regions(context) }

    var scale by remember { mutableFloatStateOf(1f) }
    var pan by remember { mutableStateOf(Offset.Zero) }
    var canvasSize by remember { mutableStateOf(Size.Zero) }
    var selected by remember { mutableStateOf<MapFieldRow?>(null) }

    // Ko'rinadigan hudud: dalalar > tanlangan viloyat konturi > butun mamlakat.
    val bounds = remember(fields, focusRegion, shapes) {
        computeBounds(fields, focusRegion, shapes)
    }
    // Filtr yoki ma'lumot o'zgarsa masshtab/siljish nolga qaytadi, aks holda
    // avvalgi zoom yangi hududda noto'g'ri joyni ko'rsatadi.
    LaunchedEffect(bounds) {
        scale = 1f
        pan = Offset.Zero
    }

    val values = remember(fields, metric) { fields.map { metricValue(it, metric) } }
    val minValue = values.minOrNull() ?: 0.0
    val maxValue = values.maxOrNull() ?: 1.0

    Column(modifier.fillMaxWidth()) {
        Box(
            Modifier
                .fillMaxWidth()
                .height(340.dp)
                .background(surfaceColor, RoundedCornerShape(12.dp))
                // MUHIM: Compose Canvas standart holda o'z chegarasidan tashqariga
                // chizishni kesmaydi — masshtablanganda yoki chegaradan tashqaridagi
                // markerlar butun ekranga "oqib" ketadi. clipToBounds buni to'xtatadi.
                .clipToBounds()
                .pointerInput(Unit) {
                    // MUHIM: xarita faqat IKKI barmoq bilan suriladi/masshtablanadi.
                    // Bir barmoqli surish hodisasi iste'mol qilinmaydi — shunda
                    // foydalanuvchi xarita ustida ham sahifani aylantira oladi.
                    awaitEachGesture {
                        awaitFirstDown(requireUnconsumed = false)
                        do {
                            val event = awaitPointerEvent()
                            if (event.changes.size >= 2) {
                                val zoomChange = event.calculateZoom()
                                val panChange = event.calculatePan()
                                if (zoomChange != 1f || panChange != Offset.Zero) {
                                    scale = (scale * zoomChange).coerceIn(0.6f, 16f)
                                    pan += panChange
                                    event.changes.forEach { it.consume() }
                                }
                            }
                        } while (event.changes.any { it.pressed })
                    }
                }
                .pointerInput(fields, metric, bounds) {
                    detectTapGestures { tap ->
                        val hit = fields.firstOrNull { field ->
                            val points = GeoRepository.parsePolygon(field.polygon)
                                .map { (lon, lat) -> project(lon, lat, bounds, canvasSize, scale, pan) }
                            points.size >= 3 && pointInPolygon(tap, points)
                        }
                        selected = hit
                        onFieldSelected(hit)
                    }
                },
        ) {
            Canvas(Modifier.fillMaxSize().padding(4.dp)) {
                canvasSize = size

                // --- Asos qatlam: O'zbekiston viloyatlari konturi ---
                shapes.forEach { shape ->
                    val focused = focusRegion != null && shape.name == focusRegion
                    shape.rings.forEach { ring ->
                        if (ring.size < 3) return@forEach
                        val points = ring.map { (lon, lat) ->
                            project(lon, lat, bounds, size, scale, pan)
                        }
                        val path = Path().apply {
                            moveTo(points[0].x, points[0].y)
                            points.drop(1).forEach { lineTo(it.x, it.y) }
                            close()
                        }
                        drawPath(path, if (focused) landFocus else landColor)
                        drawPath(
                            path, borderColor,
                            style = Stroke(width = if (focused) 2.6f else 1.4f),
                        )
                    }
                }

                when (layer) {
                    MapLayer.HEATMAP -> {
                        fields.forEach { field ->
                            val center = project(field.lon, field.lat, bounds, size, scale, pan)
                            val value = metricValue(field, metric)
                            val intensity = normalize(value, minValue, maxValue)
                            val radius = (26f + 34f * intensity).toFloat() * min(scale, 3f)
                            drawCircle(
                                color = metricColor(value, minValue, maxValue).copy(alpha = 0.28f),
                                radius = radius, center = center,
                            )
                        }
                    }
                    MapLayer.CLUSTERS -> {
                        // Xo'jalik bo'yicha klasterlash: bir xo'jalikning dalalari bitta belgi
                        fields.groupBy { it.farm }.forEach { (farm, group) ->
                            val center = project(
                                group.map { it.lon }.average(), group.map { it.lat }.average(),
                                bounds, size, scale, pan,
                            )
                            val avg = group.map { metricValue(it, metric) }.average()
                            val radius = (14f + 3f * group.size).coerceAtMost(34f)
                            drawCircle(metricColor(avg, minValue, maxValue).copy(alpha = 0.85f), radius, center)
                            drawText(
                                measurer, group.size.toString(),
                                topLeft = Offset(center.x - 5f, center.y - 8f),
                                style = TextStyle(fontSize = 10.sp, color = Color.White),
                            )
                        }
                    }
                    MapLayer.POLYGONS -> {
                        fields.forEach { field ->
                            val points = GeoRepository.parsePolygon(field.polygon)
                                .map { (lon, lat) -> project(lon, lat, bounds, size, scale, pan) }
                            val value = metricValue(field, metric)
                            val color = metricColor(value, minValue, maxValue)
                            if (points.size >= 3) {
                                val path = Path().apply {
                                    moveTo(points[0].x, points[0].y)
                                    points.drop(1).forEach { lineTo(it.x, it.y) }
                                    close()
                                }
                                drawPath(path, color.copy(alpha = 0.55f))
                                drawPath(
                                    path,
                                    if (field.id == selected?.id) labelColor else color,
                                    style = Stroke(width = if (field.id == selected?.id) 3.5f else 1.5f),
                                )
                            } else {
                                // Poligon bo'lmasa markaz nuqtasi
                                val center = project(field.lon, field.lat, bounds, size, scale, pan)
                                drawCircle(color, radius = 6f, center = center)
                            }
                        }
                    }
                }

                // --- Viloyat nomlari (konturlar markazida) ---
                shapes.forEach { shape ->
                    val center = project(shape.lon, shape.lat, bounds, size, scale, pan)
                    if (center.x < 4 || center.x > size.width - 34 ||
                        center.y < 12 || center.y > size.height - 8
                    ) {
                        return@forEach
                    }
                    val focused = focusRegion != null && shape.name == focusRegion
                    drawText(
                        measurer, shape.name,
                        topLeft = Offset(center.x - 12f, center.y - 6f),
                        style = TextStyle(
                            fontSize = if (focused) 11.sp else 9.sp,
                            color = if (focused) labelColor else outline,
                        ),
                    )
                }
            }

            // Masshtab boshqaruvi
            Column(
                Modifier.align(Alignment.TopEnd).padding(6.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                MapButton("+") { scale = (scale * 1.6f).coerceAtMost(16f) }
                MapButton("−") { scale = (scale / 1.6f).coerceAtLeast(0.6f) }
                MapButton("⟳") { scale = 1f; pan = Offset.Zero }
                Text(
                    "×${Fmt.dec(scale.toDouble(), 1)}",
                    style = MaterialTheme.typography.labelSmall,
                    color = outline,
                )
            }

            Text(
                "Ikki barmoq bilan surish/masshtab · +/− tugmalari · poligonga bosish",
                style = MaterialTheme.typography.labelSmall,
                color = outline,
                modifier = Modifier.align(Alignment.BottomStart).padding(8.dp),
            )
        }

        // Rang shkalasi
        Row(
            Modifier.fillMaxWidth().padding(top = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            LegendDot(com.agrovision.app.ui.theme.MetricLow, "past ${Fmt.dec(minValue, 1)}")
            LegendDot(com.agrovision.app.ui.theme.MetricMid, "o'rta")
            LegendDot(com.agrovision.app.ui.theme.MetricHigh, "yuqori ${Fmt.dec(maxValue, 1)}")
        }
    }
}

@Composable
private fun MapButton(label: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f),
        tonalElevation = 2.dp,
        modifier = Modifier.size(34.dp),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(label, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface)
        }
    }
}

// ---------------------------------------------------------------------------
private data class GeoBounds(val minLon: Double, val maxLon: Double, val minLat: Double, val maxLat: Double)

/** O'zbekiston chegaralari — dalalar bo'lmaganda standart ko'rinish. */
private val UZBEKISTAN = GeoBounds(55.9, 73.2, 37.1, 45.6)

private fun boundsOf(points: List<Pair<Double, Double>>, padRatio: Double): GeoBounds? {
    if (points.isEmpty()) return null
    val lons = points.map { it.first }
    val lats = points.map { it.second }
    val padLon = ((lons.max() - lons.min()) * padRatio).coerceAtLeast(0.05)
    val padLat = ((lats.max() - lats.min()) * padRatio).coerceAtLeast(0.05)
    return GeoBounds(lons.min() - padLon, lons.max() + padLon, lats.min() - padLat, lats.max() + padLat)
}

private fun computeBounds(
    fields: List<MapFieldRow>,
    focusRegion: String?,
    shapes: List<GeoAssets.RegionShape>,
): GeoBounds {
    // 1) Dalalar bor — o'shalarga yaqinlashamiz.
    boundsOf(fields.map { it.lon to it.lat }, 0.14)?.let { return it }
    // 2) Dala yo'q, lekin viloyat tanlangan — o'sha viloyat konturiga.
    if (focusRegion != null) {
        val shape = shapes.firstOrNull { it.name == focusRegion }
        boundsOf(shape?.rings?.flatten().orEmpty(), 0.05)?.let { return it }
    }
    // 3) Butun O'zbekiston.
    return boundsOf(shapes.flatMap { it.rings.flatten() }, 0.02) ?: UZBEKISTAN
}

/**
 * Geografik koordinatani ekran koordinatasiga aylantirish.
 *
 * Kenglik bo'yicha `cos(lat)` tuzatishi qo'llanadi va bir xil masshtab
 * koeffitsienti ishlatiladi — shunda O'zbekiston konturi cho'zilmaydi va
 * xarita haqiqiy shaklda ko'rinadi.
 */
private fun project(
    lon: Double,
    lat: Double,
    bounds: GeoBounds,
    size: Size,
    scale: Float,
    pan: Offset,
): Offset {
    if (size.width <= 0f || size.height <= 0f) return Offset.Zero
    val midLat = (bounds.minLat + bounds.maxLat) / 2
    val midLon = (bounds.minLon + bounds.maxLon) / 2
    val kx = cos(midLat * PI / 180.0)
    val spanX = (bounds.maxLon - bounds.minLon) * kx
    val spanY = bounds.maxLat - bounds.minLat
    if (spanX <= 0 || spanY <= 0) return Offset.Zero
    val fit = min(size.width / spanX, size.height / spanY).toFloat()
    return Offset(
        x = size.width / 2 + ((lon - midLon) * kx * fit).toFloat() * scale + pan.x,
        y = size.height / 2 - ((lat - midLat) * fit).toFloat() * scale + pan.y,
    )
}

private fun metricValue(field: MapFieldRow, metric: MapMetric): Double = when (metric) {
    MapMetric.YIELD -> field.yieldTHa
    MapMetric.NDVI -> field.ndvi
    MapMetric.AREA -> field.areaHa
}

private fun normalize(value: Double, min: Double, max: Double): Double =
    if (max - min < 1e-9) 0.5 else ((value - min) / (max - min)).coerceIn(0.0, 1.0)

/** Ray-casting algoritmi: nuqta poligon ichidami. */
private fun pointInPolygon(point: Offset, polygon: List<Offset>): Boolean {
    var inside = false
    var j = polygon.size - 1
    for (i in polygon.indices) {
        val a = polygon[i]
        val b = polygon[j]
        if ((a.y > point.y) != (b.y > point.y) &&
            point.x < (b.x - a.x) * (point.y - a.y) / (b.y - a.y + 1e-9f) + a.x
        ) {
            inside = !inside
        }
        j = i
    }
    // Dala poligonlari ekranda bir necha piksel bo'lishi mumkin — barmoq bilan
    // bosish uchun poligon markazi atrofida kamida 44px (Material tegish zonasi)
    // tolerantlik beriladi.
    if (!inside) {
        val cx = polygon.map { it.x }.average().toFloat()
        val cy = polygon.map { it.y }.average().toFloat()
        val radius = max(
            polygon.maxOf { abs(it.x - cx) },
            polygon.maxOf { abs(it.y - cy) },
        ).coerceAtLeast(44f)
        return abs(point.x - cx) <= radius && abs(point.y - cy) <= radius
    }
    return true
}
