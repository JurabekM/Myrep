package com.agrovision.app.ui.chart

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import com.agrovision.app.data.repo.TileKey
import com.agrovision.app.data.repo.TileRepository
import com.agrovision.app.data.repo.TileSource
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.pow

/** Xaritada chiziladigan dala konturi. */
data class TileOverlay(
    val label: String,
    /** (lon, lat) juftliklari. */
    val polygon: List<Pair<Double, Double>>,
    val color: Color,
)

/**
 * Internetdan yuklanadigan raster xarita (Web Mercator XYZ plitkalari).
 *
 * Sun'iy yo'ldosh tasviri yoki oddiy ko'cha xaritasi ustiga dala konturlari
 * chiziladi. Surish va masshtablash barmoq bilan ham, +/− tugmalari bilan ham
 * ishlaydi. Tarmoq bo'lmasa yuklanmagan plitkalar o'rniga bo'sh fon qoladi va
 * konturlar baribir ko'rinadi — ilova yiqilmaydi.
 */
@Composable
fun TileMap(
    centerLat: Double,
    centerLon: Double,
    source: TileSource,
    repository: TileRepository,
    modifier: Modifier = Modifier,
    heightDp: Int = 340,
    initialZoom: Int = 13,
    overlays: List<TileOverlay> = emptyList(),
    onStatus: (String) -> Unit = {},
) {
    val outline = MaterialTheme.colorScheme.onSurfaceVariant
    val surfaceColor = MaterialTheme.colorScheme.surfaceVariant

    var zoom by remember(centerLat, centerLon) { mutableIntStateOf(initialZoom) }
    var pan by remember(centerLat, centerLon) { mutableStateOf(Offset.Zero) }
    var canvasSize by remember { mutableStateOf(Size.Zero) }
    // Yangi plitka yuklanganda qayta chizishni majburlash uchun hisoblagich
    var tick by remember { mutableIntStateOf(0) }
    var pending by remember { mutableStateOf<Set<TileKey>>(emptySet()) }

    val maxZoom = source.maxZoom

    // Ko'rinadigan plitkalarni aniqlab, yetishmayotganini yuklaydi.
    LaunchedEffect(zoom, pan, canvasSize, source, centerLat, centerLon) {
        if (canvasSize.width <= 0f) return@LaunchedEffect
        val keys = visibleTiles(centerLat, centerLon, zoom, pan, canvasSize)
        val missing = keys.filter { repository.cached(it, source) == null }
        if (missing.isEmpty()) {
            onStatus("")
            return@LaunchedEffect
        }
        pending = missing.toSet()
        onStatus("Xarita yuklanmoqda… (${missing.size} plitka)")
        var loaded = 0
        missing.forEach { key ->
            if (repository.load(key, source) != null) loaded++
            tick++
        }
        pending = emptySet()
        onStatus(
            if (loaded == 0) "Xarita plitkalarini yuklab bo'lmadi — internetni tekshiring."
            else "",
        )
        repository.trimCache()
    }

    Column(modifier.fillMaxWidth()) {
        Box(
            Modifier
                .fillMaxWidth()
                .height(heightDp.dp)
                .background(surfaceColor, RoundedCornerShape(12.dp))
                .clipToBounds()
                .pointerInput(source) {
                    // MUHIM: xarita faqat IKKI barmoq bilan suriladi/masshtablanadi.
                    // Bir barmoqli surish iste'mol qilinmaydi — shunda foydalanuvchi
                    // xarita ustida ham sahifani aylantira oladi.
                    awaitEachGesture {
                        awaitFirstDown(requireUnconsumed = false)
                        do {
                            val event = awaitPointerEvent()
                            if (event.changes.size >= 2) {
                                val zoomChange = event.calculateZoom()
                                val panChange = event.calculatePan()
                                if (zoomChange != 1f || panChange != Offset.Zero) {
                                    pan += panChange
                                    if (zoomChange > 1.25f && zoom < maxZoom) {
                                        zoom++; pan *= 2f
                                    } else if (zoomChange < 0.8f && zoom > 3) {
                                        zoom--; pan /= 2f
                                    }
                                    event.changes.forEach { it.consume() }
                                }
                            }
                        } while (event.changes.any { it.pressed })
                    }
                },
        ) {
            Canvas(Modifier.fillMaxSize()) {
                canvasSize = size
                @Suppress("UNUSED_EXPRESSION") tick   // qayta chizishga bog'lanish

                val originX = TileRepository.lonToPixelX(centerLon, zoom) - size.width / 2 - pan.x
                val originY = TileRepository.latToPixelY(centerLat, zoom) - size.height / 2 - pan.y

                visibleTiles(centerLat, centerLon, zoom, pan, size).forEach { key ->
                    val bitmap = repository.cached(key, source) ?: return@forEach
                    val left = (key.x * TileRepository.TILE_SIZE - originX).toFloat()
                    val top = (key.y * TileRepository.TILE_SIZE - originY).toFloat()
                    drawImage(
                        image = bitmap.asImageBitmap(),
                        dstOffset = IntOffset(left.toInt(), top.toInt()),
                        dstSize = IntSize(TileRepository.TILE_SIZE, TileRepository.TILE_SIZE),
                    )
                }

                // Dala konturlari plitkalar ustida
                overlays.forEach { overlay ->
                    val points = overlay.polygon.map { (lon, lat) ->
                        Offset(
                            (TileRepository.lonToPixelX(lon, zoom) - originX).toFloat(),
                            (TileRepository.latToPixelY(lat, zoom) - originY).toFloat(),
                        )
                    }
                    if (points.size < 3) return@forEach
                    val path = Path().apply {
                        moveTo(points[0].x, points[0].y)
                        points.drop(1).forEach { lineTo(it.x, it.y) }
                        close()
                    }
                    drawPath(path, overlay.color.copy(alpha = 0.25f))
                    drawPath(path, overlay.color, style = Stroke(width = 3f))
                }
            }

            Column(
                Modifier.align(Alignment.TopEnd).padding(6.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                TileButton("+") { if (zoom < maxZoom) { zoom++; pan *= 2f } }
                TileButton("−") { if (zoom > 3) { zoom--; pan /= 2f } }
                TileButton("⟳") { pan = Offset.Zero; zoom = initialZoom }
                Text("z$zoom", style = MaterialTheme.typography.labelSmall, color = Color.White)
            }

            Text(
                source.attribution,
                style = MaterialTheme.typography.labelSmall,
                color = Color.White.copy(alpha = 0.85f),
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .background(Color.Black.copy(alpha = 0.35f), RoundedCornerShape(4.dp))
                    .padding(horizontal = 5.dp, vertical = 2.dp),
            )
        }
    }
}

@Composable
private fun TileButton(label: String, onClick: () -> Unit) {
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

/** Ekranda ko'rinadigan plitkalar ro'yxati (chekkalarda bittadan zaxira bilan). */
private fun visibleTiles(
    centerLat: Double,
    centerLon: Double,
    zoom: Int,
    pan: Offset,
    size: Size,
): List<TileKey> {
    if (size.width <= 0f || size.height <= 0f) return emptyList()
    val originX = TileRepository.lonToPixelX(centerLon, zoom) - size.width / 2 - pan.x
    val originY = TileRepository.latToPixelY(centerLat, zoom) - size.height / 2 - pan.y
    val tileCount = 2.0.pow(zoom).toInt()

    val x0 = floor(originX / TileRepository.TILE_SIZE).toInt()
    val x1 = ceil((originX + size.width) / TileRepository.TILE_SIZE).toInt()
    val y0 = floor(originY / TileRepository.TILE_SIZE).toInt()
    val y1 = ceil((originY + size.height) / TileRepository.TILE_SIZE).toInt()

    val keys = mutableListOf<TileKey>()
    for (x in x0..x1) {
        for (y in y0..y1) {
            if (x < 0 || y < 0 || x >= tileCount || y >= tileCount) continue
            keys += TileKey(zoom, x, y)
        }
    }
    return keys
}
