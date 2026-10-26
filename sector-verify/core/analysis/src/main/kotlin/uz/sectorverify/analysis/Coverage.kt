package uz.sectorverify.analysis

import kotlin.math.abs
import kotlin.math.roundToInt
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellKey

data class SectorCoverage(val fraction: Double, val windowBins: List<Int>, val missingBins: List<Int>)

/** §6.6 overall and per-sector coverage from per-cell bin counts. */
class CoverageCalculator(private val config: AnalysisConfig) {
    private val binner = Binner(config)
    private val windowSize = (2 * config.sectorHalfWidthDeg / config.binDeg).roundToInt().coerceIn(1, config.nBins)

    /** A bin is covered when any of [keys] has ≥ minSamplesPerCoverageBin samples in it. */
    fun coveredBins(counts: Map<CellKey, IntArray>, keys: Collection<CellKey>): BooleanArray {
        val covered = BooleanArray(config.nBins)
        for (k in keys) {
            val c = counts[k] ?: continue
            for (i in c.indices) if (c[i] >= config.minSamplesPerCoverageBin) covered[i] = true
        }
        return covered
    }

    fun fraction(covered: BooleanArray): Double = covered.count { it }.toDouble() / covered.size

    /** The 18 bins whose centres are nearest to plan azimuth (plan ± 90°). */
    fun window(planAzimuthDeg: Double): List<Int> = (0 until config.nBins)
        .sortedWith(compareBy({ abs(Angles.diff(binner.center(it), planAzimuthDeg)) }, { it }))
        .take(windowSize)
        .sorted()

    fun sector(planAzimuthDeg: Double, covered: BooleanArray): SectorCoverage {
        val w = window(planAzimuthDeg)
        val missing = w.filterNot { covered[it] }
        return SectorCoverage((w.size - missing.size).toDouble() / w.size, w, missing)
    }
}
