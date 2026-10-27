package uz.sectorverify.analysis

import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellKey

/** ARFCN'dagi bitta baholangan sektor — swap aniqlashga kirish ma'lumoti. */
data class SwapEntry(val key: CellKey, val label: String, val planAzimuthDeg: Double, val estimateDeg: Double)

/** [mapping]: yacheyka → u haqiqatda nurlanadigan sektor yorlig'i (faqat yorlig'i o'zgargan yacheykalar). */
data class SwapResult(val mapping: Map<CellKey, String>, val costIdentity: Double, val costBest: Double)

/** §6.7: barcha o'rin almashtirishlar orasidan baholarni rejadagi azimutlarga eng yaxshi moslash. */
class SwapDetector(private val config: AnalysisConfig) {

    fun detect(entries: List<SwapEntry>): SwapResult? {
        if (entries.size < 2 || entries.size > config.swapMaxSectors) return null
        val n = entries.size
        val err = Array(n) { k -> DoubleArray(n) { j -> Angles.diff(entries[k].estimateDeg, entries[j].planAzimuthDeg) } }
        val identity = IntArray(n) { it }
        val costId = cost(err, identity)
        var best = identity
        var bestCost = costId
        permutations(n) { p ->
            val c = cost(err, p)
            if (c < bestCost) {
                bestCost = c
                best = p.copyOf()
            }
        }
        val isIdentity = best.indices.all { best[it] == it }
        if (isIdentity) return null
        val withinErr = (0 until n).all { k -> kotlin.math.abs(err[k][best[k]]) <= config.swapMaxErrDeg }
        val gain = costId >= config.swapGainFactor * bestCost + config.swapGainOffset
        if (!withinErr || !gain) return null
        val mapping = (0 until n)
            .filter { entries[best[it]].label != entries[it].label }
            .associate { entries[it].key to entries[best[it]].label }
        if (mapping.isEmpty()) return null
        return SwapResult(mapping, costId, bestCost)
    }

    private fun cost(err: Array<DoubleArray>, p: IntArray): Double {
        var c = 0.0
        for (k in p.indices) c += err[k][p[k]] * err[k][p[k]]
        return c
    }

    /** Heap algoritmi; [visit] umumiy buferni oladi. */
    private fun permutations(n: Int, visit: (IntArray) -> Unit) {
        val a = IntArray(n) { it }
        val c = IntArray(n)
        visit(a)
        var i = 0
        while (i < n) {
            if (c[i] < i) {
                if (i % 2 == 0) a.swap(0, i) else a.swap(c[i], i)
                visit(a)
                c[i]++
                i = 0
            } else {
                c[i] = 0
                i++
            }
        }
    }

    private fun IntArray.swap(x: Int, y: Int) {
        val t = this[x]
        this[x] = this[y]
        this[y] = t
    }
}
