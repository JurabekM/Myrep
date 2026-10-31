package uz.epiradar.engine.geo

import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.pow
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

data class Country(
    val iso3: String,
    val iso2: String,
    val nameEn: String,
    val nameUz: String,
    val lat: Double,
    val lng: Double,
    val subregion: String,
    val borders: List<String>,
    val aliases: List<String>,
)

/** Mamlakatlar ma'lumotnomasi (`countries.tsv`, manba: mledoze/countries, ODbL). */
class Countries(
    val all: List<Country>,
) {
    private val byIso3 = all.associateBy { it.iso3 }

    operator fun get(iso3: String): Country? = byIso3[iso3]

    fun nameUz(iso3: String): String = byIso3[iso3]?.nameUz ?: iso3

    /** Ikki mamlakat markazlari orasidagi masofa (km, katta doira bo'yicha). */
    fun distanceKm(
        a: String,
        b: String,
    ): Int? {
        val ca = byIso3[a] ?: return null
        val cb = byIso3[b] ?: return null
        return haversineKm(ca.lat, ca.lng, cb.lat, cb.lng).roundToInt()
    }

    fun areNeighbors(
        a: String,
        b: String,
    ): Boolean = byIso3[a]?.borders?.contains(b) == true

    /** Qo'shnining qo'shnisi (2-daraja), masalan O'zbekiston → Qozog'iston → Rossiya. */
    fun isSecondDegree(
        a: String,
        b: String,
    ): Boolean {
        val first = byIso3[a]?.borders ?: return false
        return first.any { n -> byIso3[n]?.borders?.contains(b) == true }
    }

    /**
     * Yaqinlik koeffitsienti (0..1): bir mamlakat — 1, chegaradosh — 0.9, ikkinchi daraja — 0.75,
     * keyin masofaga qarab kamayadi. Havo qatnovi tufayli hatto uzoq o'choq ham 0.25 dan past emas.
     */
    fun proximity(
        user: String,
        outbreak: String,
    ): Double {
        if (user == outbreak) return 1.0
        if (areNeighbors(user, outbreak)) return 0.9
        if (isSecondDegree(user, outbreak)) return 0.75
        val d = distanceKm(user, outbreak) ?: return 0.4
        return when {
            d < 1500 -> 0.75
            d < 3000 -> 0.6
            d < 5000 -> 0.45
            d < 8000 -> 0.35
            else -> 0.25
        }
    }

    companion object {
        fun haversineKm(
            lat1: Double,
            lng1: Double,
            lat2: Double,
            lng2: Double,
        ): Double {
            val r = 6371.0
            val dLat = Math.toRadians(lat2 - lat1)
            val dLng = Math.toRadians(lng2 - lng1)
            val h =
                sin(dLat / 2).pow(2) +
                    cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLng / 2).pow(2)
            return 2 * r * asin(sqrt(h))
        }

        fun parseTsv(text: String): Countries =
            Countries(
                text
                    .lineSequence()
                    .filter { it.isNotBlank() && !it.startsWith("#") }
                    .map { line ->
                        val c = line.split('\t')
                        require(c.size >= 9) { "countries.tsv: noto'g'ri qator: $line" }
                        Country(
                            iso3 = c[0],
                            iso2 = c[1],
                            nameEn = c[2],
                            nameUz = c[3],
                            lat = c[4].toDouble(),
                            lng = c[5].toDouble(),
                            subregion = c[6],
                            borders = c[7].split(',').filter { it.isNotBlank() },
                            aliases = c[8].split('|').filter { it.isNotBlank() },
                        )
                    }.toList(),
            )

        fun load(): Countries {
            val stream =
                Countries::class.java.getResourceAsStream("/epiradar/countries.tsv")
                    ?: error("countries.tsv resursi topilmadi")
            return parseTsv(stream.bufferedReader(Charsets.UTF_8).use { it.readText() })
        }
    }
}
