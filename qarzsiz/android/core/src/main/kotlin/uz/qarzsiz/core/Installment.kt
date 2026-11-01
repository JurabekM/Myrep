package uz.qarzsiz.core

import java.math.BigDecimal
import java.math.MathContext
import java.math.RoundingMode

/**
 * «1000$ lik telefon 3 yilda 2000$» — bo'lib to'lashning haqiqiy narxi.
 * Naqd narx, boshlang'ich to'lov, oylik to'lov va oylar sonidan ortiqcha to'lov va
 * yashirin yillik foiz (annuitet bo'yicha ichki daromad stavkasi) hisoblanadi.
 */
data class InstallmentResult(
    val financed: Long,
    val totalPaid: Long,
    val overpay: Long,
    /** Ortiqcha to'lov naqd narxga nisbatan, bp. */
    val overpayBp: Int,
    /** Yillik nominal foiz (oylik × 12), bp. */
    val nominalAnnualBp: Int,
    /** Yillik samarali foiz ((1+r)^12 − 1), bp. */
    val effectiveAnnualBp: Int,
)

object Installment {
    /** Python oracle bilan bir xil aniqlik va yaxlitlash (`spec/oracle/oracle.py`). */
    private val MC = MathContext(50, RoundingMode.HALF_EVEN)
    private const val ITERATIONS = 120

    fun analyze(cashPrice: Long, downPayment: Long, monthlyPayment: Long, months: Int): InstallmentResult {
        require(cashPrice > 0 && downPayment >= 0 && monthlyPayment > 0 && months in 1..600) {
            "noto'g'ri kirish"
        }
        val financed = cashPrice - downPayment
        val totalPaid = downPayment + monthlyPayment * months
        val overpay = totalPaid - cashPrice
        val overpayBp = MoneyMath.ratioBp(overpay, cashPrice)
        if (financed <= 0 || monthlyPayment * months <= financed) {
            return InstallmentResult(financed, totalPaid, overpay, overpayBp, 0, 0)
        }
        val r = monthlyRate(BigDecimal.valueOf(financed), BigDecimal.valueOf(monthlyPayment), months)
        val nominal = r.multiply(BigDecimal.valueOf(120_000), MC).setScale(0, RoundingMode.HALF_UP)
        var growth = BigDecimal.ONE
        val onePlus = BigDecimal.ONE.add(r, MC)
        repeat(12) { growth = growth.multiply(onePlus, MC) }
        val effective = growth.subtract(BigDecimal.ONE, MC)
            .multiply(BigDecimal.valueOf(10_000), MC).setScale(0, RoundingMode.HALF_UP)
        return InstallmentResult(
            financed, totalPaid, overpay, overpayBp,
            nominal.toInt().coerceAtMost(Int.MAX_VALUE),
            effective.min(BigDecimal.valueOf(Int.MAX_VALUE.toLong())).toInt(),
        )
    }

    /** Annuitetning joriy qiymati: pmt × Σ (1+r)^-k, k = 1..n. */
    private fun presentValue(pmt: BigDecimal, n: Int, r: BigDecimal): BigDecimal {
        val d = BigDecimal.ONE.divide(BigDecimal.ONE.add(r, MC), MC)
        var p = BigDecimal.ONE
        var acc = BigDecimal.ZERO
        repeat(n) {
            p = p.multiply(d, MC)
            acc = acc.add(p, MC)
        }
        return acc.multiply(pmt, MC)
    }

    /** Ikkiga bo'lish usuli: PV(r) = financed bo'ladigan oylik stavka. PV(r) kamayuvchi. */
    private fun monthlyRate(financed: BigDecimal, pmt: BigDecimal, n: Int): BigDecimal {
        var lo = BigDecimal.ZERO
        var hi = BigDecimal.ONE
        var guard = 0
        while (presentValue(pmt, n, hi) > financed && guard < 30) {
            hi = hi.multiply(BigDecimal.valueOf(2), MC)
            guard++
        }
        val two = BigDecimal.valueOf(2)
        repeat(ITERATIONS) {
            val mid = lo.add(hi, MC).divide(two, MC)
            if (presentValue(pmt, n, mid) > financed) lo = mid else hi = mid
        }
        return lo.add(hi, MC).divide(two, MC)
    }
}

object SaveInstead {
    /**
     * Bo'lib to'lash o'rniga har oy shu to'lovni chetga qo'yilsa, naqd narx necha oyda yig'iladi
     * (boshlang'ich to'lov allaqachon bor deb hisoblanadi). Yuqoriga yaxlitlanadi.
     */
    fun months(cashPrice: Long, downPayment: Long, monthlyPayment: Long): Int {
        require(monthlyPayment > 0) { "oylik to'lov musbat bo'lishi kerak" }
        val need = (cashPrice - downPayment).coerceAtLeast(0)
        return ((need + monthlyPayment - 1) / monthlyPayment).toInt()
    }
}
