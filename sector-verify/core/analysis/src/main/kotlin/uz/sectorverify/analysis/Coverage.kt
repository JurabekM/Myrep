package uz.sectorverify.analysis

import kotlin.math.abs
import kotlin.math.roundToInt
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellKey

data class SectorCoverage(val fraction: Double, val windowBins: List<Int>, val missingBins: List<Int>)

/** §6.6 umumiy va sektorlar bo'yicha qamrov — har yacheyka bin sanoqlaridan. */
class CoverageCalculator(private val config: AnalysisConfig) {
    private val binner = Binner(config)
    private val windowSize = (2 * config.sectorHalfWidthDeg / config.binDeg).roundToInt().coerceIn(1, config.nBins)

    /** [keys] dan istalgan birining binda ≥ minSamplesPerCoverageBin namunasi bo'lsa, bin qamralgan hisoblanadi. */
    fun coveredBins(counts: Map<CellKey, IntArray>, keys: Collection<CellKey>): BooleanArray {
        val covered = BooleanArray(config.nBins)
        for (k in keys) {
            val c = counts[k] ?: continue
            for (i in c.indices) if (c[i] >= config.minSamplesPerCoverageBin) covered[i] = true
        }
        return covered
    }

    fun fraction(covered: BooleanArray): Double = covered.count { it }.toDouble() / covered.size

    /** Markazlari plan azimutiga eng yaqin 18 ta bin (plan ± 90°). */
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
