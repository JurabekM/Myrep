package com.agrovision.app.data.local

import android.content.Context
import org.json.JSONArray

/**
 * Ilova ichidagi geografik ma'lumotnoma (`assets/`).
 *
 * Manba: geoBoundaries gbOpen UZB ADM1/ADM2 (ochiq litsenziya), soddalashtirilgan
 * va o'zbekcha nomlarga o'girilgan. Internet talab qilinmaydi — bu ma'lumot
 * ilova ichida, shuning uchun xarita offlayn holatda ham aniq chiziladi.
 *
 * Fayllar bir marta o'qilib xotirada saqlanadi (~4 000 nuqta, ~90 KB).
 */
object GeoAssets {

    /** Viloyat konturi: bir nechta halqa (anklav/eksklavlar uchun). */
    data class RegionShape(
        val name: String,
        val lat: Double,
        val lon: Double,
        /** Har bir halqa — (lon, lat) juftliklari ro'yxati. */
        val rings: List<List<Pair<Double, Double>>>,
    )

    data class DistrictRef(
        val region: String,
        val name: String,
        val lat: Double,
        val lon: Double,
    )

    @Volatile private var regionsCache: List<RegionShape>? = null
    @Volatile private var districtsCache: List<DistrictRef>? = null

    /** 14 hudud (13 viloyat + Toshkent shahri) chegaralari bilan. */
    fun regions(context: Context): List<RegionShape> =
        regionsCache ?: synchronized(this) {
            regionsCache ?: parseRegions(read(context, "uz_basemap.json")).also { regionsCache = it }
        }

    /** O'zbekistonning barcha tuman va shaharlari (199 ta). */
    fun districts(context: Context): List<DistrictRef> =
        districtsCache ?: synchronized(this) {
            districtsCache ?: parseDistricts(read(context, "uz_districts.json")).also { districtsCache = it }
        }

    /** Xaritaning statik chegaralari — barcha viloyat konturlarini qamrab oladi. */
    fun countryBounds(context: Context): DoubleArray {
        var minLon = 180.0; var maxLon = -180.0
        var minLat = 90.0; var maxLat = -90.0
        regions(context).forEach { region ->
            region.rings.forEach { ring ->
                ring.forEach { (lon, lat) ->
                    if (lon < minLon) minLon = lon
                    if (lon > maxLon) maxLon = lon
                    if (lat < minLat) minLat = lat
                    if (lat > maxLat) maxLat = lat
                }
            }
        }
        return doubleArrayOf(minLon, minLat, maxLon, maxLat)
    }

    private fun read(context: Context, name: String): String =
        context.assets.open(name).bufferedReader().use { it.readText() }

    private fun parseRegions(json: String): List<RegionShape> {
        val array = JSONArray(json)
        return (0 until array.length()).map { index ->
            val obj = array.getJSONObject(index)
            val ringsJson = obj.getJSONArray("rings")
            val rings = (0 until ringsJson.length()).map { r ->
                val ring = ringsJson.getJSONArray(r)
                (0 until ring.length()).map { p ->
                    val point = ring.getJSONArray(p)
                    point.getDouble(0) to point.getDouble(1)
                }
            }
            RegionShape(
                name = obj.getString("name"),
                lat = obj.getDouble("lat"),
                lon = obj.getDouble("lon"),
                rings = rings,
            )
        }
    }

    private fun parseDistricts(json: String): List<DistrictRef> {
        val array = JSONArray(json)
        return (0 until array.length()).map { index ->
            val obj = array.getJSONObject(index)
            DistrictRef(
                region = obj.getString("region"),
                name = obj.getString("name"),
                lat = obj.getDouble("lat"),
                lon = obj.getDouble("lon"),
            )
        }
    }
}
