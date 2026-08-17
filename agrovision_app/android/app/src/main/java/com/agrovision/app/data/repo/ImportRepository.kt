package com.agrovision.app.data.repo

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import com.agrovision.app.core.Session
import com.agrovision.app.core.toSafeDouble
import com.agrovision.app.core.toSafeInt
import com.agrovision.app.data.local.*
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.xmlpull.v1.XmlPullParser
import org.xmlpull.v1.XmlPullParserFactory
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Universal import — desktop `utils/importer.py` analogi.
 * Qo'llab-quvvatlanadi: CSV/TSV (narx va hosildorlik), JSON, GeoJSON va KML
 * (dala poligonlari). Fayl turi kengaytma va ustun imzosi bo'yicha aniqlanadi.
 */
@Singleton
class ImportRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val marketDao: MarketDao,
    private val cropDao: CropDao,
    private val geoDao: GeoDao,
    private val yieldDao: YieldDao,
    private val importedFileDao: ImportedFileDao,
) {
    suspend fun import(uri: Uri): String = withContext(Dispatchers.IO) {
        val name = displayName(uri)
        val summary = try {
            val content = context.contentResolver.openInputStream(uri)?.use {
                it.readBytes().toString(Charsets.UTF_8)
            } ?: return@withContext "Faylni o'qib bo'lmadi: $name"

            when {
                name.endsWith(".geojson", true) -> importGeoJson(content)
                name.endsWith(".kml", true) -> importKml(content)
                name.endsWith(".json", true) -> importGeoJson(content)
                name.endsWith(".csv", true) || name.endsWith(".tsv", true) || name.endsWith(".txt", true) ->
                    importDelimited(content)
                else -> "Qo'llab-quvvatlanmagan format: $name (CSV, JSON, GeoJSON yoki KML kutilgan)"
            }
        } catch (e: Exception) {
            "Import xatosi ($name): ${e.message ?: "noma'lum"}"
        }

        importedFileDao.insert(
            ImportedFileEntity(
                filename = name,
                fileType = name.substringAfterLast('.', "").lowercase(),
                uploadedBy = Session.current?.username ?: "",
                summary = summary.take(500),
            ),
        )
        summary
    }

    // -----------------------------------------------------------------------
    // CSV / TSV
    // -----------------------------------------------------------------------
    private suspend fun importDelimited(content: String): String {
        val lines = content.lines().filter { it.isNotBlank() }
        if (lines.size < 2) return "Faylda ma'lumot qatorlari yo'q."
        val delimiter = if (lines[0].count { it == '\t' } > lines[0].count { it == ',' }) '\t' else ','
        val headers = splitRow(lines[0], delimiter).map { it.trim().lowercase() }
        val rows = lines.drop(1).map { splitRow(it, delimiter) }

        val hasPrice = headers.any { it in setOf("narx", "price", "price_per_kg", "narx_som_kg") }
        val hasYield = headers.any { it in setOf("hosildorlik", "yield", "yield_t_ha", "hosildorlik_t_ga") }

        return when {
            hasPrice -> importPrices(headers, rows)
            hasYield -> importYields(headers, rows)
            else -> "Ustunlar aniqlanmadi. Narx importi uchun [ekin, narx, sana]; " +
                "hosildorlik uchun [dala, ekin, yil, hosildorlik] ustunlari kerak."
        }
    }

    private suspend fun importPrices(headers: List<String>, rows: List<List<String>>): String {
        val cropIndex = headers.indexOfFirst { it in setOf("ekin", "crop", "ekin_nomi") }
        val priceIndex = headers.indexOfFirst { it in setOf("narx", "price", "price_per_kg", "narx_som_kg") }
        val dateIndex = headers.indexOfFirst { it in setOf("sana", "date") }
        val marketIndex = headers.indexOfFirst { it in setOf("bozor", "market", "market_name") }
        if (cropIndex < 0 || priceIndex < 0) return "Narx importi uchun 'ekin' va 'narx' ustunlari kerak."

        val crops = cropDao.all().associateBy { it.name.lowercase() }
        val batch = mutableListOf<MarketPriceEntity>()
        var skipped = 0
        rows.forEach { row ->
            val crop = crops[row.getOrNull(cropIndex)?.trim()?.lowercase()]
            val price = row.getOrNull(priceIndex).toSafeDouble()
            if (crop == null || price == null || price <= 0) { skipped++; return@forEach }
            val date = parseDate(row.getOrNull(dateIndex)) ?: LocalDate.now()
            batch += MarketPriceEntity(
                cropId = crop.id, epochDay = date.toEpochDay(), pricePerKg = price,
                marketName = row.getOrNull(marketIndex)?.trim()?.ifBlank { null } ?: "Import",
                source = "import",
            )
        }
        if (batch.isNotEmpty()) marketDao.insertAll(batch)
        return "Bozor narxlari importi: ${batch.size} qator qo'shildi, $skipped o'tkazib yuborildi."
    }

    private suspend fun importYields(headers: List<String>, rows: List<List<String>>): String {
        val fieldIndex = headers.indexOfFirst { it in setOf("dala", "field", "kontur") }
        val cropIndex = headers.indexOfFirst { it in setOf("ekin", "crop") }
        val yearIndex = headers.indexOfFirst { it in setOf("yil", "year") }
        val yieldIndex = headers.indexOfFirst { it in setOf("hosildorlik", "yield", "yield_t_ha", "hosildorlik_t_ga") }
        if (cropIndex < 0 || yearIndex < 0 || yieldIndex < 0) {
            return "Hosildorlik importi uchun 'ekin', 'yil', 'hosildorlik' ustunlari kerak."
        }
        val crops = cropDao.all().associateBy { it.name.lowercase() }
        val fields = geoDao.fields()
        if (fields.isEmpty()) return "Import uchun avval kamida bitta dala mavjud bo'lishi kerak."
        val fieldsByName = fields.associateBy { it.name.lowercase() }

        val batch = mutableListOf<YieldRecordEntity>()
        var skipped = 0
        rows.forEach { row ->
            val crop = crops[row.getOrNull(cropIndex)?.trim()?.lowercase()]
            val year = row.getOrNull(yearIndex).toSafeInt()
            val value = row.getOrNull(yieldIndex).toSafeDouble()
            val field = fieldsByName[row.getOrNull(fieldIndex)?.trim()?.lowercase()] ?: fields.first()
            if (crop == null || year == null || value == null || value <= 0) { skipped++; return@forEach }
            batch += YieldRecordEntity(
                fieldId = field.id, cropId = crop.id, year = year, areaHa = field.areaHa,
                yieldTHa = value, productionT = value * field.areaHa,
            )
        }
        if (batch.isNotEmpty()) yieldDao.insertAll(batch)
        return "Hosildorlik importi: ${batch.size} qator qo'shildi, $skipped o'tkazib yuborildi."
    }

    // -----------------------------------------------------------------------
    // GeoJSON
    // -----------------------------------------------------------------------
    private suspend fun importGeoJson(content: String): String {
        val json = JSONObject(content)
        val features = when (json.optString("type")) {
            "FeatureCollection" -> json.optJSONArray("features")
            "Feature" -> org.json.JSONArray().put(json)
            else -> null
        } ?: return "GeoJSON strukturasi topilmadi (FeatureCollection yoki Feature kutilgan)."

        val polygons = mutableListOf<Pair<String, String>>()   // (nom, poligon)
        for (i in 0 until features.length()) {
            val feature = features.optJSONObject(i) ?: continue
            val geometry = feature.optJSONObject("geometry") ?: continue
            if (geometry.optString("type") != "Polygon") continue
            val ring = geometry.optJSONArray("coordinates")?.optJSONArray(0) ?: continue
            val points = (0 until ring.length()).mapNotNull { index ->
                val pair = ring.optJSONArray(index) ?: return@mapNotNull null
                if (pair.length() < 2) return@mapNotNull null
                "${pair.optDouble(0)},${pair.optDouble(1)}"
            }
            if (points.size < 3) continue
            val name = feature.optJSONObject("properties")?.optString("name")?.ifBlank { null }
                ?: "GeoJSON-kontur-${i + 1}"
            polygons += name to points.joinToString(";")
        }
        return createFields(polygons, "GeoJSON")
    }

    // -----------------------------------------------------------------------
    // KML
    // -----------------------------------------------------------------------
    private suspend fun importKml(content: String): String {
        val parser = XmlPullParserFactory.newInstance().newPullParser()
        parser.setInput(content.reader())
        val polygons = mutableListOf<Pair<String, String>>()
        var currentName: String? = null
        var counter = 0

        var event = parser.eventType
        while (event != XmlPullParser.END_DOCUMENT) {
            if (event == XmlPullParser.START_TAG) {
                when (parser.name.lowercase()) {
                    "name" -> currentName = parser.nextText().trim().ifBlank { null }
                    "coordinates" -> {
                        val points = parser.nextText().trim().split(Regex("\\s+")).mapNotNull { token ->
                            val parts = token.split(',')
                            if (parts.size < 2) return@mapNotNull null
                            val lon = parts[0].toDoubleOrNull() ?: return@mapNotNull null
                            val lat = parts[1].toDoubleOrNull() ?: return@mapNotNull null
                            "$lon,$lat"
                        }
                        if (points.size >= 3) {
                            counter++
                            polygons += (currentName ?: "KML-kontur-$counter") to points.joinToString(";")
                            currentName = null
                        }
                    }
                }
            }
            event = parser.next()
        }
        return createFields(polygons, "KML")
    }

    /** Import qilingan poligonlardan "Import xo'jaligi" ostida dalalar yaratadi. */
    private suspend fun createFields(polygons: List<Pair<String, String>>, source: String): String {
        if (polygons.isEmpty()) return "$source faylida poligon topilmadi."
        val farms = geoDao.farms()
        val districts = geoDao.districts()
        if (districts.isEmpty()) return "Import uchun ma'lumotnoma (tumanlar) kerak."

        val importFarm = farms.firstOrNull { it.name == "Import xo'jaligi" } ?: run {
            val farmers = geoDao.farmers()
            val farmerId = farmers.firstOrNull()?.id
                ?: geoDao.insertFarmers(
                    listOf(FarmerEntity(name = "Import fermeri", phone = "", districtId = districts.first().id)),
                ).first()
            val districtId = farmers.firstOrNull()?.districtId ?: districts.first().id
            val id = geoDao.insertFarms(
                listOf(FarmEntity(name = "Import xo'jaligi", farmerId = farmerId, districtId = districtId, areaHa = 0.0)),
            ).first()
            geoDao.farm(id)!!
        }

        // Bir xil faylni ikki marta yuklash dublikat dala yaratmasligi kerak —
        // import nom bo'yicha idempotent qilinadi.
        val existingNames = geoDao.fields().map { it.name.trim().lowercase() }.toHashSet()

        var created = 0
        var skipped = 0
        var totalArea = 0.0
        polygons.forEach { (name, polygon) ->
            if (!existingNames.add(name.take(120).trim().lowercase())) {
                skipped++
                return@forEach
            }
            val area = GeoRepository.polygonAreaHa(polygon) ?: return@forEach
            val centroid = GeoRepository.polygonCentroid(polygon) ?: return@forEach
            geoDao.insertFields(
                listOf(
                    FieldEntity(
                        farmId = importFarm.id, name = name.take(120), areaHa = area,
                        soilType = "bo'z tuproq", lat = centroid.second, lon = centroid.first, polygon = polygon,
                    ),
                ),
            )
            created++
            totalArea += area
        }
        if (created > 0) {
            geoDao.updateFarm(importFarm.copy(areaHa = importFarm.areaHa + totalArea))
        }
        val skippedNote = if (skipped > 0) ", $skipped ta mavjud nom o'tkazib yuborildi" else ""
        return "$source importi: $created ta dala poligoni qo'shildi " +
            "(jami ${"%.1f".format(java.util.Locale.US, totalArea)} ga)$skippedNote."
    }

    // -----------------------------------------------------------------------
    private fun splitRow(line: String, delimiter: Char): List<String> {
        val result = mutableListOf<String>()
        val current = StringBuilder()
        var inQuotes = false
        line.forEach { char ->
            when {
                char == '"' -> inQuotes = !inQuotes
                char == delimiter && !inQuotes -> { result += current.toString(); current.clear() }
                else -> current.append(char)
            }
        }
        result += current.toString()
        return result.map { it.trim() }
    }

    private fun parseDate(text: String?): LocalDate? {
        val value = text?.trim()?.ifBlank { null } ?: return null
        return runCatching { LocalDate.parse(value) }.getOrNull()
            ?: runCatching { LocalDate.parse(value.replace('.', '-').replace('/', '-')) }.getOrNull()
    }

    private fun displayName(uri: Uri): String {
        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0 && cursor.moveToFirst()) return cursor.getString(index) ?: "fayl"
        }
        return uri.lastPathSegment?.substringAfterLast('/') ?: "fayl"
    }

    suspend fun recentImports(): List<ImportedFileEntity> = importedFileDao.recent()
}
