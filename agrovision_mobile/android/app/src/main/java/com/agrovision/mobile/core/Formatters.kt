package com.agrovision.mobile.core

import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.roundToInt

/**
 * Raqam/sana formatlash yordamchilari — butun ilova bo'ylab bir xil ko'rinish uchun.
 *
 * MUHIM: barcha formatlash `Locale.US` bilan qilinadi (nuqta — kasr ajratkichi,
 * vergul — minglik ajratkichi), qurilma tili/hududi qanday bo'lishidan qat'iy
 * nazar. Aks holda ba'zi qurilmalarda (masalan rus/o'zbek) standart o'nlik
 * ajratkich vergul bo'lgani uchun natijani keyinroq qayta o'qishda (parse)
 * `NumberFormatException` chiqadi — bu SeedData'da haqiqiy production xatosiga
 * sabab bo'lgan (masalan: "63,7".toDouble() -> crash).
 */
object Fmt {
    fun number(value: Double, decimals: Int = 0): String =
        String.format(Locale.US, "%,.${decimals}f", value).replace(',', ' ')

    fun money(value: Double): String = when {
        abs(value) >= 1_000_000_000 -> "${number(value / 1_000_000_000, 1)} mlrd"
        abs(value) >= 1_000_000 -> "${number(value / 1_000_000, 1)} mln"
        else -> number(value, 0)
    }

    fun percent(value: Double): String = "${number(value, 1)}%"

    fun date(epochDay: Long): String =
        LocalDate.ofEpochDay(epochDay).format(DateTimeFormatter.ofPattern("yyyy-MM-dd"))

    fun shortDate(epochDay: Long): String =
        LocalDate.ofEpochDay(epochDay).format(DateTimeFormatter.ofPattern("MM-dd"))

    /** Kod ichida (hisob-kitob/saqlash uchun) sonni har doim nuqta bilan formatlash. */
    fun fixed(value: Double, decimals: Int): String = String.format(Locale.US, "%.${decimals}f", value)

    private fun abs(v: Double) = if (v < 0) -v else v
}

fun Double.round0(): Double = kotlin.math.round(this)
fun Double.round1(): Double = (this * 10).roundToInt() / 10.0
fun Double.round2(): Double = (this * 100).roundToInt() / 100.0

/**
 * Foydalanuvchi qo'lda kiritgan matnni xavfsiz Double'ga aylantiradi.
 * Ayrim klaviaturalar (rus/o'zbek) o'nlik ajratkich sifatida vergul
 * ko'rsatadi — shu sababli avval vergulni nuqtaga almashtiramiz.
 */
fun String.toSafeDouble(): Double? =
    trim().replace(',', '.').toDoubleOrNull()

fun String.toSafeInt(): Int? = trim().toIntOrNull()
