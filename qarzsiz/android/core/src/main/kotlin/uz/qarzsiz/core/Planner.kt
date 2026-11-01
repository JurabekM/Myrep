package uz.qarzsiz.core

import kotlinx.serialization.Serializable

/**
 * Ortgan pulni (majburiy to'lovlardan keyingi qoldiqni) qaysi qarzga yo'naltirish.
 * Majburiy to'lov hamma qarzga doim to'lanadi — «to'xtatmang, kam bo'lsa ham bering».
 */
@Serializable
enum class Strategy(val label: String, val hint: String) {
    AVALANCHE("Ko'chki", "Ortgan pul eng yuqori foizli qarzga. Jami foiz eng kam bo'ladi."),
    SNOWBALL("Qor to'pi", "Ortgan pul eng kichik qarzga. Qarzlar soni tezroq kamayadi."),
    PRO_RATA("Teng ulush", "Ortgan pul qoldiqqa mutanosib, hammasiga bo'lib beriladi."),
    MINIMUM_ONLY("Faqat majburiy", "Faqat oylik to'lovlar, qo'shimcha pulsiz. Taqqoslash uchun."),
}

/** Rejalovchi uchun qarz: hamma summa so'mning kichik birligida. */
@Serializable
data class PlanDebt(
    val id: String,
    val balance: Long,
    val annualRateBp: Int,
    val minPayment: Long,
)

@Serializable
data class SimResult(
    /** Hammasi yopilgan oy (1 dan). Yopilmasa — simulyatsiya to'xtagan oy (`maxMonths` yoki «portlash»). */
    val months: Int,
    /** `false` — byudjet foiz o'sishiga yetmaydi yoki `maxMonths` ichida yopilmaydi. */
    val finished: Boolean,
    val totalInterest: Long,
    val totalPaid: Long,
    /** Har qarz yopilgan oy; yopilmagan — `null`. Kirish tartibida. */
    val payoffMonth: List<Int?>,
    /** 1-oyda har qarzga to'lov (majburiy + qo'shimcha). Kirish tartibida. */
    val firstMonth: List<Long>,
    /** 1-oyda majburiy to'lovlarga byudjet yetmadi. */
    val shortfall: Boolean,
)

/** 70/30 qoidasi: daromadning qancha qismi qarzga. */
object Budget {
    const val DEFAULT_SHARE_BP = 7_000
    const val MIN_SHARE_BP = 1_000
    const val MAX_SHARE_BP = 9_000

    fun debtBudget(income: Long, shareBp: Int): Long =
        if (income <= 0) 0 else MoneyMath.share(income, shareBp.coerceIn(0, 10_000))

    /**
     * Minimal yashash xarajatini buzmaydigan eng katta ulush (pastga yaxlitlanadi).
     * Daromad yashash xarajatiga yetmasa — 0.
     */
    fun safeShareBp(income: Long, livingMinimum: Long): Int {
        if (income <= 0) return 0
        val free = income - livingMinimum.coerceAtLeast(0)
        if (free <= 0) return 0
        return MoneyMath.mulDivFloor(free, MoneyMath.BP_PER_UNIT, income).toInt()
    }

    /**
     * Taklif qilinadigan ulush: joriy ulush yashash minimumini buzmasa — o'zi; aks holda xavfsiz ulush
     * 5% ga pastga yaxlitlanadi (kamida 10%); xavfsiz ulush 10% dan past bo'lsa — aynan o'zi.
     */
    fun suggestedShareBp(income: Long, livingMinimum: Long, currentBp: Int): Int {
        if (income <= 0 || livingMinimum <= 0) return currentBp
        val safe = safeShareBp(income, livingMinimum)
        if (currentBp <= safe) return currentBp
        if (safe < MIN_SHARE_BP) return safe
        return maxOf(MIN_SHARE_BP, safe - safe % 500)
    }
}

object Planner {
    const val MAX_MONTHS = 600

    /** Jami qoldiq boshlang'ichdan shuncha marta oshsa — qarz «portlayapti», simulyatsiya to'xtaydi. */
    const val BLOWUP_FACTOR = 10L

    /** Qo'shimcha to'lov tartibi (strategiya bo'yicha). `bal` — joriy qoldiqlar. */
    private fun order(debts: List<PlanDebt>, bal: LongArray, strategy: Strategy): List<Int> {
        val idx = debts.indices.filter { bal[it] > 0 }
        return when (strategy) {
            Strategy.AVALANCHE -> idx.sortedWith(
                compareByDescending<Int> { debts[it].annualRateBp }.thenBy { bal[it] }.thenBy { debts[it].id },
            )
            Strategy.SNOWBALL -> idx.sortedWith(
                compareBy<Int> { bal[it] }.thenByDescending { debts[it].annualRateBp }.thenBy { debts[it].id },
            )
            Strategy.PRO_RATA, Strategy.MINIMUM_ONLY -> idx.sortedWith(
                compareByDescending<Int> { bal[it] }.thenBy { debts[it].id },
            )
        }
    }

    /**
     * Oylik simulyatsiya. Har oy: (1) foiz qo'shiladi; (2) hamma qarzning majburiy to'lovi —
     * byudjet yetmasa, majburiy to'lovga mutanosib bo'linadi; (3) ortgan pul strategiya bo'yicha.
     * Yopilgan qarzning bo'shagan to'lovi keyingi oylarda boshqa qarzga o'tadi (byudjet o'zgarmaydi).
     */
    fun simulate(
        debts: List<PlanDebt>,
        monthlyBudget: Long,
        strategy: Strategy,
        maxMonths: Int = MAX_MONTHS,
    ): SimResult {
        val n = debts.size
        val bal = LongArray(n) { debts[it].balance.coerceAtLeast(0) }
        val payoff = arrayOfNulls<Int>(n)
        var firstMonth = List(n) { 0L }
        var shortfall = false
        var totalInterest = 0L
        var totalPaid = 0L
        var month = 0
        val limit = bal.sum() * BLOWUP_FACTOR

        while (bal.any { it > 0 } && month < maxMonths) {
            month++
            for (i in 0 until n) {
                if (bal[i] > 0) {
                    val interest = Classifier.monthlyInterest(bal[i], debts[i].annualRateBp)
                    bal[i] += interest
                    totalInterest += interest
                }
            }
            val pay = LongArray(n)
            val req = LongArray(n) { minOf(debts[it].minPayment.coerceAtLeast(0), bal[it]) }
            val sumReq = req.sum()
            var extra: Long
            if (strategy == Strategy.MINIMUM_ONLY) {
                for (i in 0 until n) pay[i] = req[i]
                extra = 0
            } else if (sumReq > monthlyBudget) {
                if (month == 1) shortfall = true
                val budget = monthlyBudget.coerceAtLeast(0)
                for (i in 0 until n) pay[i] = MoneyMath.mulDivFloor(budget, req[i], sumReq)
                var leftover = budget - pay.sum()
                for (i in order(debts, bal, strategy)) {
                    if (leftover == 0L) break
                    if (pay[i] < req[i]) {
                        pay[i]++
                        leftover--
                    }
                }
                extra = 0
            } else {
                for (i in 0 until n) pay[i] = req[i]
                extra = monthlyBudget - sumReq
            }
            for (i in 0 until n) bal[i] -= pay[i]

            if (extra > 0) {
                when (strategy) {
                    Strategy.AVALANCHE, Strategy.SNOWBALL -> {
                        for (i in order(debts, bal, strategy)) {
                            if (extra == 0L) break
                            val p = minOf(extra, bal[i])
                            bal[i] -= p
                            pay[i] += p
                            extra -= p
                        }
                    }
                    Strategy.PRO_RATA -> {
                        val total = bal.sum()
                        if (total > 0) {
                            if (extra >= total) {
                                for (i in 0 until n) {
                                    pay[i] += bal[i]
                                    bal[i] = 0
                                }
                            } else {
                                val share = LongArray(n) { MoneyMath.mulDivFloor(extra, bal[it], total) }
                                for (i in 0 until n) {
                                    bal[i] -= share[i]
                                    pay[i] += share[i]
                                }
                                var rem = extra - share.sum()
                                for (i in order(debts, bal, strategy)) {
                                    if (rem == 0L) break
                                    bal[i]--
                                    pay[i]++
                                    rem--
                                }
                            }
                        }
                    }
                    Strategy.MINIMUM_ONLY -> Unit
                }
            }

            totalPaid += pay.sum()
            if (month == 1) firstMonth = pay.toList()
            for (i in 0 until n) if (bal[i] == 0L && payoff[i] == null) payoff[i] = month
            if (bal.sum() > limit) break
        }
        // Boshidan nol qoldiqli qarzlar.
        for (i in 0 until n) if (bal[i] == 0L && payoff[i] == null) payoff[i] = 0

        return SimResult(
            months = month,
            finished = bal.all { it == 0L },
            totalInterest = totalInterest,
            totalPaid = totalPaid,
            payoffMonth = payoff.toList(),
            firstMonth = firstMonth,
            shortfall = shortfall,
        )
    }
}
