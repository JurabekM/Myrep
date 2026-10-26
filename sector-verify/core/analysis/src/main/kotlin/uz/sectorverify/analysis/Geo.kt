package uz.sectorverify.analysis

import kotlin.math.asin
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.sin
import kotlin.math.sqrt

data class LatLon(val lat: Double, val lon: Double)

/** Spherical-earth geodesy; good to well below 1 m over the 0–2 km a survey covers. */
object Geo {
    const val EARTH_RADIUS_M = 6_371_008.8

    /** Haversine distance in metres. */
    fun distanceM(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val p1 = Math.toRadians(lat1)
        val p2 = Math.toRadians(lat2)
        val dp = p2 - p1
        val dl = Math.toRadians(lon2 - lon1)
        val h = sin(dp / 2).let { it * it } + cos(p1) * cos(p2) * sin(dl / 2).let { it * it }
        return 2 * EARTH_RADIUS_M * asin(sqrt(h.coerceIn(0.0, 1.0)))
    }

    /** Great-circle initial bearing from point 1 to point 2, degrees in [0, 360). */
    fun bearingDeg(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val p1 = Math.toRadians(lat1)
        val p2 = Math.toRadians(lat2)
        val dl = Math.toRadians(lon2 - lon1)
        val y = sin(dl) * cos(p2)
        val x = cos(p1) * sin(p2) - sin(p1) * cos(p2) * cos(dl)
        return Angles.norm360(Math.toDegrees(atan2(y, x)))
    }

    /** Point reached from (lat, lon) after [distM] along initial [bearingDeg]. */
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
    /** Normalises to [0, 360). */
    fun norm360(deg: Double): Double {
        val r = deg - 360.0 * floor(deg / 360.0)
        return if (r >= 360.0) 0.0 else r
    }

    /** Normalises to [-180, 180). */
    fun wrap180(deg: Double): Double = norm360(deg + 180.0) - 180.0

    /** Signed smallest difference a − b in [-180, 180). */
    fun diff(a: Double, b: Double): Double = wrap180(a - b)
}
