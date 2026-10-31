package uz.qarzsiz.core

import java.time.LocalDate
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class CoreTest {
    private fun debt(rate: Int = 0, penalty: Boolean = false, balance: Long = 100_00, start: Long = balance) = Debt(
        id = "d", creditor = "X", kind = DebtKind.OTHER, balance = balance, startBalance = start,
        annualRateBp = rate, hasPenalty = penalty, createdOn = "2026-10-31",
    )

    @Test
    fun parseAmounts() {
        assertEquals(150_000_000L, MoneyFormat.parse("1 500 000"))
        assertEquals(150_000_050L, MoneyFormat.parse("1500000,50"))
        assertEquals(1_265_050L, MoneyFormat.parse("12 650.5"))
        assertEquals(5L, MoneyFormat.parse(",05"))
        assertNull(MoneyFormat.parse(""))
        assertNull(MoneyFormat.parse("-5"))
        assertNull(MoneyFormat.parse("1.2.3"))
        assertNull(MoneyFormat.parse("1,234"))
        assertNull(MoneyFormat.parse("abc"))
        assertEquals(2450, MoneyFormat.parsePercentBp("24,5"))
        assertNull(MoneyFormat.parsePercentBp("2000"))
    }

    @Test
    fun formatAmounts() {
        assertEquals("1\u00A0500\u00A0000", MoneyFormat.amount(150_000_000))
        assertEquals("12\u00A0650,05", MoneyFormat.amount(1_265_005))
        assertEquals("0", MoneyFormat.amount(0))
        assertEquals("24,5%", MoneyFormat.percent(2450))
        assertEquals("8%", MoneyFormat.percent(800))
        assertEquals("0,75%", MoneyFormat.percent(75))
        assertEquals("12,5 mln", MoneyFormat.compact(1_250_000_000))
        assertEquals("3\u00A0000\u00A0$", MoneyFormat.withCurrency(300_000, Currency.USD))
        assertEquals("77\u00A0546\u00A0so'm", MoneyFormat.withCurrency(7_754_583, Currency.UZS))
    }

    @Test
    fun classification() {
        assertEquals(DebtCategory.A, debt(rate = 2400).category)
        assertEquals(DebtCategory.A, debt(penalty = true).category)
        assertEquals(DebtCategory.B, debt().category)
    }

    @Test
    fun progress() {
        assertEquals(5_000, debt(balance = 50_00, start = 100_00).progressBp)
        assertEquals(10_000, debt(balance = 0, start = 100_00).progressBp)
        assertTrue(debt(balance = 0).isClosed)
        assertEquals(0, debt(balance = 150_00, start = 100_00).progressBp)
    }

    @Test
    fun fxWithoutRate() {
        assertNull(FxRates().toUzs(100, Currency.USD))
        assertEquals(100, FxRates().toUzs(100, Currency.UZS))
    }

    @Test
    fun habitStreak() {
        val today = LocalDate.of(2026, 10, 31)
        val done = setOf(
            Habits.key(today.minusDays(1), "early"),
            Habits.key(today.minusDays(2), "early"),
            Habits.key(today.minusDays(4), "early"),
        )
        assertEquals(2, Habits.streak(done, "early", today))
        assertEquals(3, Habits.streak(done + Habits.key(today, "early"), "early", today))
        assertEquals(0, Habits.streak(done, "move", today))
    }

    @Test
    fun avalanchePaysLessInterestThanProRata() {
        val debts = listOf(
            PlanDebt("hot", 20_000_000_00, 4800, 500_000_00),
            PlanDebt("cold", 20_000_000_00, 0, 0),
        )
        val a = Planner.simulate(debts, 3_000_000_00, Strategy.AVALANCHE)
        val p = Planner.simulate(debts, 3_000_000_00, Strategy.PRO_RATA)
        assertTrue(a.finished && p.finished)
        assertTrue(a.totalInterest < p.totalInterest)
    }

    @Test
    fun budgetTooSmallNeverFinishes() {
        val r = Planner.simulate(listOf(PlanDebt("a", 100_000_000_00, 6000, 0)), 1_000_000_00, Strategy.AVALANCHE)
        assertFalse(r.finished)
        assertNull(r.payoffMonth[0])
    }

    @Test
    fun scriptsHaveNoPressure() {
        val text = Scripts.personal(Scripts.Proposal("Aziz aka", "10 000 $", "300 $", "dekabrdan", 34))
        assertTrue("Aziz aka" in text && "300 $" in text && "34 oyda" in text)
        assertFalse("o'lib" in text)
    }
}

class HelpersTest {
    @Test
    fun saveInstead() {
        assertEquals(10, SaveInstead.months(6_000_000_00, 0, 650_000_00))
        assertEquals(0, SaveInstead.months(100, 200, 50))
    }

    @Test
    fun dueDates() {
        val d = LocalDate.of(2026, 2, 10)
        assertEquals(LocalDate.of(2026, 2, 28), DueDates.next(31, d))
        assertEquals(LocalDate.of(2026, 2, 10), DueDates.next(10, d))
        assertEquals(LocalDate.of(2026, 3, 5), DueDates.next(5, d))
    }

    @Test
    fun overviewConvertsAndFlagsMissingRates() {
        val debts = listOf(
            Debt("a", "Bank", DebtKind.BANK_CREDIT, balance = 10_000_000_00, annualRateBp = 2400, monthlyPayment = 1_000_000_00, createdOn = "2026-10-31"),
            Debt("b", "Aziz", DebtKind.PERSONAL, Currency.USD, balance = 1_000_00, createdOn = "2026-10-31"),
            Debt("c", "Kaspi", DebtKind.FOREIGN_BANK, Currency.KZT, balance = 100_000_00, annualRateBp = 3000, createdOn = "2026-10-31"),
        )
        val s = PlanSettings(monthlyIncome = 10_000_000_00, rates = FxRates(mapOf(Currency.USD to 12_650_00)))
        val o = OverviewCalc.compute(debts, s)
        assertEquals(setOf(Currency.KZT), o.missingRates)
        assertEquals(10_000_000_00L + 12_650_000_00L, o.totalUzs)
        assertEquals(1, o.countB)
        assertEquals(2, o.countA)
        assertEquals(1000, o.debtLoadBp)
        assertEquals(7_000_000_00, o.budgetUzs)
        assertEquals("a", o.lines.first().debt.id)
    }

    @Test
    fun progressKeepsClosedDebts() {
        val open = Debt("a", "A", DebtKind.PERSONAL, balance = 10_000_00, createdOn = "2026-10-31")
        val closed = Debt("b", "B", DebtKind.PERSONAL, balance = 0, startBalance = 10_000_00, closedOn = "2026-10-31", createdOn = "2026-10-01")
        assertEquals(5_000, OverviewCalc.compute(listOf(open, closed), PlanSettings()).overallProgressBp)
    }
}

class TranslitTest {
    private fun c(s: String) = Translit.toCyrillic(s)

    @Test
    fun letters() {
        assertEquals("Қарздан чиқиш мумкин", c("Qarzdan chiqish mumkin"))
        assertEquals("сўм", c("so'm"))
        assertEquals("йўқ", c("yo'q"))
        assertEquals("Ўзбекистон", c("O'zbekiston"))
        assertEquals("ғалла", c("g'alla"))
        assertEquals("маълумот", c("ma'lumot"))
        assertEquals("Эҳтиёт бўлинг", c("Ehtiyot bo'ling"))
        assertEquals("Евро", c("Yevro"))
        assertEquals("ишлаяпти", c("ishlayapti"))
        assertEquals("Кўчки", c("Koʻchki"))
        assertEquals("юк", c("yuk"))
        assertEquals("Шу ой", c("Shu oy"))
        assertEquals("реструктуризация", c("restrukturizatsiya"))
        assertEquals("поэзия", c("poeziya"))
    }

    @Test
    fun wordsCaseAndKeep() {
        assertEquals("2029-йил декабрь", c("2029-yil dekabr"))
        assertEquals("декабрдан", c("dekabrdan"))
        assertEquals("АҚШ доллари", c("AQSh dollari"))
        assertEquals("АРИЗА", c("ARIZA"))
        assertEquals("ЙЎҚ", c("YO'Q"))
        assertEquals("1 USD = 12 650 сўм", c("1 USD = 12 650 so'm"))
        assertEquals("Android Keystore", c("Android Keystore"))
        assertEquals("Б — фоизсиз", c("B — foizsiz"))
        assertEquals("12,5 млн", c("12,5 mln"))
        assertEquals("Наси калькулятори", c("Nasi kalkulyatori"))
    }

    @Test
    fun idempotentAndSafe() {
        val once = c("Hammasini o'chirish: «Ha», 45% — $ 100!")
        assertEquals(once, c(once))
        assertEquals("«Ҳа»", c("«Ha»"))
        assertEquals("ўйин'", c("o'yin'"))
        assertEquals("Lotin", Translit.apply("Lotin", Script.LATIN))
    }
}

class RemindersTest {
    private val today = LocalDate.of(2026, 10, 31)
    private fun debt(id: String, day: Int?, closed: Boolean = false, pay: Long = 500_000_00) = Debt(
        id = id, creditor = id.uppercase(), kind = DebtKind.BANK_CREDIT, balance = if (closed) 0 else 1_000_000_00,
        monthlyPayment = pay, dueDay = day, createdOn = "2026-10-01",
    )

    @Test
    fun onDayAndDaysBefore() {
        // 31-okt: bugun 31-kun, 2 kundan keyin — 2-noyabr.
        val items = Reminders.due(
            listOf(debt("a", 31), debt("b", 2), debt("c", 1), debt("d", null), debt("e", 2, closed = true)),
            emptyList(), today, 2,
        )
        assertEquals(listOf("a" to 0, "b" to 2), items.map { it.debtId to it.daysLeft })
        assertEquals(LocalDate.of(2026, 11, 2), items[1].dueDate)
    }

    @Test
    fun paidThisPeriodIsSkipped() {
        val items = Reminders.due(
            listOf(debt("a", 31), debt("b", 2)),
            listOf("a" to today.minusDays(3), "b" to today.minusDays(40)),
            today, 2,
        )
        assertEquals(listOf("b"), items.map { it.debtId })
    }

    @Test
    fun shortMonthUsesLastDay() {
        val feb = LocalDate.of(2026, 2, 28)
        assertEquals(listOf(0), Reminders.due(listOf(debt("a", 31)), emptyList(), feb, 2).map { it.daysLeft })
    }

    @Test
    fun messages() {
        val one = Reminders.due(listOf(debt("a", 31)), emptyList(), today, 2)
        val (t1, b1) = Reminders.message(one)
        assertEquals("A: bugun to'lov kuni", t1)
        assertTrue("500 000 so'm" in b1)
        val two = Reminders.due(listOf(debt("a", 31), debt("b", 2, pay = 0)), emptyList(), today, 2)
        val (t2, b2) = Reminders.message(two)
        assertEquals("2 ta to'lov yaqin", t2)
        assertEquals("A: bugun — 500 000 so'm\nB: 2 kundan keyin", b2)
    }
}
