package com.uzerp.mobile.core

import java.time.LocalDate
import java.time.LocalDateTime
import java.time.YearMonth
import java.time.format.DateTimeFormatter

/** Sana/vaqt yordamchilari — Python `now_str()`/`today_str()` bilan bir xil format. */
object DateUtils {
    private val DATE_FMT: DateTimeFormatter = DateTimeFormatter.ISO_LOCAL_DATE
    private val DATETIME_FMT: DateTimeFormatter =
        DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")

    fun todayStr(): String = LocalDate.now().format(DATE_FMT)

    fun nowStr(): String = LocalDateTime.now().format(DATETIME_FMT)

    /** Berilgan yil/oy uchun (birinchi kun, oxirgi kun) ISO matnda qaytaradi. */
    fun monthBounds(year: Int, month: Int): Pair<String, String> {
        val ym = YearMonth.of(year, month)
        return ym.atDay(1).format(DATE_FMT) to ym.atEndOfMonth().format(DATE_FMT)
    }

    /** Oxirgi [n] oy ro'yxatini (yil, oy) tartibida qaytaradi (eski -> yangi). */
    fun lastNMonths(n: Int = 12): List<Pair<Int, Int>> {
        val current = YearMonth.now()
        return (n - 1 downTo 0).map { offset ->
            val ym = current.minusMonths(offset.toLong())
            ym.year to ym.monthValue
        }
    }
}
