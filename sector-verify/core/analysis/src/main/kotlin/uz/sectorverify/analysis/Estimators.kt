package uz.sectorverify.analysis

import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.random.Random
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.AzimuthEstimate

data class PatternFit(val alphaDeg: Double, val p0: Double, val cost: Double, val rmseDb: Double)

/** §6.3 A usuli: A(Δ) = −min(c·(Δ/θ)², Am) ni α ning 1° li to'rida vaznli eng kichik kvadratlar usuli bilan moslash. */
class PatternFitter(private val config: AnalysisConfig) {
    private val steps = (AnalysisConfig.FULL_CIRCLE / config.alphaStepDeg).roundToInt()

    fun pattern(deltaDeg: Double, hpbwDeg: Double): Double {
        val r = Angles.wrap180(deltaDeg) / hpbwDeg
        return -min(config.patternCoef * r * r, config.patternMaxAttDb)
    }

    fun fit(bins: List<Bin>, hpbwDeg: Double): PatternFit {
        require(bins.isNotEmpty())
        val w = DoubleArray(bins.size) { sqrt(bins[it].count.toDouble()) }
        val y = DoubleArray(bins.size) { bins[it].median }
        val phi = DoubleArray(bins.size) { bins[it].centerDeg }
        val sw = w.sum()
        val a = DoubleArray(bins.size)
        var best = PatternFit(0.0, 0.0, Double.POSITIVE_INFINITY, 0.0)
        for (k in 0 until steps) {
            val alpha = k * config.alphaStepDeg
            var num = 0.0
            for (i in bins.indices) {
                a[i] = pattern(phi[i] - alpha, hpbwDeg)
                num += w[i] * (y[i] - a[i])
            }
            val p0 = num / sw
            var j = 0.0
            for (i in bins.indices) {
                val r = y[i] - p0 - a[i]
                j += w[i] * r * r
            }
            if (j < best.cost) best = PatternFit(alpha, p0, j, 0.0)
        }
        return best.copy(rmseDb = sqrt(best.cost / sw))
    }
}

/** §6.5 B usuli: α_B = atan2(Σ p·sin φ, Σ p·cos φ), p = 10^(ȳ/10). */
object CentroidEstimator {
    fun estimate(bins: List<Bin>): Double {
        val ref = bins.maxOf { it.median } // 10^(-ref/10) ga masshtablash burchakni o'zgartirmaydi, underflow'ning oldini oladi
        var sx = 0.0
        var sy = 0.0
        for (b in bins) {
            val p = 10.0.pow((b.median - ref) / 10.0)
            val r = Math.toRadians(b.centerDeg)
            sx += p * cos(r)
            sy += p * sin(r)
        }
        return Angles.norm360(Math.toDegrees(atan2(sy, sx)))
    }
}

data class BootstrapCi(val lowOffsetDeg: Double, val highOffsetDeg: Double) {
    val halfDeg: Double get() = max(abs(lowOffsetDeg), abs(highOffsetDeg))
}

/** §6.4: binlar qaytariladigan tanlov bilan qayta tanlanadi, qayta moslanadi, α̂ dan og'ishlarning persentillari olinadi. */
class Bootstrap(private val config: AnalysisConfig, private val fitter: PatternFitter) {
    fun ci(bins: List<Bin>, hpbwDeg: Double, alphaHat: Double, iterations: Int, random: Random): BootstrapCi {
        if (iterations <= 0) return BootstrapCi(0.0, 0.0)
        val offsets = DoubleArray(iterations) {
            val sample = List(bins.size) { bins[random.nextInt(bins.size)] }
            Angles.diff(fitter.fit(sample, hpbwDeg).alphaDeg, alphaHat)
        }
        offsets.sort()
        return BootstrapCi(percentile(offsets, config.ciLowPercentile), percentile(offsets, config.ciHighPercentile))
    }

    companion object {
        /** Tartib statistikalari orasida chiziqli interpolyatsiya (R type 7). [sorted] o'sish tartibida bo'lishi shart. */
        fun percentile(sorted: DoubleArray, pct: Double): Double {
            require(sorted.isNotEmpty())
            val h = (sorted.size - 1) * pct / 100.0
            val lo = floor(h).toInt()
            val hi = ceil(h).toInt()
            return sorted[lo] + (h - lo) * (sorted[hi] - sorted[lo])
        }
    }
}

/** A va B usullarini hamda bootstrap'ni bitta [AzimuthEstimate] ga birlashtiradi. */
class AzimuthEstimator(private val config: AnalysisConfig) {
    val fitter = PatternFitter(config)
    private val bootstrap = Bootstrap(config, fitter)

    /** Binlar minBinsForFit dan kam bo'lsa null. */
    fun estimate(bins: List<Bin>, hpbwDeg: Double, iterations: Int, random: Random): AzimuthEstimate? {
        if (bins.size < config.minBinsForFit) return null
        val fit = fitter.fit(bins, hpbwDeg)
        val ci = bootstrap.ci(bins, hpbwDeg, fit.alphaDeg, iterations, random)
        val alphaB = CentroidEstimator.estimate(bins)
        return AzimuthEstimate(
            alphaDeg = fit.alphaDeg,
            ciLowDeg = Angles.norm360(fit.alphaDeg + ci.lowOffsetDeg),
            ciHighDeg = Angles.norm360(fit.alphaDeg + ci.highOffsetDeg),
            ciHalfDeg = ci.halfDeg,
            alphaBDeg = alphaB,
            rmseDb = fit.rmseDb,
            nSamples = bins.sumOf { it.count },
            nBins = bins.size,
            unreliable = abs(Angles.diff(fit.alphaDeg, alphaB)) > config.unreliableDiffDeg,
        )
    }
}
