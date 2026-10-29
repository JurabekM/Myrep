package uz.mpay.wallet.app

import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Ilova tillari (o'zbek — standart). */
enum class Lang(val tag: String) {
    UZ("uz"), RU("ru"), EN("en");

    val locale: Locale get() = Locale.forLanguageTag(tag)

    companion object {
        fun of(tag: String?): Lang = entries.firstOrNull { it.tag == tag } ?: UZ
    }
}

/** Ko'rinish formatlari — platformadan mustaqil (JVM testlari). */
object Format {
    /** O'zbekiston vaqti (UTC+5) — sxema vaqti bilan bir xil. */
    val ZONE: ZoneId = ZoneId.of("Asia/Tashkent")

    private const val NBSP = ' '

    /**
     * Summa: `12 500,00 so'm` (uz), `12 500,00 сум` (ru), `12,500.00 UZS` (en). Faqat UZS (860) nomi bilan,
     * boshqa valyuta — ISO raqami bilan.
     */
    fun money(minor: Long, currency: Int, lang: Lang): String {
        val neg = minor < 0
        val abs = kotlin.math.abs(minor)
        val whole = (abs / 100).toString()
        val frac = (abs % 100).toString().padStart(2, '0')
        val (sep, dec) = if (lang == Lang.EN) ',' to '.' else NBSP to ','
        val grouped = whole.reversed().chunked(3).joinToString(sep.toString()).reversed()
        val num = (if (neg) "-" else "") + grouped + dec + frac
        val cur = when {
            currency != 860 -> currency.toString().padStart(3, '0')
            lang == Lang.RU -> "сум"
            lang == Lang.EN -> "UZS"
            else -> "so'm"
        }
        return "$num$NBSP$cur"
    }

    /** Karta raqami kiritilayotganda: 4 tadan guruh (`9900 1200 0000 0014`). */
    fun groupPan(digits: String): String = digits.chunked(4).joinToString(" ")

    /** Luhn nazorat raqami (faqat raqamlar, 13–19 belgi). */
    fun luhnOk(digits: String): Boolean {
        if (digits.length !in 13..19 || !digits.all(Char::isDigit)) return false
        val sum = digits.reversed().mapIndexed { i, c ->
            val d = c - '0'
            if (i % 2 == 1) (d * 2).let { if (it > 9) it - 9 else it } else d
        }.sum()
        return sum % 10 == 0
    }

    /** Foydalanuvchi kiritgan `MMYY` → server `YYMM`; noto'g'ri oy — `null`. */
    fun mmyyToYymm(mmyy: String): String? {
        if (mmyy.length != 4 || !mmyy.all(Char::isDigit)) return null
        val mm = mmyy.take(2).toInt()
        if (mm !in 1..12) return null
        return mmyy.drop(2) + mmyy.take(2)
    }

    /** Server `YYMM` → karta ko'rinishi `MM/YY`. */
    fun expiry(yymm: String): String = if (yymm.length == 4) "${yymm.drop(2)}/${yymm.take(2)}" else yymm

    fun time(unix: Long, lang: Lang): String =
        DateTimeFormatter.ofPattern("HH:mm", lang.locale).format(Instant.ofEpochSecond(unix).atZone(ZONE))

    /** Kun sarlavhasi: `29.10.2026` (barcha tillarda bir xil — oy nomlari tarjimasiz). */
    fun day(unix: Long): String =
        DateTimeFormatter.ofPattern("dd.MM.yyyy").format(Instant.ofEpochSecond(unix).atZone(ZONE))

    /** Maskalangan PAN'ning oxirgi 4 raqami (`•• 0014`). */
    fun last4(masked: String): String = "•• " + masked.takeLast(4)
}
