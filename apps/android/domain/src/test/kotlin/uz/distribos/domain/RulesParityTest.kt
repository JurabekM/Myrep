package uz.distribos.domain

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.math.BigDecimal

/**
 * Kotlin domen qoidalari Python bilan bir xil natija berishini qulflaydi.
 *
 * Bu test yiqilsa: telefonda hisoblangan summa desktopda boshqacha
 * chiqadi. Ikkala qiymat ham to'g'ri imzolangan bo'ladi, ya'ni
 * sinxronizatsiya buni "konflikt" deb ham ko'rsatmaydi — jimgina
 * noto'g'ri raqam qoladi. Shuning uchun bu test kritik.
 *
 * Vektorlar `tools/gen_rules_parity.py` da generatsiya qilinadi.
 */
class RulesParityTest {

    private val vectors: JSONObject by lazy {
        val stream = requireNotNull(
            javaClass.classLoader?.getResourceAsStream("rules_parity.json")
        ) { "rules_parity.json topilmadi — `python tools/gen_rules_parity.py` ni ishga tushiring" }
        JSONObject(stream.bufferedReader().use { it.readText() })
    }

    private fun JSONArray.objects(): List<JSONObject> =
        (0 until length()).map { getJSONObject(it) }

    // --- holat mashinasi ---------------------------------------------------

    @Test
    fun `order state transitions match python`() {
        var checked = 0
        for (case in vectors.getJSONArray("order_transitions").objects()) {
            val current = OrderState.from(case.getString("current"))
            val target = OrderState.from(case.getString("target"))
            assertEquals(
                "o'tish farq qildi: ${current.name} -> ${target.name}",
                case.getBoolean("allowed"),
                OrderRules.canTransition(current, target),
            )
            checked++
        }
        assertTrue("vektorlar bo'sh", checked >= 100)
    }

    @Test
    fun `order states match python`() {
        val expected = vectors.getJSONArray("order_states")
            .let { array -> (0 until array.length()).map { array.getString(it) } }
        assertEquals(
            "holatlar ro'yxati farq qildi",
            expected.sorted(), OrderState.entries.map { it.name }.sorted(),
        )
    }

    @Test
    fun `movement types match python`() {
        val expected = vectors.getJSONArray("movement_types")
            .let { array -> (0 until array.length()).map { array.getString(it) } }
        assertEquals(
            "harakat turlari farq qildi",
            expected.sorted(), MovementType.entries.map { it.name }.sorted(),
        )
    }

    // --- narx va yaxlitlash ------------------------------------------------

    @Test
    fun `line totals match python including rounding edges`() {
        for (case in vectors.getJSONArray("line_totals").objects()) {
            val actual = PricingRules.lineTotal(
                case.getString("quantity"),
                case.getLong("unit_price"),
                case.getString("discount_percent"),
            )
            assertEquals(
                "qator summasi farq qildi: ${case.getString("quantity")} x " +
                    "${case.getLong("unit_price")} - ${case.getString("discount_percent")}%",
                case.getLong("line_total"), actual,
            )
        }
    }

    @Test
    fun `order totals match python`() {
        for (case in vectors.getJSONArray("order_totals").objects()) {
            val lines = case.getJSONArray("lines").objects().map {
                PricingRules.LineInput(
                    it.getString("quantity"),
                    it.getLong("unit_price"),
                    it.getString("discount_percent"),
                )
            }
            val totals = PricingRules.computeOrderTotals(lines)
            assertEquals("subtotal farq qildi", case.getLong("subtotal"), totals.subtotal)
            assertEquals("chegirma farq qildi", case.getLong("discount_total"), totals.discountTotal)
            assertEquals("jami farq qildi", case.getLong("total"), totals.total)
        }
    }

    @Test
    fun `price tier resolution matches python`() {
        for (case in vectors.getJSONArray("prices").objects()) {
            val priceMap = case.getJSONObject("prices").let { json ->
                json.keys().asSequence().associateWith { json.getLong(it) }
            }
            val tier = case.getString("price_tier")

            if (case.isNull("error")) {
                assertEquals(
                    "narx farq qildi: $tier",
                    case.getLong("unit_price"),
                    PricingRules.resolveUnitPrice(priceMap, tier),
                )
            } else {
                try {
                    PricingRules.resolveUnitPrice(priceMap, tier)
                    throw AssertionError("narxsiz mahsulot qabul qilindi: $tier")
                } catch (_: DomainException) {
                    // kutilgan — 0 so'mga sotish taqiqlanadi
                }
            }
        }
    }

    // --- kredit ------------------------------------------------------------

    @Test
    fun `credit checks match python`() {
        for (case in vectors.getJSONArray("credit").objects()) {
            val result = CreditRules.check(
                case.getLong("current_debt"),
                case.getLong("credit_limit"),
                case.getLong("order_total"),
            )
            assertEquals("ruxsat farq qildi", case.getBoolean("allowed"), result.allowed)
            assertEquals(
                "kutilayotgan qarz farq qildi",
                case.getLong("projected_debt"), result.projectedDebt,
            )
        }
    }

    // --- ombor -------------------------------------------------------------

    @Test
    fun `stock computation matches python`() {
        for (case in vectors.getJSONArray("stock").objects()) {
            val movements = case.getJSONArray("movements").objects().map {
                MovementType.from(it.getString("type")) to it.getString("quantity")
            }
            val stock = StockRules.computeStock(movements)

            assertEquals(
                "qoldiq farq qildi",
                0, BigDecimal(case.getString("on_hand")).compareTo(stock.onHand),
            )
            assertEquals(
                "rezerv farq qildi",
                0, BigDecimal(case.getString("reserved")).compareTo(stock.reserved),
            )
            assertEquals(
                "mavjud miqdor farq qildi",
                0, BigDecimal(case.getString("available")).compareTo(stock.available),
            )
        }
    }

    // --- moliya ------------------------------------------------------------

    @Test
    fun `payment allocations match python`() {
        for (case in vectors.getJSONArray("payment_allocations").objects()) {
            val orders = case.getJSONArray("open_orders").objects().map {
                it.getString("order_id") to it.getLong("outstanding")
            }
            val actual = FinanceRules.allocatePayment(case.getLong("amount"), orders)
            val expected = case.getJSONArray("allocations").objects().map {
                it.getString("order_id") to it.getLong("amount")
            }
            assertEquals("taqsimot farq qildi", expected, actual)
        }
    }
}
