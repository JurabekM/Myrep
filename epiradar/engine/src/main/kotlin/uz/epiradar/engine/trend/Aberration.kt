package uz.epiradar.engine.trend

import kotlin.math.max
import kotlin.math.sqrt

/**
 * Epidemiologik «g'ayritabiiy o'sish» (aberration) aniqlash algoritmlari.
 *
 * - **EARS C2** (CDC Early Aberration Reporting System): joriy qiymatni 2 haftalik tanaffusdan
 *   oldingi 7 haftalik bazaga solishtiradi. `C2 = (x − μ) / σ`, signal: C2 ≥ 3.
 * - **Tarixiy chegaralar** (Stroup va boshq., 1989): joriy qiymatni o'tgan yillarning shu
 *   davridagi qiymatlariga solishtiradi; chegara `μ + 2σ`. Mavsumiy kasalliklar (gripp) uchun
 *   har qishda «yolg'on signal» bermaslik shu usul bilan ta'minlanadi.
 */
object Aberration {
    data class Result(
        val statistic: Double,
        val mean: Double,
        val threshold: Double,
        val alarm: Boolean,
    )

    const val C2_THRESHOLD = 3.0
    private const val C2_BASELINE = 7
    private const val C2_GUARD = 2

    /**
     * EARS C2. `series` — vaqt bo'yicha qiymatlar (null — ma'lumot yo'q), `t` — tekshiriladigan indeks.
     * `minSigma` — juda barqaror baza (σ≈0) bo'lganda mayda tebranishni signal deb olmaslik uchun.
     */
    fun earsC2(
        series: List<Double?>,
        t: Int,
        minSigma: Double = 1.0,
    ): Result? {
        val x = series.getOrNull(t) ?: return null
        val from = t - C2_GUARD - C2_BASELINE
        val to = t - C2_GUARD - 1
        if (from < 0) return null
        val base = (from..to).mapNotNull { series[it] }
        if (base.size < 4) return null
        val mean = base.average()
        val sigma = max(stdDev(base, mean), max(minSigma, 0.2 * mean))
        val c2 = (x - mean) / sigma
        return Result(c2, mean, mean + C2_THRESHOLD * sigma, c2 >= C2_THRESHOLD)
    }

    /** Tarixiy chegara: `baseline` — o'tgan yillarning shu (±2 hafta) davridagi qiymatlari. */
    fun historicalLimit(
        x: Double,
        baseline: List<Double>,
        minSigma: Double = 1.0,
    ): Result? {
        if (baseline.size < 5) return null
        val mean = baseline.average()
        val sigma = max(stdDev(baseline, mean), minSigma)
        val threshold = mean + 2 * sigma
        return Result((x - mean) / sigma, mean, threshold, x > threshold)
    }

    fun stdDev(
        values: List<Double>,
        mean: Double = values.average(),
    ): Double {
        if (values.size < 2) return 0.0
        return sqrt(values.sumOf { (it - mean) * (it - mean) } / (values.size - 1))
    }
}
