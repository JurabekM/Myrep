package com.agrovision.app.data.repo

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.LruCache
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.PI
import kotlin.math.atan
import kotlin.math.ln
import kotlin.math.sinh
import kotlin.math.tan

/** Bitta xarita plitkasi (Web Mercator, XYZ sxemasi). */
data class TileKey(val zoom: Int, val x: Int, val y: Int)

enum class TileSource(val title: String, val attribution: String, val maxZoom: Int) {
    SATELLITE("Sun'iy yo'ldosh", "Esri, Maxar, Earthstar Geographics", 18),
    STREETS("Oddiy xarita", "© OpenStreetMap hissadorlari", 18),
    ;

    fun url(key: TileKey): String = when (this) {
        SATELLITE ->
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/" +
                "${key.zoom}/${key.y}/${key.x}"
        STREETS ->
            "https://tile.openstreetmap.org/${key.zoom}/${key.x}/${key.y}.png"
    }
}

/**
 * Onlayn raster xarita plitkalarini yuklab beruvchi qatlam.
 *
 * Plitkalar ikki bosqichda saqlanadi: xotirada (LRU, tez qayta chizish uchun)
 * va diskda (`cacheDir/tiles`). Shu sababli bir marta ko'rilgan hudud
 * keyinchalik internetsiz ham ochiladi. Tarmoq bo'lmasa `null` qaytadi —
 * chaqiruvchi ekran o'rniga offlayn vektor konturni ko'rsatadi.
 */
@Singleton
class TileRepository @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(12, TimeUnit.SECONDS)
        .build()

    /** ~64 MB emas — plitkalar 256×256, taxminan 60 ta plitka xotirada yetarli. */
    private val memory = object : LruCache<String, Bitmap>(64) {
        override fun sizeOf(key: String, value: Bitmap) = 1
    }

    private val diskDir: File
        get() = File(context.cacheDir, "tiles").apply { mkdirs() }

    fun cached(key: TileKey, source: TileSource): Bitmap? = memory.get(id(key, source))

    /**
     * Plitkani xotira → disk → tarmoq tartibida oladi.
     * Xatolik (tarmoq yo'q, 404, timeout) `null` bilan qaytadi va yiqilmaydi.
     */
    suspend fun load(key: TileKey, source: TileSource): Bitmap? = withContext(Dispatchers.IO) {
        val id = id(key, source)
        memory.get(id)?.let { return@withContext it }

        val file = File(diskDir, "$id.png")
        if (file.exists() && file.length() > 0) {
            BitmapFactory.decodeFile(file.path)?.let {
                memory.put(id, it)
                return@withContext it
            }
        }

        try {
            val request = Request.Builder()
                .url(source.url(key))
                // Plitka serverlari User-Agent talab qiladi (OSM siyosati).
                .header("User-Agent", "AgroVision/1.0 (Android; qishloq xo'jaligi analitikasi)")
                .build()
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return@withContext null
                val bytes = response.body?.bytes() ?: return@withContext null
                val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                    ?: return@withContext null
                runCatching { file.writeBytes(bytes) }
                memory.put(id, bitmap)
                bitmap
            }
        } catch (e: Exception) {
            null
        }
    }

    /** Kesh hajmini cheklab turish (100 MB dan oshsa eng eskilari o'chiriladi). */
    suspend fun trimCache(maxBytes: Long = 100L * 1024 * 1024) = withContext(Dispatchers.IO) {
        val files = diskDir.listFiles()?.sortedBy { it.lastModified() } ?: return@withContext
        var total = files.sumOf { it.length() }
        for (file in files) {
            if (total <= maxBytes) break
            total -= file.length()
            file.delete()
        }
    }

    suspend fun clearCache() = withContext(Dispatchers.IO) {
        diskDir.listFiles()?.forEach { it.delete() }
        memory.evictAll()
    }

    fun cacheSizeKb(): Long = (diskDir.listFiles()?.sumOf { it.length() } ?: 0L) / 1024

    private fun id(key: TileKey, source: TileSource) =
        "${source.name.lowercase()}_${key.zoom}_${key.x}_${key.y}"

    companion object {
        const val TILE_SIZE = 256

        /** Longitude → global piksel X (berilgan zoom uchun). */
        fun lonToPixelX(lon: Double, zoom: Int): Double =
            (lon + 180.0) / 360.0 * TILE_SIZE * (1 shl zoom)

        /** Latitude → global piksel Y (Web Mercator). */
        fun latToPixelY(lat: Double, zoom: Int): Double {
            val rad = lat * PI / 180.0
            val y = ln(tan(rad) + 1.0 / kotlin.math.cos(rad))
            return (1.0 - y / PI) / 2.0 * TILE_SIZE * (1 shl zoom)
        }

        fun pixelXToLon(px: Double, zoom: Int): Double =
            px / (TILE_SIZE * (1 shl zoom)) * 360.0 - 180.0

        fun pixelYToLat(py: Double, zoom: Int): Double {
            val n = PI - 2.0 * PI * py / (TILE_SIZE * (1 shl zoom))
            return 180.0 / PI * atan(sinh(n))
        }

        /**
         * Berilgan geografik chegarani ekranga sig'diradigan eng katta zoom.
         * Plitka o'lchami sobit bo'lgani uchun zoom butun son bo'lishi shart.
         */
        fun fitZoom(
            minLon: Double, minLat: Double, maxLon: Double, maxLat: Double,
            widthPx: Int, heightPx: Int, maxZoom: Int,
        ): Int {
            for (zoom in maxZoom downTo 2) {
                val w = lonToPixelX(maxLon, zoom) - lonToPixelX(minLon, zoom)
                val h = latToPixelY(minLat, zoom) - latToPixelY(maxLat, zoom)
                if (w <= widthPx && h <= heightPx) return zoom
            }
            return 2
        }
    }
}
