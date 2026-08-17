package com.agrovision.app.data.repo

import com.agrovision.app.core.round1
import com.agrovision.app.data.local.*
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.abs
import kotlin.math.cos

@Singleton
class GeoRepository @Inject constructor(
    private val geoDao: GeoDao,
    private val cropDao: CropDao,
) {
    // ---- O'qish ----
    suspend fun regions(): List<RegionEntity> = geoDao.regions()
    suspend fun regionByName(name: String): RegionEntity? = geoDao.regionByName(name)
    suspend fun districts(): List<DistrictEntity> = geoDao.districts()
    suspend fun district(id: Long): DistrictEntity? = geoDao.district(id)
    suspend fun farmers(): List<FarmerEntity> = geoDao.farmers()
    suspend fun farms(): List<FarmEntity> = geoDao.farms()
    suspend fun fields(): List<FieldEntity> = geoDao.fields()
    suspend fun field(id: Long): FieldEntity? = geoDao.field(id)
    suspend fun fieldOptions(): List<FieldLabelRow> = geoDao.fieldOptions()
    suspend fun crops(): List<CropEntity> = cropDao.all()
    suspend fun crop(id: Long): CropEntity? = cropDao.byId(id)
    suspend fun mapFields(year: Int): List<MapFieldRow> = geoDao.mapFields(year)
    suspend fun soilStats(): List<SoilStatRow> = geoDao.soilStats()

    suspend fun search(query: String): List<SearchRow> =
        if (query.isBlank()) emptyList() else geoDao.search("%${query.trim()}%")

    /** Tuman nomlarini "Tuman (Viloyat)" ko'rinishida ro'yxatlash. */
    suspend fun districtOptions(): List<Pair<DistrictEntity, String>> {
        val regionNames = geoDao.regions().associate { it.id to it.name }
        return geoDao.districts().map { it to "${it.name} (${regionNames[it.regionId] ?: ""})" }
    }

    // ---- CRUD ro'yxatlari ----
    suspend fun farmerList(): List<FarmerListRow> = geoDao.farmerList()
    suspend fun farmList(): List<FarmListRow> = geoDao.farmList()
    suspend fun fieldList(): List<FieldListRow> = geoDao.fieldList()

    // ---- Yozish ----
    suspend fun createFarmer(name: String, phone: String, districtId: Long): Long =
        geoDao.insertFarmers(listOf(FarmerEntity(name = name.trim(), phone = phone.trim(), districtId = districtId))).first()

    suspend fun createFarm(name: String, farmerId: Long, districtId: Long): Long =
        geoDao.insertFarms(listOf(FarmEntity(name = name.trim(), farmerId = farmerId, districtId = districtId, areaHa = 0.0))).first()

    suspend fun createField(
        farmId: Long,
        name: String,
        areaHa: Double,
        soilType: String,
        lat: Double,
        lon: Double,
    ): Long {
        val polygon = squarePolygon(lat, lon, areaHa)
        val id = geoDao.insertFields(
            listOf(
                FieldEntity(
                    farmId = farmId, name = name.trim(), areaHa = areaHa,
                    soilType = soilType, lat = lat, lon = lon, polygon = polygon,
                ),
            ),
        ).first()
        geoDao.farm(farmId)?.let { farm ->
            geoDao.updateFarm(farm.copy(areaHa = (farm.areaHa + areaHa).round1()))
        }
        return id
    }

    /** Import qilingan poligonlardan dala yaratish. */
    suspend fun createFieldWithPolygon(
        farmId: Long,
        name: String,
        areaHa: Double,
        soilType: String,
        polygon: String,
    ): Long {
        val centroid = polygonCentroid(polygon)
        val id = geoDao.insertFields(
            listOf(
                FieldEntity(
                    farmId = farmId, name = name.trim(), areaHa = areaHa, soilType = soilType,
                    lat = centroid?.second ?: 41.3, lon = centroid?.first ?: 64.5, polygon = polygon,
                ),
            ),
        ).first()
        geoDao.farm(farmId)?.let { farm ->
            geoDao.updateFarm(farm.copy(areaHa = (farm.areaHa + areaHa).round1()))
        }
        return id
    }

    suspend fun updateCrop(crop: CropEntity) = cropDao.update(crop)

    suspend fun fieldsForGeoJson(): List<ExportFieldGeoRow> = geoDao.fieldsForGeoJson()

    companion object {
        /** Maydonga mos kvadrat poligon (markaz + yarim tomon). */
        fun squarePolygon(lat: Double, lon: Double, areaHa: Double): String {
            val half = maxOf(0.0012, kotlin.math.sqrt(areaHa) * 0.00045)
            val points = listOf(
                (lon - half) to (lat - half), (lon + half) to (lat - half),
                (lon + half) to (lat + half), (lon - half) to (lat + half),
            )
            return points.joinToString(";") { (x, y) ->
                "${(x * 1e6).toLong() / 1e6},${(y * 1e6).toLong() / 1e6}"
            }
        }

        /** "lon,lat;lon,lat;..." → (lon, lat) markaz. */
        fun parsePolygon(polygon: String): List<Pair<Double, Double>> =
            polygon.split(';').mapNotNull { part ->
                val xy = part.split(',')
                if (xy.size != 2) return@mapNotNull null
                val x = xy[0].toDoubleOrNull() ?: return@mapNotNull null
                val y = xy[1].toDoubleOrNull() ?: return@mapNotNull null
                x to y
            }

        fun polygonCentroid(polygon: String): Pair<Double, Double>? {
            val points = parsePolygon(polygon)
            if (points.isEmpty()) return null
            return points.sumOf { it.first } / points.size to points.sumOf { it.second } / points.size
        }

        /**
         * Poligon maydoni (gektar) — lokal ekvirektangulyar proyeksiyada
         * shoelace formulasi (desktop `gis/geo.py` fallback usuli).
         */
        fun polygonAreaHa(polygon: String): Double? {
            val points = parsePolygon(polygon)
            if (points.size < 3) return null
            val lat0 = points.sumOf { it.second } / points.size
            val mPerDegLat = 111_320.0
            val mPerDegLon = 111_320.0 * cos(Math.toRadians(lat0))
            val xy = points.map { (lon, lat) -> lon * mPerDegLon to lat * mPerDegLat }
            var area = 0.0
            for (i in xy.indices) {
                val j = (i + 1) % xy.size
                area += xy[i].first * xy[j].second - xy[j].first * xy[i].second
            }
            return (abs(area) / 2 / 10_000).round1()
        }
    }
}
