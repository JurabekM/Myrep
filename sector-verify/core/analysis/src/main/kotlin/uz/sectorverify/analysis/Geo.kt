package uz.sectorverify.analysis

import kotlin.math.asin
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.sin
import kotlin.math.sqrt

data class LatLon(val lat: Double, val lon: Double)

/** Sferik Yer geodeziyasi; o'lchov qamraydigan 0–2 km da xatosi 1 m dan ancha kichik. */
object Geo {
    const val EARTH_RADIUS_M = 6_371_008.8

    /** Haversine masofasi, metrda. */
    fun distanceM(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val p1 = Math.toRadians(lat1)
        val p2 = Math.toRadians(lat2)
        val dp = p2 - p1
        val dl = Math.toRadians(lon2 - lon1)
        val h = sin(dp / 2).let { it * it } + cos(p1) * cos(p2) * sin(dl / 2).let { it * it }
        return 2 * EARTH_RADIUS_M * asin(sqrt(h.coerceIn(0.0, 1.0)))
    }

    /** 1-nuqtadan 2-nuqtaga katta doira bo'yicha boshlang'ich yo'nalish (bearing), gradusda, [0, 360) oralig'ida. */
    fun bearingDeg(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val p1 = Math.toRadians(lat1)
        val p2 = Math.toRadians(lat2)
        val dl = Math.toRadians(lon2 - lon1)
        val y = sin(dl) * cos(p2)
        val x = cos(p1) * sin(p2) - sin(p1) * cos(p2) * cos(dl)
        return Angles.norm360(Math.toDegrees(atan2(y, x)))
    }

    /** (lat, lon) dan boshlang'ich [bearingDeg] yo'nalishi bo'yicha [distM] yurilgandan keyin yetiladigan nuqta. */
    fun destination(lat: Double, lon: Double, bearingDeg: Double, distM: Double): LatLon {
        val d = distM / EARTH_RADIUS_M
        val b = Math.toRadians(bearingDeg)
        val p1 = Math.toRadians(lat)
        val l1 = Math.toRadians(lon)
        val p2 = asin(sin(p1) * cos(d) + cos(p1) * sin(d) * cos(b))
        val l2 = l1 + atan2(sin(b) * sin(d) * cos(p1), cos(d) - sin(p1) * sin(p2))
        return LatLon(Math.toDegrees(p2), Angles.wrap180(Math.toDegrees(l2)))
    }
}

object Angles {
    /** [0, 360) oralig'iga normallashtiradi. */
    fun norm360(deg: Double): Double {
        val r = deg - 360.0 * floor(deg / 360.0)
        return if (r >= 360.0) 0.0 else r
    }

    /** [-180, 180) oralig'iga normallashtiradi. */
    fun wrap180(deg: Double): Double = norm360(deg + 180.0) - 180.0

    /** a − b ning [-180, 180) oralig'idagi ishorali eng kichik farqi. */
    fun diff(a: Double, b: Double): Double = wrap180(a - b)
}
