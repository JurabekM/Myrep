package com.agrovision.app.data.repo

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Paint
import android.graphics.pdf.PdfDocument
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import com.agrovision.app.config.Constants
import com.agrovision.app.core.Fmt
import com.agrovision.app.data.local.*
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton

data class TableData(val title: String, val headers: List<String>, val rows: List<List<String>>)

enum class ExportDataset(val title: String) {
    YIELDS("Hosildorlik yozuvlari"),
    PRICES("Bozor narxlari"),
    WEATHER("Ob-havo yozuvlari"),
    FINANCE("Moliya yozuvlari"),
    IRRIGATION("Sug'orish yozuvlari"),
    NDVI("NDVI indekslari"),
}

/**
 * Hisobot va eksport — desktop `reports/exporter.py` analogi.
 * Formatlar: PDF (Android PdfDocument), CSV, JSON, GeoJSON, HTML, PNG.
 * Barcha fayllar `Downloads/AgroVision` papkasiga yoziladi.
 */
@Singleton
class ReportRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val kpiRepository: KpiRepository,
    private val yieldDao: YieldDao,
    private val marketDao: MarketDao,
    private val weatherDao: WeatherDao,
    private val financeDao: FinanceDao,
    private val irrigationDao: IrrigationDao,
    private val satelliteDao: SatelliteDao,
    private val geoDao: GeoDao,
) {
    // -----------------------------------------------------------------------
    // Hisobot jadvallari (desktop `_report_tables`)
    // -----------------------------------------------------------------------
    private suspend fun reportTables(year: Int): List<TableData> = listOf(
        TableData(
            "Viloyatlar bo'yicha hosildorlik",
            listOf("Hudud", "t/ga", "Ishlab chiqarish (t)", "Maydon (ga)"),
            kpiRepository.byRegion(year).map {
                listOf(it.region, Fmt.dec(it.avgYield, 2), Fmt.num(it.production, 0), Fmt.num(it.area, 0))
            },
        ),
        TableData(
            "Ekinlar taqsimoti",
            listOf("Ekin", "Maydon (ga)", "Ishlab chiqarish (t)", "t/ga"),
            kpiRepository.cropDistribution(year).take(12).map {
                listOf(it.crop, Fmt.num(it.area, 0), Fmt.num(it.production, 0), Fmt.dec(it.avgYield, 2))
            },
        ),
        TableData(
            "Eng samarali xo'jaliklar",
            listOf("Xo'jalik", "Hudud", "Ishlab chiqarish (t)", "t/ga"),
            kpiRepository.topFarms(year).map {
                listOf(it.farm, it.region, Fmt.num(it.production, 0), Fmt.dec(it.avgYield, 2))
            },
        ),
    )

    private suspend fun kpiLines(year: Int): List<Pair<String, String>> {
        val kpi = kpiRepository.compute(year)
        return listOf(
            "Umumiy yer maydoni" to "${Fmt.num(kpi.totalAreaHa, 0)} ga",
            "Fermerlar / xo'jaliklar / dalalar" to "${kpi.farmers} / ${kpi.farms} / ${kpi.fields}",
            "O'rtacha hosildorlik" to "${Fmt.dec(kpi.avgYieldTHa, 2)} t/ga",
            "Jami ishlab chiqarish" to "${Fmt.num(kpi.productionT, 0)} t",
            "Daromad" to "${Fmt.money(kpi.income)} so'm",
            "Xarajat" to "${Fmt.money(kpi.expense)} so'm",
            "Sof foyda (ROI)" to "${Fmt.money(kpi.profit)} so'm (${Fmt.dec(kpi.roiPercent, 1)}%)",
            "O'rtacha NDVI" to Fmt.dec(kpi.avgNdvi, 3),
            "Sug'orish suvi" to "${Fmt.dec(kpi.waterMillionM3, 2)} mln m³",
        )
    }

    // -----------------------------------------------------------------------
    // PDF
    // -----------------------------------------------------------------------
    suspend fun exportPdf(year: Int): String = withContext(Dispatchers.IO) {
        val document = PdfDocument()
        val titlePaint = Paint().apply { textSize = 18f; isFakeBoldText = true }
        val headerPaint = Paint().apply { textSize = 13f; isFakeBoldText = true }
        val textPaint = Paint().apply { textSize = 10f }
        val smallPaint = Paint().apply { textSize = 9f }

        var pageNumber = 1
        var page = document.startPage(PdfDocument.PageInfo.Builder(595, 842, pageNumber).create())
        var canvas = page.canvas
        var y = 48f

        fun newPageIfNeeded(needed: Float) {
            if (y + needed < 810f) return
            document.finishPage(page)
            pageNumber++
            page = document.startPage(PdfDocument.PageInfo.Builder(595, 842, pageNumber).create())
            canvas = page.canvas
            y = 48f
        }

        canvas.drawText("AgroVision — $year-yil yakuniy hisoboti", 40f, y, titlePaint)
        y += 18f
        canvas.drawText(
            "Yaratildi: ${SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(Date())}",
            40f, y, smallPaint,
        )
        y += 26f

        canvas.drawText("Asosiy ko'rsatkichlar", 40f, y, headerPaint)
        y += 18f
        kpiLines(year).forEach { (label, value) ->
            newPageIfNeeded(16f)
            canvas.drawText(label, 46f, y, textPaint)
            canvas.drawText(value, 330f, y, textPaint)
            y += 15f
        }
        y += 12f

        reportTables(year).forEach { table ->
            newPageIfNeeded(60f)
            canvas.drawText(table.title, 40f, y, headerPaint)
            y += 17f
            val columnWidth = 515f / table.headers.size.coerceAtLeast(1)
            table.headers.forEachIndexed { index, header ->
                canvas.drawText(header.take(18), 42f + index * columnWidth, y, smallPaint.also { it.isFakeBoldText = true })
            }
            smallPaint.isFakeBoldText = false
            y += 13f
            table.rows.take(24).forEach { row ->
                newPageIfNeeded(14f)
                row.forEachIndexed { index, cell ->
                    canvas.drawText(cell.take(20), 42f + index * columnWidth, y, smallPaint)
                }
                y += 12f
            }
            y += 14f
        }

        document.finishPage(page)
        val bytes = ByteArrayOutputStream().also { document.writeTo(it) }.toByteArray()
        document.close()
        write("agrovision_hisobot_${year}_${stamp()}.pdf", "application/pdf", bytes)
    }

    // -----------------------------------------------------------------------
    // HTML
    // -----------------------------------------------------------------------
    suspend fun exportHtml(year: Int): String = withContext(Dispatchers.IO) {
        val kpi = kpiLines(year)
        val sections = reportTables(year).joinToString("\n") { table ->
            buildString {
                append("<h2>${table.title}</h2><table><tr>")
                table.headers.forEach { append("<th>$it</th>") }
                append("</tr>")
                table.rows.forEach { row ->
                    append("<tr>")
                    row.forEach { append("<td>$it</td>") }
                    append("</tr>")
                }
                append("</table>")
            }
        }
        val html = """
            <!DOCTYPE html><html lang="uz"><head><meta charset="utf-8">
            <title>AgroVision hisobot $year</title><style>
            body{font-family:sans-serif;margin:24px;color:#1b2a1b}
            h1{color:#2e7d32}h2{color:#33691e;border-bottom:2px solid #aed581;padding-bottom:4px}
            table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}
            td,th{padding:6px 10px;border-bottom:1px solid #dcedc8;text-align:left}
            th{background:#f1f8e9}
            .kpi{display:inline-block;background:#f1f8e9;border-radius:12px;padding:12px 18px;margin:6px;min-width:150px}
            .kpi b{display:block;font-size:20px;color:#2e7d32}
            </style></head><body>
            <h1>AgroVision — $year-yil yakuniy hisoboti</h1>
            <p>Yaratildi: ${SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(Date())}</p>
            <div>${kpi.joinToString("") { "<div class=\"kpi\"><b>${it.second}</b>${it.first}</div>" }}</div>
            $sections
            </body></html>
        """.trimIndent()
        write("agrovision_hisobot_${year}_${stamp()}.html", "text/html", html.toByteArray())
    }

    // -----------------------------------------------------------------------
    // Dataset eksporti (CSV / JSON)
    // -----------------------------------------------------------------------
    suspend fun exportDataset(dataset: ExportDataset, format: String): String = withContext(Dispatchers.IO) {
        val table = datasetTable(dataset)
        val base = "agrovision_${dataset.name.lowercase()}_${stamp()}"
        when (format.lowercase()) {
            "json" -> {
                val array = JSONArray()
                table.rows.forEach { row ->
                    val obj = JSONObject()
                    table.headers.forEachIndexed { index, header -> obj.put(header, row.getOrElse(index) { "" }) }
                    array.put(obj)
                }
                write("$base.json", "application/json", array.toString(2).toByteArray())
            }
            else -> {
                val csv = buildString {
                    appendLine(table.headers.joinToString(",") { csvEscape(it) })
                    table.rows.forEach { row -> appendLine(row.joinToString(",") { csvEscape(it) }) }
                }
                // BOM — Excel UTF-8 ni to'g'ri o'qishi uchun
                write("$base.csv", "text/csv", byteArrayOf(0xEF.toByte(), 0xBB.toByte(), 0xBF.toByte()) + csv.toByteArray())
            }
        }
    }

    suspend fun datasetTable(dataset: ExportDataset): TableData = when (dataset) {
        ExportDataset.YIELDS -> TableData(
            dataset.title,
            listOf("Yil", "Hudud", "Tuman", "Xo'jalik", "Dala", "Ekin", "Maydon_ga", "Hosildorlik_t_ga", "Ishlab_chiqarish_t"),
            yieldDao.exportRows().map {
                listOf(
                    it.year.toString(), it.region, it.district, it.farm, it.field, it.crop,
                    Fmt.dec(it.areaHa, 1), Fmt.dec(it.yieldTHa, 2), Fmt.dec(it.productionT, 1),
                )
            },
        )
        ExportDataset.PRICES -> TableData(
            dataset.title,
            listOf("Sana", "Ekin", "Narx_som_kg", "Bozor", "Manba"),
            marketDao.exportRows().map {
                listOf(Fmt.date(it.epochDay), it.crop, Fmt.dec(it.pricePerKg, 0), it.marketName, it.source)
            },
        )
        ExportDataset.WEATHER -> TableData(
            dataset.title,
            listOf("Sana", "Tuman", "T_min", "T_max", "Yogin_mm", "Namlik", "Manba"),
            weatherDao.exportRows().map {
                listOf(
                    Fmt.date(it.epochDay), it.district, Fmt.dec(it.tMin, 1), Fmt.dec(it.tMax, 1),
                    Fmt.dec(it.precipitationMm, 1), Fmt.dec(it.humidity, 1), it.source,
                )
            },
        )
        ExportDataset.FINANCE -> TableData(
            dataset.title,
            listOf("Yil", "Xo'jalik", "Turi", "Summa", "Izoh"),
            financeDao.exportRows().map {
                listOf(it.year.toString(), it.farm, it.category, Fmt.dec(it.amount, 0), it.note)
            },
        )
        ExportDataset.IRRIGATION -> TableData(
            dataset.title,
            listOf("Sana", "Dala", "Suv_m3", "Usul"),
            irrigationDao.exportRows().map {
                listOf(Fmt.date(it.epochDay), it.field, Fmt.dec(it.waterM3, 0), it.method)
            },
        )
        ExportDataset.NDVI -> TableData(
            dataset.title,
            listOf("Sana", "Dala", "NDVI", "EVI", "Manba"),
            satelliteDao.exportRows().map {
                listOf(Fmt.date(it.epochDay), it.field, Fmt.dec(it.ndvi, 3), Fmt.dec(it.evi, 3), it.source)
            },
        )
    }

    // -----------------------------------------------------------------------
    // GeoJSON (dala poligonlari)
    // -----------------------------------------------------------------------
    suspend fun exportGeoJson(): String = withContext(Dispatchers.IO) {
        val features = JSONArray()
        geoDao.fieldsForGeoJson().forEach { row ->
            val points = GeoRepository.parsePolygon(row.polygon)
            if (points.size < 3) return@forEach
            val ring = JSONArray()
            points.forEach { (lon, lat) -> ring.put(JSONArray().put(lon).put(lat)) }
            ring.put(JSONArray().put(points[0].first).put(points[0].second))
            features.put(
                JSONObject()
                    .put("type", "Feature")
                    .put(
                        "geometry",
                        JSONObject().put("type", "Polygon").put("coordinates", JSONArray().put(ring)),
                    )
                    .put(
                        "properties",
                        JSONObject()
                            .put("name", row.name).put("area_ha", row.areaHa)
                            .put("soil", row.soilType).put("farm", row.farm).put("region", row.region),
                    ),
            )
        }
        val geoJson = JSONObject().put("type", "FeatureCollection").put("features", features)
        write("agrovision_dalalar_${stamp()}.geojson", "application/geo+json", geoJson.toString().toByteArray())
    }

    // -----------------------------------------------------------------------
    // PNG (grafik/dashboard snapshot)
    // -----------------------------------------------------------------------
    suspend fun exportBitmap(bitmap: Bitmap, name: String): String = withContext(Dispatchers.IO) {
        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
        write("${name}_${stamp()}.png", "image/png", stream.toByteArray())
    }

    // -----------------------------------------------------------------------
    private fun stamp() = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())

    private fun csvEscape(value: String): String =
        if (value.contains(',') || value.contains('"') || value.contains('\n')) {
            "\"${value.replace("\"", "\"\"")}\""
        } else {
            value
        }

    /** Faylni Downloads/AgroVision papkasiga yozadi va nomini qaytaradi. */
    private fun write(fileName: String, mimeType: String, bytes: ByteArray): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, fileName)
                put(MediaStore.Downloads.MIME_TYPE, mimeType)
                put(MediaStore.Downloads.RELATIVE_PATH, "${Environment.DIRECTORY_DOWNLOADS}/${Constants.APP_NAME}")
            }
            val uri = context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: error("Faylni yozib bo'lmadi")
            context.contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
            return fileName
        }
        @Suppress("DEPRECATION")
        val dir = File(
            Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
            Constants.APP_NAME,
        ).apply { mkdirs() }
        File(dir, fileName).writeBytes(bytes)
        return fileName
    }
}
