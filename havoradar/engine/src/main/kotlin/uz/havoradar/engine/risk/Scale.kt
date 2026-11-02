package uz.havoradar.engine.risk

import java.util.Locale
import kotlin.math.roundToInt

/** Bo'lakli-chiziqli shkala: o'lchov qiymati → 0..100 ball. Har bir tayanch nuqta hujjatlashtirilgan (README). */
class Scale(
    private vararg val anchors: Pair<Double, Double>,
) {
    init {
        require(anchors.size >= 2 && anchors.toList().zipWithNext().all { (a, b) -> b.first > a.first })
    }

    operator fun invoke(x: Double): Double {
        if (x <= anchors.first().first) return anchors.first().second
        for (i in 1 until anchors.size) {
            val (x1, y1) = anchors[i]
            if (x <= x1) {
                val (x0, y0) = anchors[i - 1]
                return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
            }
        }
        return anchors.last().second
    }
}

internal fun Double.score(): Int = roundToInt().coerceIn(0, 100)

/** Sezgir guruhlar uchun ball 25% oshiriladi (chegara ertaroq kesib o'tiladi). */
internal const val SENSITIVE_FACTOR = 1.25

internal fun personalize(
    base: Int,
    sensitive: Boolean,
): Int = if (sensitive) (base * SENSITIVE_FACTOR).score() else base

/** O'zbekcha son: 3.5 → "3,5"; butun bo'lsa kasrsiz. */
internal fun num(
    v: Double,
    decimals: Int = 0,
): String {
    val s = String.format(Locale.ROOT, "%.${decimals}f", v).replace('.', ',')
    return if (decimals > 0 && s.endsWith(",0")) s.dropLast(2) else s
}

internal fun hour(h: Int) = "${h.toString().padStart(2, '0')}:00"
