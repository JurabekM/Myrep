package uz.buildcontrol.mobile.core

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlin.math.abs
import kotlin.math.roundToLong

/** Presentation helpers matching the desktop formatting rules. */
object Fmt {

    private const val NBSP = ' '
    private val dateOut: DateTimeFormatter = DateTimeFormatter.ofPattern("dd.MM.yyyy")
    private val dateTimeOut: DateTimeFormatter = DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm")

    /** Groups thousands with a thin space; decimal separator is a comma. */
    fun group(value: Double, decimals: Int = 0): String {
        val text = String.format(java.util.Locale.US, "%,.${decimals}f", value)
        if (decimals == 0) return text.replace(',', NBSP)
        val dot = text.lastIndexOf('.')
        return text.substring(0, dot).replace(',', NBSP) + "," + text.substring(dot + 1)
    }

    /** `12 500 000 so'm` */
    fun money(value: Double?, withSuffix: Boolean = true): String {
        val amount = value ?: 0.0
        val text = group(amount, 0)
        return if (withSuffix) "$text$NBSP${I18n.currencySuffix()}" else text
    }

    fun qty(value: Double?): String {
        val amount = value ?: 0.0
        return if (abs(amount - amount.roundToLong()) < 1e-9) group(amount, 0) else group(amount, 2)
    }

    fun percent(value: Double?, decimals: Int = 1): String =
        String.format("%.${decimals}f", value ?: 0.0).replace('.', ',') + "%"

    /** ISO `yyyy-MM-dd` to `31.07.2026`. */
    fun date(iso: String?): String {
        if (iso.isNullOrBlank()) return "—"
        return try {
            LocalDate.parse(iso.substringBefore('T').substringBefore(' ')).format(dateOut)
        } catch (_: Exception) {
            iso
        }
    }

    fun dateTime(millis: Long?): String {
        if (millis == null || millis <= 0) return "—"
        return Instant.ofEpochMilli(millis).atZone(ZoneId.systemDefault()).format(dateTimeOut)
    }

    fun today(): String = LocalDate.now().toString()

    fun plusDays(iso: String?, days: Long): String =
        (runCatching { LocalDate.parse(iso) }.getOrDefault(LocalDate.now())).plusDays(days).toString()

    fun daysBetween(from: String?, to: String?): Long {
        val a = runCatching { LocalDate.parse(from) }.getOrNull() ?: return 0
        val b = runCatching { LocalDate.parse(to) }.getOrNull() ?: return 0
        return java.time.temporal.ChronoUnit.DAYS.between(a, b)
    }

    fun isPast(iso: String?): Boolean {
        val date = runCatching { LocalDate.parse(iso) }.getOrNull() ?: return false
        return date.isBefore(LocalDate.now())
    }

    fun short(text: String?, limit: Int = 60): String {
        val value = (text ?: "").trim().replace('\n', ' ')
        return if (value.length <= limit) value else value.take(limit - 1) + "…"
    }

    /** Tolerant number parsing for user input (`12 500,50`). */
    fun parseNumber(text: String): Double =
        text.replace(NBSP.toString(), "").replace(" ", "").replace(',', '.').toDoubleOrNull() ?: 0.0
}
