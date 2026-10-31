package uz.qarzsiz.core

import kotlinx.serialization.Serializable
import java.time.LocalDate
import java.time.YearMonth

/** Foydalanuvchi sozlamalari: daromad, qarz ulushi (70/30), yashash minimumi, strategiya, kurslar. */
@Serializable
data class PlanSettings(
    /** Oylik daromad, so'm (kichik birlik). */
    val monthlyIncome: Long = 0,
    /** Daromadning qarzga ketadigan ulushi, bp. Standart 70%. */
    val debtShareBp: Int = Budget.DEFAULT_SHARE_BP,
    /** Oila uchun minimal oylik yashash xarajati, so'm. */
    val livingMinimum: Long = 0,
    val strategy: Strategy = Strategy.AVALANCHE,
    val rates: FxRates = FxRates(),
)

/** Bitta qarzning rejadagi qatori (so'mda). */
data class PlanLine(
    val debt: Debt,
    val balanceUzs: Long,
    val minPaymentUzs: Long,
    val monthlyInterestUzs: Long,
    /** Shu oy to'lash tavsiya etiladi (so'm). */
    val thisMonthUzs: Long,
    /** Yopiladigan oy (1 = joriy oy) yoki `null`. */
    val payoffMonth: Int?,
)

data class Overview(
    val activeCount: Int,
    val closedCount: Int,
    val totalUzs: Long,
    val categoryATotalUzs: Long,
    val categoryBTotalUzs: Long,
    val countA: Int,
    val countB: Int,
    /** B qarzlardan kelishilganlari. */
    val agreedB: Int,
    val monthlyInterestUzs: Long,
    /** Kunlik foiz (oylik / 30, yarmi yuqoriga) — «kuniga qancha ketyapti» uchun. */
    val dailyInterestUzs: Long,
    val monthlyMinimumUzs: Long,
    /** Oylik majburiy to'lov / daromad, bp. Daromad kiritilmagan bo'lsa — `null`. */
    val debtLoadBp: Int?,
    val overallProgressBp: Int,
    /** Kursi kiritilmagan valyutalar — ular jamiga qo'shilmagan. */
    val missingRates: Set<Currency>,
    val budgetUzs: Long,
    val safeShareBp: Int,
    /** Tanlangan ulush yashash minimumini buzadi. */
    val livingAtRisk: Boolean,
    val lines: List<PlanLine>,
    /** Strategiyalar taqqoslash natijalari. */
    val results: Map<Strategy, SimResult>,
)

object OverviewCalc {
    fun compute(debts: List<Debt>, settings: PlanSettings): Overview {
        val active = debts.filter { !it.isClosed }
        val rates = settings.rates
        val missing = active.filter { rates.toUzs(1, it.currency) == null }.map { it.currency }.toSet()
        val convertible = active.filter { it.currency !in missing }

        fun uzs(amount: Long, c: Currency) = rates.toUzs(amount, c) ?: 0L

        val planDebts = convertible.map {
            PlanDebt(it.id, uzs(it.balance, it.currency), it.annualRateBp, uzs(it.monthlyPayment, it.currency))
        }
        val budget = Budget.debtBudget(settings.monthlyIncome, settings.debtShareBp)
        val results = Strategy.entries.associateWith { Planner.simulate(planDebts, budget, it) }
        val chosen = results.getValue(settings.strategy)

        val lines = convertible.mapIndexed { i, d ->
            PlanLine(
                debt = d,
                balanceUzs = planDebts[i].balance,
                minPaymentUzs = planDebts[i].minPayment,
                monthlyInterestUzs = Classifier.monthlyInterest(planDebts[i].balance, d.annualRateBp),
                thisMonthUzs = chosen.firstMonth.getOrElse(i) { 0 },
                payoffMonth = chosen.payoffMonth.getOrNull(i),
            )
        }.sortedWith(compareBy(Classifier.displayOrder) { it.debt })

        val a = lines.filter { it.debt.category == DebtCategory.A }
        val b = lines.filter { it.debt.category == DebtCategory.B }
        val minimum = lines.sumOf { it.minPaymentUzs }
        val startTotal = convertible.sumOf { uzs(it.startBalance.coerceAtLeast(it.balance), it.currency) }
        val total = lines.sumOf { it.balanceUzs }
        val safe = Budget.safeShareBp(settings.monthlyIncome, settings.livingMinimum)
        return Overview(
            activeCount = active.size,
            closedCount = debts.size - active.size,
            totalUzs = total,
            categoryATotalUzs = a.sumOf { it.balanceUzs },
            categoryBTotalUzs = b.sumOf { it.balanceUzs },
            countA = active.count { it.category == DebtCategory.A },
            countB = active.count { it.category == DebtCategory.B },
            agreedB = active.count { it.category == DebtCategory.B && it.talkStatus == TalkStatus.AGREED },
            monthlyInterestUzs = lines.sumOf { it.monthlyInterestUzs },
            dailyInterestUzs = MoneyMath.mulDivHalfUp(lines.sumOf { it.monthlyInterestUzs }, 1, 30),
            monthlyMinimumUzs = minimum,
            debtLoadBp = if (settings.monthlyIncome > 0) MoneyMath.ratioBp(minimum, settings.monthlyIncome) else null,
            overallProgressBp = if (startTotal > 0) MoneyMath.ratioBp((startTotal - total).coerceAtLeast(0), startTotal) else 0,
            missingRates = missing,
            budgetUzs = budget,
            safeShareBp = safe,
            livingAtRisk = settings.monthlyIncome > 0 && settings.livingMinimum > 0 && settings.debtShareBp > safe,
            lines = lines,
            results = results,
        )
    }
}

/** To'lov yozish: qoldiq kamayadi, nolga yetsa qarz yopiladi. */
object Ledger {
    fun applyPayment(debt: Debt, amount: Long, on: LocalDate): Debt {
        require(amount > 0) { "to'lov musbat bo'lishi kerak" }
        val left = (debt.balance - amount).coerceAtLeast(0)
        return debt.copy(balance = left, closedOn = if (left == 0L) on.toString() else debt.closedOn)
    }

    /** To'lovni bekor qilish (xato yozilgan bo'lsa): qoldiq tiklanadi va qarz qayta ochiladi. */
    fun revertPayment(debt: Debt, amount: Long): Debt =
        debt.copy(balance = debt.balance + amount, closedOn = null)
}

object UzDates {
    private val months = listOf(
        "yanvar", "fevral", "mart", "aprel", "may", "iyun",
        "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
    )

    /** «2029-yil mart». */
    fun yearMonth(ym: YearMonth): String = "${ym.year}-yil ${months[ym.monthValue - 1]}"

    /** «31-oktabr, 2026». */
    fun date(d: LocalDate): String = "${d.dayOfMonth}-${months[d.monthValue - 1]}, ${d.year}"

    /** Simulyatsiya oyi (1 = joriy oy) → kalendar oyi. */
    fun monthOf(planMonth: Int, now: YearMonth): YearMonth = now.plusMonths((planMonth - 1).coerceAtLeast(0).toLong())

    /** «2 yil 3 oy», «11 oy». */
    fun duration(months: Int): String {
        val y = months / 12
        val m = months % 12
        return when {
            y == 0 -> "$m oy"
            m == 0 -> "$y yil"
            else -> "$y yil $m oy"
        }
    }
}

object DueDates {
    /** Keyingi to'lov sanasi: oyda bunday kun bo'lmasa (31-fevral) — oyning oxirgi kuni. */
    fun next(dueDay: Int, today: LocalDate): LocalDate {
        fun inMonth(ym: YearMonth): LocalDate = ym.atDay(dueDay.coerceIn(1, ym.lengthOfMonth()))
        val thisMonth = inMonth(YearMonth.from(today))
        return if (!thisMonth.isBefore(today)) thisMonth else inMonth(YearMonth.from(today).plusMonths(1))
    }
}
