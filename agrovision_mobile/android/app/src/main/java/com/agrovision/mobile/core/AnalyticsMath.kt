package com.agrovision.mobile.core

import kotlin.math.abs
import kotlin.math.sqrt

/** Vaqt qatorlari uchun sof-Kotlin matematik yordamchilar (desktop analytics/timeseries.py porti). */
object AnalyticsMath {

    fun trendSlope(values: List<Double>): Double {
        if (values.size < 2) return 0.0
        val x = values.indices.map { it.toDouble() }
        val (slope, _) = leastSquares(x, values)
        return slope
    }

    /** Chiziqli trend prognozi + ~95% ishonch oralig'i (qoldiq standart og'ishi asosida). */
    fun linearForecast(values: List<Double>, periods: Int): Triple<List<Double>, List<Double>, List<Double>> {
        if (values.isEmpty()) return Triple(emptyList(), emptyList(), emptyList())
        if (values.size == 1) {
            val flat = List(periods) { values[0] }
            return Triple(flat, flat, flat)
        }
        val x = values.indices.map { it.toDouble() }
        val (slope, intercept) = leastSquares(x, values)
        val residuals = x.indices.map { values[it] - (slope * x[it] + intercept) }
        val residualStd = sqrt(residuals.sumOf { it * it } / residuals.size)
        val xMean = x.average()
        val sumSqX = x.sumOf { (it - xMean) * (it - xMean) }.let { if (it < 1e-9) 1e-9 else it }

        val forecast = mutableListOf<Double>()
        val lower = mutableListOf<Double>()
        val upper = mutableListOf<Double>()
        for (i in 0 until periods) {
            val fx = (values.size + i).toDouble()
            val point = slope * fx + intercept
            val band = 1.96 * residualStd * sqrt(1 + (fx - xMean) * (fx - xMean) / sumSqX)
            forecast += point
            lower += point - band
            upper += point + band
        }
        return Triple(forecast, lower, upper)
    }

    fun percentChange(previous: Double, current: Double): Double {
        if (abs(previous) < 1e-12) return 0.0
        return ((current - previous) / abs(previous) * 100 * 10).let { Math.round(it) / 10.0 }
    }

    fun correlation(x: List<Double>, y: List<Double>): Double {
        if (x.size != y.size || x.size < 3) return 0.0
        val mx = x.average()
        val my = y.average()
        var num = 0.0
        var dx = 0.0
        var dy = 0.0
        for (i in x.indices) {
            num += (x[i] - mx) * (y[i] - my)
            dx += (x[i] - mx) * (x[i] - mx)
            dy += (y[i] - my) * (y[i] - my)
        }
        val denom = sqrt(dx * dy)
        return if (denom < 1e-12) 0.0 else num / denom
    }

    /** Oddiy eng kichik kvadratlar (y = slope*x + intercept) bitta o'zgaruvchi uchun. */
    private fun leastSquares(x: List<Double>, y: List<Double>): Pair<Double, Double> {
        val n = x.size
        val xMean = x.average()
        val yMean = y.average()
        var num = 0.0
        var den = 0.0
        for (i in 0 until n) {
            num += (x[i] - xMean) * (y[i] - yMean)
            den += (x[i] - xMean) * (x[i] - xMean)
        }
        val slope = if (den < 1e-12) 0.0 else num / den
        val intercept = yMean - slope * xMean
        return slope to intercept
    }
}

/**
 * Ko'p o'zgaruvchili chiziqli regressiya — normal tenglamalar usuli
 * ((X^T X)^-1 X^T y), Gauss-Jordan bilan matritsa teskarilash.
 * Bu qurilma ichida (offline) haqiqiy o'qitilgan model — sklearn emas,
 * lekin xuddi shu matematik tamoyil (eng kichik kvadratlar regressiyasi).
 */
object LinearRegression {

    /** @return (koeffitsientlar: [intercept, b1..bn], R^2) */
    fun fit(features: List<DoubleArray>, targets: List<Double>): Pair<DoubleArray, Double> {
        val n = features.size
        val p = features[0].size + 1 // +intercept
        // X^T X va X^T y qurish
        val xtx = Array(p) { DoubleArray(p) }
        val xty = DoubleArray(p)
        for (row in 0 until n) {
            val xi = DoubleArray(p)
            xi[0] = 1.0
            for (j in features[row].indices) xi[j + 1] = features[row][j]
            for (a in 0 until p) {
                xty[a] += xi[a] * targets[row]
                for (b in 0 until p) xtx[a][b] += xi[a] * xi[b]
            }
        }
        // Regularizatsiya (kichik diagonal qo'shish) — singular matritsani oldini oladi
        for (i in 0 until p) xtx[i][i] += 1e-6

        val coefficients = solve(xtx, xty)

        // R^2 hisoblash
        val yMean = targets.average()
        var ssTot = 0.0
        var ssRes = 0.0
        for (row in 0 until n) {
            val xi = DoubleArray(p)
            xi[0] = 1.0
            for (j in features[row].indices) xi[j + 1] = features[row][j]
            var pred = 0.0
            for (a in 0 until p) pred += coefficients[a] * xi[a]
            ssRes += (targets[row] - pred) * (targets[row] - pred)
            ssTot += (targets[row] - yMean) * (targets[row] - yMean)
        }
        val rSquared = if (ssTot < 1e-9) 1.0 else 1.0 - ssRes / ssTot
        return coefficients to rSquared
    }

    fun predict(coefficients: DoubleArray, features: DoubleArray): Double {
        var result = coefficients[0]
        for (i in features.indices) result += coefficients[i + 1] * features[i]
        return result
    }

    /** Gauss-Jordan elimination bilan Ax=b yechish. */
    private fun solve(a: Array<DoubleArray>, b: DoubleArray): DoubleArray {
        val n = b.size
        val m = Array(n) { i -> DoubleArray(n + 1) { j -> if (j < n) a[i][j] else b[i] } }
        for (col in 0 until n) {
            var pivot = col
            for (row in col + 1 until n) if (abs(m[row][col]) > abs(m[pivot][col])) pivot = row
            val tmp = m[col]; m[col] = m[pivot]; m[pivot] = tmp
            val pivotVal = if (abs(m[col][col]) < 1e-12) 1e-12 else m[col][col]
            for (j in col..n) m[col][j] /= pivotVal
            for (row in 0 until n) {
                if (row == col) continue
                val factor = m[row][col]
                for (j in col..n) m[row][j] -= factor * m[col][j]
            }
        }
        return DoubleArray(n) { m[it][n] }
    }
}
