package uz.distribos.core

import java.math.BigDecimal

/**
 * Son va pul formatlash — yagona manba.
 *
 * Desktop tomonida ham aynan shu qoidalar (`domain/formatting.py`):
 * pul BUTUN son (tiyin), miqdor esa ortiqcha nollarsiz, lekin ILMIY
 * NOTATSIYASIZ ko'rsatiladi.
 */
object Formatting {

    /** Miqdorni ortiqcha nollarsiz ko'rsatadi: "40.000" -> "40". */
    fun quantity(value: String?): String {
        if (value.isNullOrBlank()) return "0"
        val number = BigDecimal(value).stripTrailingZeros()
        // `toPlainString()` SHART: `toString()` katta sonlarda ilmiy
        // notatsiya beradi ("4E+1") va foydalanuvchi buni buzilgan dastur
        // deb o'ylaydi.
        return number.toPlainString()
    }

    /** Tiyindan o'qiladigan matnga: 150000000 -> "1 500 000 UZS". */
    fun money(amount: Long, currency: String = "UZS"): String {
        val negative = amount < 0
        val absolute = if (negative) -amount else amount
        val whole = absolute / 100
        val fraction = absolute % 100
        val grouped = whole.toString()
            .reversed().chunked(3).joinToString(" ").reversed()
        val sign = if (negative) "-" else ""
        return if (fraction > 0) {
            "$sign$grouped,${fraction.toString().padStart(2, '0')} $currency"
        } else {
            "$sign$grouped $currency"
        }
    }

    /**
     * So'mdagi qiymatni tiyinga aylantiradi.
     *
     * `BigDecimal` orqali: `(12.34 * 100).toLong()` ba'zan 1233 beradi,
     * bu moliyaviy hisobda qabul qilib bo'lmaydigan xato.
     */
    fun toTiyin(amount: String): Long =
        BigDecimal(amount).multiply(BigDecimal(100)).setScale(0, java.math.RoundingMode.HALF_UP).toLong()

    fun fromTiyin(amount: Long): BigDecimal =
        BigDecimal(amount).divide(BigDecimal(100))
}
