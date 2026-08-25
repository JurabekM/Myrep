package uz.distribos.domain

import java.math.BigDecimal
import java.math.RoundingMode

/**
 * Domen qoidalari — buyurtma holati, narx, chegirma, qoldiq, qarzdorlik.
 *
 * Bu fayl Python `distribos/domain/rules.py` ning KOTLIN NUSXASI va u
 * bilan bir xil natija berishi SHART. Ikki tomon farq qilsa, telefonda
 * hisoblangan buyurtma summasi desktopda boshqacha chiqadi — bu esa
 * sinxronizatsiyada tuzatib bo'lmaydigan xato.
 *
 * Moslikni `RulesParityTest` qulflaydi: u Python generatsiya qilgan
 * vektorlarni o'qib solishtiradi.
 *
 * Pul BUTUN son (tiyin). Suzuvchi nuqta ishlatilmaydi.
 */

/** Buyurtma holati. */
enum class OrderState {
    DRAFT, CONFIRMED, APPROVED, ALLOCATED, PICKED, SHIPPED,
    DELIVERED, PARTIALLY_RETURNED, RETURNED, CANCELLED;

    companion object {
        fun from(value: String): OrderState =
            entries.firstOrNull { it.name == value }
                ?: throw DomainException("Noma'lum buyurtma holati: $value")
    }
}

/** Ombor harakati turi. */
enum class MovementType {
    RECEIPT, SALE, RETURN_IN, RETURN_OUT, TRANSFER_OUT, TRANSFER_IN,
    WRITE_OFF, ADJUSTMENT, RESERVATION, RELEASE;

    companion object {
        fun from(value: String): MovementType =
            entries.firstOrNull { it.name == value }
                ?: throw DomainException("Noma'lum harakat turi: $value")
    }
}

class DomainException(message: String) : Exception(message)

class IllegalStateTransitionException(message: String) : Exception(message)

object OrderRules {

    /** Ruxsat etilgan o'tishlar. Bu yerda yo'q o'tish RAD ETILADI. */
    val TRANSITIONS: Map<OrderState, Set<OrderState>> = mapOf(
        OrderState.DRAFT to setOf(OrderState.CONFIRMED, OrderState.CANCELLED),
        OrderState.CONFIRMED to setOf(OrderState.APPROVED, OrderState.CANCELLED),
        OrderState.APPROVED to setOf(OrderState.ALLOCATED, OrderState.CANCELLED),
        OrderState.ALLOCATED to setOf(OrderState.PICKED, OrderState.CANCELLED),
        OrderState.PICKED to setOf(OrderState.SHIPPED, OrderState.CANCELLED),
        OrderState.SHIPPED to setOf(OrderState.DELIVERED),
        OrderState.DELIVERED to setOf(OrderState.PARTIALLY_RETURNED, OrderState.RETURNED),
        OrderState.PARTIALLY_RETURNED to setOf(OrderState.RETURNED),
        // Yakuniy holatlar — chiqish yo'q.
        OrderState.RETURNED to emptySet(),
        OrderState.CANCELLED to emptySet(),
    )

    val TERMINAL: Set<OrderState> = setOf(OrderState.RETURNED, OrderState.CANCELLED)

    fun canTransition(current: OrderState, target: OrderState): Boolean =
        target in (TRANSITIONS[current] ?: emptySet())

    /**
     * Noqonuniy o'tishda xato.
     *
     * Bu tekshiruv sinxronizatsiyada ham ishlaydi: peer'dan kelgan
     * noqonuniy o'tish qo'llanmaydi va konflikt sifatida ko'rsatiladi.
     */
    fun assertTransition(current: OrderState, target: OrderState) {
        if (!canTransition(current, target)) {
            val allowed = TRANSITIONS[current].orEmpty().map { it.name }.sorted()
            throw IllegalStateTransitionException(
                "${current.name} -> ${target.name} mumkin emas. " +
                    "Ruxsat etilgan: ${allowed.ifEmpty { listOf("yakuniy holat") }}"
            )
        }
    }

    fun isTerminal(state: OrderState): Boolean = state in TERMINAL
}

object PricingRules {

    /** Mijoz toifasi -> mahsulotdagi narx maydoni. */
    val PRICE_TIERS: Map<String, String> = mapOf(
        "retail" to "retail_price",
        "wholesale" to "wholesale_price",
        "agent" to "agent_price",
    )

    /**
     * Mijoz toifasiga mos narxni tanlaydi (tiyinda).
     *
     * Narx umuman yo'q bo'lsa xato: 0 so'mga sotishni jimgina ruxsat
     * berish moliyaviy teshik ochadi.
     */
    fun resolveUnitPrice(prices: Map<String, Long>, priceTier: String): Long {
        val field = PRICE_TIERS[priceTier] ?: "wholesale_price"
        for (candidate in listOf(field, "wholesale_price", "retail_price")) {
            val price = prices[candidate] ?: 0L
            if (price > 0) return price
        }
        throw DomainException("Mahsulot uchun narx belgilanmagan")
    }

    /**
     * Qator summasi (tiyinda, butun son).
     *
     * Yaxlitlash HALF_UP — Python `ROUND_HALF_UP` bilan bir xil.
     */
    fun lineTotal(quantity: String, unitPrice: Long, discountPercent: String = "0"): Long {
        val amount = BigDecimal(quantity)
        val discount = BigDecimal(discountPercent)
        if (amount < BigDecimal.ZERO) throw DomainException("Miqdor manfiy bo'lishi mumkin emas")
        if (discount < BigDecimal.ZERO || discount > BigDecimal(100)) {
            throw DomainException("Chegirma 0-100% oralig'ida bo'lishi kerak")
        }
        val gross = amount.multiply(BigDecimal(unitPrice))
        val net = gross.multiply(BigDecimal(100).subtract(discount))
            .divide(BigDecimal(100), 10, RoundingMode.HALF_UP)
        return net.setScale(0, RoundingMode.HALF_UP).toLong()
    }

    data class OrderTotals(val subtotal: Long, val discountTotal: Long, val total: Long)

    data class LineInput(
        val quantity: String,
        val unitPrice: Long,
        val discountPercent: String = "0",
    )

    fun computeOrderTotals(lines: List<LineInput>): OrderTotals {
        var subtotal = 0L
        var total = 0L
        for (line in lines) {
            val gross = BigDecimal(line.quantity)
                .multiply(BigDecimal(line.unitPrice))
                .setScale(0, RoundingMode.HALF_UP)
                .toLong()
            subtotal += gross
            total += lineTotal(line.quantity, line.unitPrice, line.discountPercent)
        }
        return OrderTotals(subtotal, subtotal - total, total)
    }
}

object CreditRules {

    data class CreditCheck(
        val allowed: Boolean,
        val currentDebt: Long,
        val creditLimit: Long,
        val orderTotal: Long,
        val reason: String = "",
    ) {
        val projectedDebt: Long get() = currentDebt + orderTotal
    }

    /**
     * `creditLimit == 0` — limit belgilanmagan, cheklov yo'q.
     * Manfiy qarz = oldindan to'lov, bu ruxsat etiladi.
     */
    fun check(currentDebt: Long, creditLimit: Long, orderTotal: Long): CreditCheck {
        val projected = currentDebt + orderTotal
        if (creditLimit <= 0) {
            return CreditCheck(true, currentDebt, creditLimit, orderTotal)
        }
        if (projected > creditLimit) {
            return CreditCheck(
                false, currentDebt, creditLimit, orderTotal,
                reason = "Kredit limiti oshib ketadi",
            )
        }
        return CreditCheck(true, currentDebt, creditLimit, orderTotal)
    }
}

object StockRules {

    /** Qaysi harakatlar qoldiqni oshiradi (+1) yoki kamaytiradi (-1). */
    val MOVEMENT_SIGN: Map<MovementType, Int> = mapOf(
        MovementType.RECEIPT to +1,
        MovementType.RETURN_IN to +1,
        MovementType.TRANSFER_IN to +1,
        MovementType.SALE to -1,
        MovementType.RETURN_OUT to -1,
        MovementType.TRANSFER_OUT to -1,
        MovementType.WRITE_OFF to -1,
        MovementType.ADJUSTMENT to +1,   // ishorasi miqdorning o'zida
        MovementType.RESERVATION to 0,
        MovementType.RELEASE to 0,
    )

    data class Stock(val onHand: BigDecimal, val reserved: BigDecimal) {
        val available: BigDecimal get() = onHand.subtract(reserved)
    }

    /**
     * Qoldiq HECH QACHON to'g'ridan-to'g'ri yozilmaydi — u harakatlar
     * ketma-ketligidan hisoblanadi. Shuning uchun ikki qurilma bir vaqtda
     * sotsa ham natija to'g'ri chiqadi (yo'qolgan yangilanish bo'lmaydi).
     */
    fun computeStock(movements: List<Pair<MovementType, String>>): Stock {
        var onHand = BigDecimal.ZERO
        var reserved = BigDecimal.ZERO
        for ((type, quantity) in movements) {
            val amount = BigDecimal(quantity)
            when (type) {
                MovementType.RESERVATION -> reserved = reserved.add(amount)
                MovementType.RELEASE -> reserved = reserved.subtract(amount)
                else -> {
                    val sign = MOVEMENT_SIGN[type]
                        ?: throw DomainException("Noma'lum harakat turi: $type")
                    onHand = onHand.add(amount.multiply(BigDecimal(sign)))
                }
            }
        }
        return Stock(onHand, reserved)
    }

    fun isAvailable(
        stock: Stock, requested: String, allowNegative: Boolean = false,
    ): Boolean = allowNegative || stock.available >= BigDecimal(requested)
}

object FinanceRules {

    /** Mijoz qarzi = buyurtmalar - sof to'lovlar. Manfiy = avans. */
    fun customerDebt(ordersTotal: Long, paymentsTotal: Long, returnsTotal: Long = 0): Long =
        ordersTotal - paymentsTotal - returnsTotal

    /**
     * To'lovni ochiq buyurtmalarga taqsimlaydi (eng eskisidan boshlab).
     * Ortib qolgan summa taqsimlanmaydi — u avans bo'lib qoladi.
     */
    fun allocatePayment(
        amount: Long, openOrders: List<Pair<String, Long>>,
    ): List<Pair<String, Long>> {
        if (amount < 0) throw DomainException("To'lov summasi manfiy bo'lishi mumkin emas")

        val allocations = mutableListOf<Pair<String, Long>>()
        var remaining = amount
        for ((orderId, outstanding) in openOrders) {
            if (remaining <= 0) break
            if (outstanding <= 0) continue
            val applied = minOf(remaining, outstanding)
            allocations += orderId to applied
            remaining -= applied
        }
        return allocations
    }
}
