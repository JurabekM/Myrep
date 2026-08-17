package com.agrovision.app.data.repo

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import com.agrovision.app.core.round3
import com.agrovision.app.data.local.*
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

data class FieldHealth(
    val fieldId: Long,
    val field: String,
    val farm: String,
    val region: String,
    val ndvi: Double,
    val evi: Double,
    val epochDay: Long,
    val status: String,
)

@Singleton
class SatelliteRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val satelliteDao: SatelliteDao,
    private val geoDao: GeoDao,
    private val importedFileDao: ImportedFileDao,
) {
    /** Desktop `LocalProvider` — qurilmadagi indeks seriyasi. */
    suspend fun series(fieldId: Long, days: Int = 730): List<NdviPointRow> =
        satelliteDao.series(fieldId, LocalDate.now().minusDays(days.toLong()).toEpochDay())

    suspend fun fieldHealth(): List<FieldHealth> = satelliteDao.fieldHealth().map {
        FieldHealth(
            fieldId = it.fieldId, field = it.field, farm = it.farm, region = it.region,
            ndvi = it.ndvi, evi = it.evi, epochDay = it.epochDay, status = classify(it.ndvi),
        )
    }

    suspend fun fieldOptions(): List<FieldLabelRow> = geoDao.fieldOptions()

    suspend fun recentList(): List<NdviListRow> = satelliteDao.recentList()

    /** Desktop bilan bir xil klassifikatsiya. */
    fun classify(ndvi: Double): String = when {
        ndvi >= 0.55 -> "A'lo"
        ndvi >= 0.40 -> "Yaxshi"
        ndvi >= 0.25 -> "O'rtacha"
        else -> "Zaif"
    }

    /**
     * Dron/sun'iy yo'ldosh tasvirini qayta ishlash — desktop
     * `process_drone_image` analogi. Rasterio mavjud bo'lmaganda desktop
     * Pillow bilan yorqinlik asosida vegetatsiya bahosini hisoblaydi; bu yerda
     * ham xuddi shunday: RGB tasvirdan **yashillik indeksi** (ExG — Excess
     * Green) hisoblanadi va NDVI proksi sifatida yoziladi.
     */
    suspend fun processImage(uri: Uri, fieldId: Long, username: String): String = withContext(Dispatchers.IO) {
        val name = uri.lastPathSegment?.substringAfterLast('/') ?: "tasvir"
        try {
            val bitmap = context.contentResolver.openInputStream(uri)?.use { stream ->
                BitmapFactory.decodeStream(stream, null, BitmapFactory.Options().apply { inSampleSize = 4 })
            } ?: return@withContext "Tasvirni o'qib bo'lmadi: $name"

            val index = excessGreenIndex(bitmap)
            bitmap.recycle()
            val ndvi = (0.10 + index * 0.75).coerceIn(0.05, 0.95).round3()
            val evi = (ndvi * 0.85).round3()

            satelliteDao.insertAll(
                listOf(
                    SatelliteIndexEntity(
                        fieldId = fieldId, epochDay = LocalDate.now().toEpochDay(),
                        ndvi = ndvi, evi = evi, source = "dron",
                    ),
                ),
            )
            val summary = "Tasvir qayta ishlandi: ${bitmap.width}x${bitmap.height}px, " +
                "yashillik indeksi ${String.format(java.util.Locale.US, "%.3f", index)} → NDVI ≈ $ndvi"
            importedFileDao.insert(
                ImportedFileEntity(
                    filename = name, fileType = "image", uploadedBy = username, summary = summary,
                ),
            )
            summary
        } catch (e: Exception) {
            "Tasvirni qayta ishlashda xato: ${e.message ?: "noma'lum"}"
        }
    }

    /**
     * ExG = (2G − R − B) / (2G + R + B) — RGB tasvirdan o'simlik qoplamini
     * baholashning standart usuli (haqiqiy NIR kanali bo'lmagan holatda).
     */
    private fun excessGreenIndex(bitmap: Bitmap): Double {
        val step = maxOf(1, minOf(bitmap.width, bitmap.height) / 100)
        var sum = 0.0
        var count = 0
        var y = 0
        while (y < bitmap.height) {
            var x = 0
            while (x < bitmap.width) {
                val pixel = bitmap.getPixel(x, y)
                val r = (pixel shr 16 and 0xFF).toDouble()
                val g = (pixel shr 8 and 0xFF).toDouble()
                val b = (pixel and 0xFF).toDouble()
                val denominator = 2 * g + r + b
                if (denominator > 1) {
                    sum += ((2 * g - r - b) / denominator).coerceIn(-1.0, 1.0)
                    count++
                }
                x += step
            }
            y += step
        }
        if (count == 0) return 0.3
        return ((sum / count) + 1) / 2   // [-1,1] → [0,1]
    }
}
