package uz.sectorverify.location

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Looper
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import uz.sectorverify.model.GnssFix

/**
 * §7 GnssCollector: LocationManager.GPS_PROVIDER, 1000 ms, 0 m. No Play Services (works offline, no fused/network location).
 * Requires ACCESS_FINE_LOCATION.
 */
class GnssCollector(private val context: Context, private val intervalMs: Long = DEFAULT_INTERVAL_MS) {
    @SuppressLint("MissingPermission")
    fun fixes(): Flow<GnssFix> = callbackFlow {
        val lm = context.getSystemService(LocationManager::class.java)
        val listener = LocationListener { trySend(LocationMapper.toFix(it)) }
        lm.requestLocationUpdates(LocationManager.GPS_PROVIDER, intervalMs, 0f, listener, Looper.getMainLooper())
        awaitClose { lm.removeUpdates(listener) }
    }

    fun isGpsEnabled(): Boolean = context.getSystemService(LocationManager::class.java).isProviderEnabled(LocationManager.GPS_PROVIDER)

    companion object {
        const val DEFAULT_INTERVAL_MS = 1000L
    }
}

object LocationMapper {
    /** Accuracy reported when the provider gives none: always rejected by the cleaner (§6.1.4). */
    const val UNKNOWN_ACCURACY_M = 999.0

    fun toFix(l: Location): GnssFix = GnssFix(
        tNanos = l.elapsedRealtimeNanos,
        utcMs = l.time,
        lat = l.latitude,
        lon = l.longitude,
        accM = if (l.hasAccuracy()) l.accuracy.toDouble() else UNKNOWN_ACCURACY_M,
        speedMps = if (l.hasSpeed()) l.speed.toDouble() else null,
        bearingDeg = if (l.hasBearing()) l.bearing.toDouble() else null,
    )
}
