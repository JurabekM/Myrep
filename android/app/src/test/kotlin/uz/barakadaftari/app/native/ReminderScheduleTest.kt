package uz.barakadaftari.app.native

import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.LocalDate
import java.time.ZonedDateTime

class ReminderScheduleTest {
    private fun at(y: Int, m: Int, d: Int, h: Int, min: Int = 0) =
        ZonedDateTime.of(y, m, d, h, min, 0, 0, ReminderSchedule.ZONE)

    @Test
    fun remindsOneDayBeforeAtNine() {
        val t = ReminderSchedule.next(at(2026, 10, 6, 15), 25, null)
        assertEquals(at(2026, 10, 24, 9), t.at)
        assertEquals(LocalDate.of(2026, 10, 25), t.due)
    }

    @Test
    fun dueDayPassedGoesToNextMonth() {
        val t = ReminderSchedule.next(at(2026, 10, 26, 8), 25, null)
        assertEquals(LocalDate.of(2026, 11, 25), t.due)
        assertEquals(at(2026, 11, 24, 9), t.at)
    }

    @Test
    fun shortMonthUsesLastDay() {
        val t = ReminderSchedule.next(at(2026, 2, 1, 8), 31, null)
        assertEquals(LocalDate.of(2026, 2, 28), t.due)
        assertEquals(at(2026, 2, 27, 9), t.at)
    }

    @Test
    fun reminderTimePassedButNotNotifiedFiresNow() {
        val now = at(2026, 10, 24, 15)
        val t = ReminderSchedule.next(now, 25, null)
        assertEquals(now, t.at)
        assertEquals(LocalDate.of(2026, 10, 25), t.due)
        // To'lov kuni o'zida ham hali eslatilmagan bo'lsa — darhol.
        val onDue = ReminderSchedule.next(at(2026, 10, 25, 10), 25, null)
        assertEquals(LocalDate.of(2026, 10, 25), onDue.due)
    }

    @Test
    fun alreadyNotifiedNeverRepeatsForSameDue() {
        val t = ReminderSchedule.next(at(2026, 10, 24, 15), 25, LocalDate.of(2026, 10, 25))
        assertEquals(LocalDate.of(2026, 11, 25), t.due)
        assertEquals(at(2026, 11, 24, 9), t.at)
    }

    @Test
    fun nextFridayAtNine() {
        // 2026-10-06 — seshanba.
        assertEquals(at(2026, 10, 9, 9), ReminderSchedule.nextFriday(at(2026, 10, 6, 15)))
        // Juma 08:59 — bugun 09:00.
        assertEquals(at(2026, 10, 9, 9), ReminderSchedule.nextFriday(at(2026, 10, 9, 8, 59)))
        // Juma 09:00 aynan / undan keyin — keyingi juma.
        assertEquals(at(2026, 10, 16, 9), ReminderSchedule.nextFriday(at(2026, 10, 9, 9)))
        assertEquals(at(2026, 10, 16, 9), ReminderSchedule.nextFriday(at(2026, 10, 9, 18)))
    }

    @Test
    fun nextWeekdayForTreats() {
        // Seshanba 15:00 → shu hafta chorshanba 09:00.
        assertEquals(
            at(2026, 10, 7, 9),
            ReminderSchedule.nextWeekday(at(2026, 10, 6, 15), java.time.DayOfWeek.WEDNESDAY),
        )
        // Seshanba 15:00 → keyingi seshanba (bugungi 09:00 o'tib ketgan).
        assertEquals(
            at(2026, 10, 13, 9),
            ReminderSchedule.nextWeekday(at(2026, 10, 6, 15), java.time.DayOfWeek.TUESDAY),
        )
        // Yakshanba ham (ISO 7).
        assertEquals(
            at(2026, 10, 11, 9),
            ReminderSchedule.nextWeekday(at(2026, 10, 6, 15), java.time.DayOfWeek.of(7)),
        )
    }

    @Test
    fun firstOfMonthRemindsOnLastDayOfPreviousMonth() {
        val t = ReminderSchedule.next(at(2026, 10, 6, 15), 1, null)
        assertEquals(LocalDate.of(2026, 11, 1), t.due)
        assertEquals(at(2026, 10, 31, 9), t.at)
    }
}

class IncomeReminderScheduleTest {
    private fun at(y: Int, m: Int, d: Int, h: Int, min: Int = 0) =
        ZonedDateTime.of(y, m, d, h, min, 0, 0, ReminderSchedule.ZONE)

    @Test
    fun dailyTodayEveningOrTomorrow() {
        assertEquals(
            at(2026, 10, 11, 20),
            ReminderSchedule.nextIncome(at(2026, 10, 11, 9), IncomeReminderKind.DAILY, 1),
        )
        assertEquals(
            at(2026, 10, 12, 20),
            ReminderSchedule.nextIncome(at(2026, 10, 11, 21), IncomeReminderKind.DAILY, 1),
        )
    }

    @Test
    fun weeklyNextSaturdayEvening() {
        // 2026-10-11 — yakshanba.
        assertEquals(
            at(2026, 10, 17, 20),
            ReminderSchedule.nextIncome(at(2026, 10, 11, 9), IncomeReminderKind.WEEKLY, 1),
        )
        assertEquals(
            at(2026, 10, 17, 20),
            ReminderSchedule.nextIncome(at(2026, 10, 17, 19), IncomeReminderKind.WEEKLY, 1),
        )
    }

    @Test
    fun monthlySalaryDayShortMonth() {
        assertEquals(
            at(2026, 10, 25, 10),
            ReminderSchedule.nextIncome(at(2026, 10, 11, 9), IncomeReminderKind.MONTHLY, 25),
        )
        assertEquals(
            at(2027, 2, 28, 10),
            ReminderSchedule.nextIncome(at(2027, 1, 31, 11), IncomeReminderKind.MONTHLY, 31),
        )
    }
}
