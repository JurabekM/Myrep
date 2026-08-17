package com.agrovision.app.core.math

import kotlin.math.abs
import kotlin.math.roundToInt
import kotlin.math.sqrt

/**
 * Vaqt qatorlari va statistika — desktop `analytics/timeseries.py` (numpy)
 * faylining sof-Kotlin ko'chirmasi. Barcha funksiyalar bo'sh/qisqa qatorlarda
 * ham xavfsiz (crash bermaydi).
 */
object Stats {

    /** Ortacha; bo'sh ro'yxatda 0. */
    fun mean(values: List<Double>): Double = if (values.isEmpty()) 0.0 else values.sum() / values.size

    fun std(values: List<Double>): Double {
        if (values.size < 2) return 0.0
        val m = mean(values)
        return sqrt(values.sumOf { (it - m) * (it - m) } / values.size)
    }

    /** Ortacha harakatlanuvchi (trailing) — desktop `moving_average`. */
    fun movingAverage(values: List<Double>, window: Int = 3): List<Double> =
        values.indices.map { i -> mean(values.subList(maxOf(0, i - window + 1), i + 1)) }

    /** Eng kichik kvadratlar: y = slope*x + intercept. */
    fun leastSquares(y: List<Double>): Pair<Double, Double> {
        if (y.size < 2) return 0.0 to (y.firstOrNull() ?: 0.0)
        val n = y.size
        val xMean = (n - 1) / 2.0
        val yMean = mean(y)
        var num = 0.0
        var den = 0.0
        for (i in 0 until n) {
            num += (i - xMean) * (y[i] - yMean)
            den += (i - xMean) * (i - xMean)
        }
        val slope = if (abs(den) < 1e-12) 0.0 else num / den
        return slope to (yMean - slope * xMean)
    }

    fun trendSlope(values: List<Double>): Double = leastSquares(values).first

    data class Forecast(val point: List<Double>, val lower: List<Double>, val upper: List<Double>)

    /**
     * Chiziqli trend prognozi + ~95% ishonch oralig'i. Desktop `linear_forecast`
     * bilan bir xil: band = 1.96·σ·sqrt(1 + (x−x̄)²/Σ(x−x̄)²).
     */
    fun linearForecast(values: List<Double>, periods: Int = 1): Forecast {
        if (values.isEmpty() || periods <= 0) return Forecast(emptyList(), emptyList(), emptyList())
        if (values.size == 1) {
            val flat = List(periods) { values[0] }
            return Forecast(flat, flat, flat)
        }
        val n = values.size
        val (slope, intercept) = leastSquares(values)
        val residuals = values.indices.map { values[it] - (slope * it + intercept) }
        val residualStd = sqrt(residuals.sumOf { it * it } / n)
        val xMean = (n - 1) / 2.0
        val sumSq = (0 until n).sumOf { (it - xMean) * (it - xMean) }.let { if (it < 1e-9) 1e-9 else it }

        val point = ArrayList<Double>(periods)
        val lower = ArrayList<Double>(periods)
        val upper = ArrayList<Double>(periods)
        for (i in 0 until periods) {
            val x = (n + i).toDouble()
            val value = slope * x + intercept
            val band = 1.96 * residualStd * sqrt(1 + (x - xMean) * (x - xMean) / sumSq)
            point += value
            lower += value - band
            upper += value + band
        }
        return Forecast(point, lower, upper)
    }

    /**
     * Trend + multiplikativ mavsumiy indeks prognozi (klassik dekompozitsiya) —
     * desktop `seasonal_forecast`. Ma'lumot 2 mavsumdan kam bo'lsa chiziqliga o'tadi.
     */
    fun seasonalForecast(values: List<Double>, seasonLength: Int = 12, periods: Int = 12): Forecast {
        if (values.size < seasonLength * 2) return linearForecast(values, periods)
        val n = values.size
        val (slope, intercept) = leastSquares(values)
        val trend = (0 until n).map { slope * it + intercept }
        val ratio = values.indices.map { values[it] / (if (abs(trend[it]) < 1e-9) 1e-9 else trend[it]) }
        val seasonal = (0 until seasonLength).map { s ->
            mean((s until n step seasonLength).map { ratio[it] })
        }
        val residuals = values.indices.map { values[it] - trend[it] * seasonal[it % seasonLength] }
        val residualStd = sqrt(residuals.sumOf { it * it } / n)

        val point = ArrayList<Double>(periods)
        val lower = ArrayList<Double>(periods)
        val upper = ArrayList<Double>(periods)
        for (i in 0 until periods) {
            val x = n + i
            val value = (slope * x + intercept) * seasonal[x % seasonLength]
            point += value
            lower += value - 1.96 * residualStd
            upper += value + 1.96 * residualStd
        }
        return Forecast(point, lower, upper)
    }

    /** |z| > threshold bo'lgan indekslar — desktop `zscore_anomalies`. */
    fun zscoreAnomalies(values: List<Double>, threshold: Double = 2.0): List<Int> {
        if (values.size < 3) return emptyList()
        val m = mean(values)
        val s = std(values)
        if (s < 1e-12) return emptyList()
        return values.indices.filter { abs((values[it] - m) / s) > threshold }
    }

    /** Xavfsiz foiz o'zgarish — desktop `percent_change`. */
    fun percentChange(previous: Double, current: Double): Double {
        if (abs(previous) < 1e-12) return 0.0
        return ((current - previous) / abs(previous) * 100 * 10).roundToInt() / 10.0
    }

    /** Pearson korrelyatsiya koeffitsienti. */
    fun correlation(x: List<Double>, y: List<Double>): Double {
        if (x.size != y.size || x.size < 3) return 0.0
        val mx = mean(x)
        val my = mean(y)
        var num = 0.0
        var dx = 0.0
        var dy = 0.0
        for (i in x.indices) {
            num += (x[i] - mx) * (y[i] - my)
            dx += (x[i] - mx) * (x[i] - mx)
            dy += (y[i] - my) * (y[i] - my)
        }
        val denom = sqrt(dx * dy)
        return if (denom < 1e-12) 0.0 else (num / denom * 1000).roundToInt() / 1000.0
    }
}

/**
 * K-Means klasterizatsiya (k-means++ initsializatsiya bilan) — desktop
 * analitika sahifasidagi `sklearn.cluster.KMeans` ekvivalenti.
 */
object KMeans {

    data class Result(val labels: IntArray, val centroids: Array<DoubleArray>)

    fun fit(data: Array<DoubleArray>, k: Int, seed: Long = 42, maxIter: Int = 100): Result {
        require(data.isNotEmpty()) { "K-Means uchun ma'lumot bo'sh" }
        val n = data.size
        val dim = data[0].size
        val clusters = minOf(k, n)
        val random = kotlin.random.Random(seed)

        // k-means++ initsializatsiya
        val centroids = Array(clusters) { DoubleArray(dim) }
        data[random.nextInt(n)].copyInto(centroids[0])
        for (c in 1 until clusters) {
            val distances = DoubleArray(n) { i ->
                (0 until c).minOf { squaredDistance(data[i], centroids[it]) }
            }
            val total = distances.sum()
            var target = random.nextDouble() * (if (total <= 0) 1.0 else total)
            var chosen = n - 1
            for (i in 0 until n) {
                target -= distances[i]
                if (target <= 0) { chosen = i; break }
            }
            data[chosen].copyInto(centroids[c])
        }

        val labels = IntArray(n)
        repeat(maxIter) {
            var changed = false
            for (i in 0 until n) {
                var best = 0
                var bestDist = Double.MAX_VALUE
                for (c in 0 until clusters) {
                    val d = squaredDistance(data[i], centroids[c])
                    if (d < bestDist) { bestDist = d; best = c }
                }
                if (labels[i] != best) { labels[i] = best; changed = true }
            }
            val sums = Array(clusters) { DoubleArray(dim) }
            val counts = IntArray(clusters)
            for (i in 0 until n) {
                counts[labels[i]]++
                for (d in 0 until dim) sums[labels[i]][d] += data[i][d]
            }
            for (c in 0 until clusters) {
                if (counts[c] == 0) continue
                for (d in 0 until dim) centroids[c][d] = sums[c][d] / counts[c]
            }
            if (!changed) return@repeat
        }
        return Result(labels, centroids)
    }

    /** Har bir ustunni z-standartlash (KMeans masshtabga sezgir). */
    fun standardize(data: Array<DoubleArray>): Array<DoubleArray> {
        if (data.isEmpty()) return data
        val dim = data[0].size
        val means = DoubleArray(dim)
        val stds = DoubleArray(dim)
        for (d in 0 until dim) {
            val column = data.map { it[d] }
            means[d] = Stats.mean(column)
            stds[d] = Stats.std(column).let { if (it < 1e-9) 1.0 else it }
        }
        return Array(data.size) { i -> DoubleArray(dim) { d -> (data[i][d] - means[d]) / stds[d] } }
    }

    private fun squaredDistance(a: DoubleArray, b: DoubleArray): Double {
        var sum = 0.0
        for (i in a.indices) {
            val diff = a[i] - b[i]
            sum += diff * diff
        }
        return sum
    }
}
