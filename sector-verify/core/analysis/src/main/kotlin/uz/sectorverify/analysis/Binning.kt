package uz.sectorverify.analysis

import kotlin.math.floor
import uz.sectorverify.model.AnalysisConfig

/** Bitta yacheykaning bitta azimut bini: [centerDeg] = (index + 0.5)·binDeg, [median] — y medianasi, [count] — namunalar soni. */
data class Bin(val index: Int, val centerDeg: Double, val median: Double, val count: Int)

/** §6.2: har yacheyka uchun 10° li binlar, bin qiymati = y medianasi, namunalari minPerBin dan kam binlar tashlanadi. */
class Binner(private val config: AnalysisConfig) {
    private val nBins = config.nBins

    fun index(bearingDeg: Double): Int = floor(Angles.norm360(bearingDeg) / config.binDeg).toInt().coerceIn(0, nBins - 1)

    fun center(index: Int): Double = (index + 0.5) * config.binDeg

    fun counts(samples: List<CleanSample>): IntArray {
        val c = IntArray(nBins)
        for (s in samples) c[index(s.bearingDeg)]++
        return c
    }

    fun bins(samples: List<CleanSample>): List<Bin> {
        val values = Array(nBins) { ArrayList<Double>() }
        for (s in samples) values[index(s.bearingDeg)] += s.y
        return values.withIndex()
            .filter { it.value.size >= config.minPerBin }
            .map { (i, v) -> Bin(i, center(i), median(v), v.size) }
    }

    companion object {
        fun median(values: List<Double>): Double {
            require(values.isNotEmpty())
            val s = values.sorted()
            val m = s.size / 2
            return if (s.size % 2 == 1) s[m] else (s[m - 1] + s[m]) / 2.0
        }
    }
}
