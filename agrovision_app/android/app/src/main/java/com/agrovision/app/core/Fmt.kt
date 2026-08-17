package com.agrovision.app.core

import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.abs
import kotlin.math.round

/**
 * Butun ilova bo'ylab yagona raqam/sana formatlash.
 *
 * MUHIM QOIDA: formatlash HAR DOIM `Locale.US` bilan bajariladi (nuqta —
 * o'nlik ajratkich). Qurilma tili rus/o'zbek bo'lganda standart locale vergul
 * ishlatadi va formatlangan matnni keyin qayta o'qish (`toDouble`)
 * `NumberFormatException` beradi. Shu sababli:
 *   - ko'rsatish uchun → Fmt.* funksiyalari
 *   - saqlash/hisoblash uchun → Double qiymatning o'zi (matnga aylantirilmaydi)
 *   - foydalanuvchi kiritgan matn → `String.toSafeDouble()` (vergulni ham tushunadi)
 */
object Fmt {
    fun num(value: Double, decimals: Int = 0): String =
        String.format(Locale.US, "%,.${decimals}f", value).replace(',', ' ')

    fun dec(value: Double, decimals: Int = 2): String =
        String.format(Locale.US, "%.${decimals}f", value)

    /** Katta so'm summalarini qisqartirib ko'rsatish. */
    fun money(value: Double): String = when {
        abs(value) >= 1_000_000_000 -> "${dec(value / 1_000_000_000, 1)} mlrd"
        abs(value) >= 1_000_000 -> "${dec(value / 1_000_000, 1)} mln"
        abs(value) >= 1_000 -> "${dec(value / 1_000, 1)} ming"
        else -> num(value, 0)
    }

    fun percent(value: Double, decimals: Int = 1): String = "${dec(value, decimals)}%"

    fun signedPercent(value: Double): String =
        (if (value >= 0) "+" else "") + dec(value, 1) + "%"

    fun date(epochDay: Long): String =
        LocalDate.ofEpochDay(epochDay).format(DateTimeFormatter.ISO_LOCAL_DATE)

    fun monthDay(epochDay: Long): String =
        LocalDate.ofEpochDay(epochDay).format(DateTimeFormatter.ofPattern("MM-dd"))

    fun yearMonth(epochDay: Long): String =
        LocalDate.ofEpochDay(epochDay).let { String.format(Locale.US, "%d-%02d", it.year, it.monthValue) }

    fun dateTime(millis: Long): String = DateTimeFormatter
        .ofPattern("yyyy-MM-dd HH:mm")
        .format(java.time.Instant.ofEpochMilli(millis).atZone(java.time.ZoneId.systemDefault()))

    val MONTHS_UZ = listOf(
        "Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek",
    )

    fun monthLabel(month: Int): String = MONTHS_UZ.getOrElse(month - 1) { month.toString() }
}

fun Double.round1(): Double = round(this * 10) / 10.0
fun Double.round2(): Double = round(this * 100) / 100.0
fun Double.round3(): Double = round(this * 1000) / 1000.0

/**
 * Foydalanuvchi kiritgan matnni xavfsiz Double'ga aylantiradi — vergulli
 * ("63,7") va bo'shliqli kiritishni ham tushunadi.
 */
fun String?.toSafeDouble(): Double? =
    this?.trim()?.replace(" ", "")?.replace(',', '.')?.toDoubleOrNull()

fun String?.toSafeInt(): Int? = this?.trim()?.replace(" ", "")?.toIntOrNull()
