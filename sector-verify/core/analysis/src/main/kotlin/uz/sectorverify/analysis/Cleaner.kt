package uz.sectorverify.analysis

import kotlin.math.abs
import kotlin.math.log10
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.CleaningStats
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat

/** A sample that survived cleaning (§6.1), located relative to the site and path-loss normalised (§6.2). */
data class CleanSample(
    val key: CellKey,
    val tNanos: Long,
    val distanceM: Double,
    val bearingDeg: Double,
    val rsrp: Double,
    val y: Double,
    val registered: Boolean,
)

data class CleaningResult(val samples: List<CleanSample>, val stats: CleaningStats)

/** §6.1 cleaning: rsrp, age, GNSS interpolation and quality, distance window and LTE TA filter. */
class Cleaner(private val config: AnalysisConfig) {

    fun clean(siteLat: Double, siteLon: Double, samples: List<CellSample>, fixes: List<GnssFix>): CleaningResult {
        val good = fixes
            .filter { f -> f.accM <= config.maxAccuracyM && (f.speedMps?.let { it <= config.maxSpeedMps } ?: true) }
            .sortedBy { it.tNanos }
        val times = LongArray(good.size) { good[it].tNanos }
        val rejected = IntArray(Reject.entries.size)
        val kept = ArrayList<CleanSample>(samples.size)
        for (s in samples) {
            when (val r = classify(s, siteLat, siteLon, good, times)) {
                is CleanSample -> kept += r
                is Reject -> rejected[r.ordinal]++
            }
        }
        val stats = CleaningStats(
            total = samples.size,
            noRsrp = rejected[Reject.NO_RSRP.ordinal],
            stale = rejected[Reject.STALE.ordinal],
            noFix = rejected[Reject.NO_FIX.ordinal],
            outOfRange = rejected[Reject.OUT_OF_RANGE.ordinal],
            taMismatch = rejected[Reject.TA_MISMATCH.ordinal],
            kept = kept.size,
        )
        return CleaningResult(kept, stats)
    }

    private enum class Reject { NO_RSRP, STALE, NO_FIX, OUT_OF_RANGE, TA_MISMATCH }

    /** Returns the [CleanSample] or the first [Reject] reason, in the order of §6.1. */
    private fun classify(s: CellSample, siteLat: Double, siteLon: Double, fixes: List<GnssFix>, times: LongArray): Any {
        val rsrp = s.rsrp ?: return Reject.NO_RSRP
        val rx = s.rxNanos
        val pos = interpolate(fixes, times, s.tNanos)
        val d = pos?.let { Geo.distanceM(siteLat, siteLon, it.lat, it.lon) }
        val ta = s.ta
        return when {
            rx != null && (rx - s.tNanos) / NANOS_PER_MS > config.maxSampleAgeMs -> Reject.STALE
            pos == null || d == null -> Reject.NO_FIX
            d < config.rMinM || d > config.rMaxM -> Reject.OUT_OF_RANGE
            s.rat == Rat.LTE && ta != null && abs(ta * config.taStepM - d) > config.taToleranceSteps * config.taStepM ->
                Reject.TA_MISMATCH
            else -> CleanSample(
                s.key,
                s.tNanos,
                d,
                Geo.bearingDeg(siteLat, siteLon, pos.lat, pos.lon),
                rsrp,
                normalise(rsrp, d),
                s.registered,
            )
        }
    }

    /** y = rsrp + 10·n·log10(d / dRef). */
    fun normalise(rsrp: Double, distanceM: Double): Double =
        rsrp + 10.0 * config.pathLossExponent * log10(distanceM / config.dRefM)

    /** Linear interpolation between the neighbouring fixes; null when the nearest fix is too far in time. */
    internal fun interpolate(fixes: List<GnssFix>, times: LongArray, t: Long): LatLon? {
        if (fixes.isEmpty()) return null
        val maxGapNanos = config.maxFixGapMs * NANOS_PER_MS
        val idx = times.binarySearch(t)
        if (idx >= 0) return LatLon(fixes[idx].lat, fixes[idx].lon)
        val next = -idx - 1
        val prev = next - 1
        val before = fixes.getOrNull(prev)
        val after = fixes.getOrNull(next)
        val gapBefore = before?.let { t - it.tNanos } ?: Long.MAX_VALUE
        val gapAfter = after?.let { it.tNanos - t } ?: Long.MAX_VALUE
        if (minOf(gapBefore, gapAfter) > maxGapNanos) return null
        if (before == null || after == null) {
            val only = before ?: after!!
            return LatLon(only.lat, only.lon)
        }
        val f = (t - before.tNanos).toDouble() / (after.tNanos - before.tNanos).toDouble()
        return LatLon(before.lat + f * (after.lat - before.lat), before.lon + f * (after.lon - before.lon))
    }

    private companion object {
        const val NANOS_PER_MS = 1_000_000L
    }
}
