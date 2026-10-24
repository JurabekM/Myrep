package uz.barakadaftari.app.native

import java.time.LocalDate
import java.time.LocalTime
import java.time.YearMonth
import java.time.ZoneId
import java.time.ZonedDateTime

/** Eslatma vaqtini hisoblash (sof funksiyalar — JUnit bilan testlanadi). */
object ReminderSchedule {
    val ZONE: ZoneId = ZoneId.of("Asia/Tashkent")
    val REMIND_AT: LocalTime = LocalTime.of(9, 0)

    /** Shu oydagi to'lov kuni; qisqa oyda — oyning oxirgi kuni. */
    fun dueDate(month: YearMonth, dayOfMonth: Int): LocalDate =
        month.atDay(dayOfMonth.coerceIn(1, month.lengthOfMonth()))

    /**
     * Keyingi eslatma: to'lov kunidan 1 kun oldin 09:00.
     *
     * Agar eslatma vaqti bugun o'tib ketgan bo'lsa-yu, bu to'lov uchun hali
     * eslatilmagan bo'lsa ([lastNotifiedDue] boshqa sana) — darhol ([now]).
     * Shunday qilib ilova kech o'rnatilsa ham eslatma yo'qolmaydi va bir
     * to'lov uchun ikki marta kelmaydi.
     */
    fun next(
        now: ZonedDateTime,
        dayOfMonth: Int,
        lastNotifiedDue: LocalDate?,
    ): Trigger {
        val today = now.withZoneSameInstant(ZONE).toLocalDate()
        var month = YearMonth.from(today)
        repeat(3) {
            val due = dueDate(month, dayOfMonth)
            val remindAt = ZonedDateTime.of(due.minusDays(1), REMIND_AT, ZONE)
            val alreadyNotified = lastNotifiedDue == due
            if (!alreadyNotified && !due.isBefore(today)) {
                return if (remindAt.isAfter(now)) Trigger(remindAt, due) else Trigger(now, due)
            }
            month = month.plusMonths(1)
        }
        error("Eslatma topilmadi") // 3 oy ichida doim topiladi
    }

    data class Trigger(val at: ZonedDateTime, val due: LocalDate)

    /** Keyingi juma 09:00; juma kuni 09:00 dan oldin bo'lsa — bugun. */
    fun nextFriday(now: ZonedDateTime): ZonedDateTime = nextWeekday(now, java.time.DayOfWeek.FRIDAY)

    /** Keyingi [day] 09:00 (Toshkent); o'sha kuni 09:00 dan oldin bo'lsa — bugun. */
    fun nextWeekday(now: ZonedDateTime, day: java.time.DayOfWeek): ZonedDateTime {
        var date = now.withZoneSameInstant(ZONE).toLocalDate()
        while (true) {
            if (date.dayOfWeek == day) {
                val at = ZonedDateTime.of(date, REMIND_AT, ZONE)
                if (at.isAfter(now)) return at
            }
            date = date.plusDays(1)
        }
    }

    /** Daromad eslatmasi vaqti: kunlik va haftalik — 20:00, oylik — 10:00. */
    val INCOME_EVENING: LocalTime = LocalTime.of(20, 0)
    val INCOME_SALARY: LocalTime = LocalTime.of(10, 0)

    /**
     * Keyingi daromad eslatmasi (Vazifa 15):
     * * [IncomeReminderKind.DAILY] — bugun 20:00 (o'tgan bo'lsa ertaga);
     * * [IncomeReminderKind.WEEKLY] — keyingi shanba 20:00;
     * * [IncomeReminderKind.MONTHLY] — maosh kuni ([dayOfMonth], qisqa oyda
     *   oxirgi kun) 10:00.
     */
    fun nextIncome(
        now: ZonedDateTime,
        kind: IncomeReminderKind,
        dayOfMonth: Int,
    ): ZonedDateTime {
        val local = now.withZoneSameInstant(ZONE)
        return when (kind) {
            IncomeReminderKind.DAILY -> {
                val today = ZonedDateTime.of(local.toLocalDate(), INCOME_EVENING, ZONE)
                if (today.isAfter(now)) today else today.plusDays(1)
            }
            IncomeReminderKind.WEEKLY -> {
                var date = local.toLocalDate()
                while (true) {
                    if (date.dayOfWeek == java.time.DayOfWeek.SATURDAY) {
                        val at = ZonedDateTime.of(date, INCOME_EVENING, ZONE)
                        if (at.isAfter(now)) return at
                    }
                    date = date.plusDays(1)
                }
                @Suppress("UNREACHABLE_CODE")
                error("unreachable")
            }
            IncomeReminderKind.MONTHLY -> {
                var month = YearMonth.from(local.toLocalDate())
                while (true) {
                    val at = ZonedDateTime.of(dueDate(month, dayOfMonth), INCOME_SALARY, ZONE)
                    if (at.isAfter(now)) return at
                    month = month.plusMonths(1)
                }
                @Suppress("UNREACHABLE_CODE")
                error("unreachable")
            }
        }
    }
}
