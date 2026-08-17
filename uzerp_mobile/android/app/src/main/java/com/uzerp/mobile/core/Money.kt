package com.uzerp.mobile.core

import java.math.BigDecimal
import java.math.RoundingMode
import java.text.DecimalFormat
import java.text.DecimalFormatSymbols
import java.util.Locale

/**
 * Pul bilan ishlash yordamchilari.
 *
 * Python tarafidagi `decimal.Decimal` bilan bir xil tamoyil: barcha
 * moliyaviy hisob-kitoblar `BigDecimal` bilan, 2 xonali aniqlikda,
 * HALF_UP yaxlitlash bilan bajariladi — float ishlatilmaydi.
 */

private val TWO_PLACES = 2
private val ZERO: BigDecimal = BigDecimal.ZERO.setScale(TWO_PLACES)

/** Har qanday qiymatni xavfsiz 2 xonali [BigDecimal] ga aylantiradi. */
fun d(value: Any?): BigDecimal = when (value) {
    null -> ZERO
    is BigDecimal -> value.setScale(TWO_PLACES, RoundingMode.HALF_UP)
    is Int -> BigDecimal(value).setScale(TWO_PLACES)
    is Long -> BigDecimal(value).setScale(TWO_PLACES)
    is Double -> BigDecimal.valueOf(value).setScale(TWO_PLACES, RoundingMode.HALF_UP)
    is String -> value.toBigDecimalOrNull()?.setScale(TWO_PLACES, RoundingMode.HALF_UP) ?: ZERO
    else -> ZERO
}

private fun String.toBigDecimalOrNull(): BigDecimal? =
    try {
        BigDecimal(this.trim())
    } catch (_: NumberFormatException) {
        null
    }

/** [BigDecimal] ni bazaga saqlash uchun matnga aylantiradi (aniqlik yo'qotilmaydi). */
fun BigDecimal.toDbString(): String = this.setScale(TWO_PLACES, RoundingMode.HALF_UP).toPlainString()

/** Bazadan o'qilgan matnni [BigDecimal] ga aylantiradi. */
fun String?.toMoney(): BigDecimal = d(this)

private val moneyFormat: DecimalFormat by lazy {
    val symbols = DecimalFormatSymbols(Locale.US).apply { groupingSeparator = ' ' }
    DecimalFormat("#,##0.##", symbols)
}

/** Pulni o'qish oson formatda qaytaradi: `1 234 567` yoki `1 234 567.89`. */
fun money(value: Any?, currency: String = ""): String {
    val amount = d(value)
    val text = moneyFormat.format(amount)
    return if (currency.isBlank()) text else "$text $currency"
}

/** QQS summasini narx ichidan ajratib oladi: `total * rate / (100 + rate)`. */
fun extractVat(total: BigDecimal, ratePercent: BigDecimal): BigDecimal {
    if (ratePercent <= BigDecimal.ZERO) return ZERO
    val denom = BigDecimal(100).add(ratePercent)
    return d(total.multiply(ratePercent).divide(denom, 10, RoundingMode.HALF_UP))
}
