package uz.qarzsiz.core

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** Oltin vektorlar (`spec/test-vectors`, Python oracle bilan hisoblangan) — Kotlin yadro aynan takrorlaydi. */
class VectorTest {
    private val dir = File(System.getProperty("qarzsiz.vectors") ?: "../../spec/test-vectors")

    private fun cases(suite: String): List<JsonObject> {
        val root = Json.parseToJsonElement(File(dir, "$suite.json").readText()).jsonObject
        assertEquals(suite, root["suite"]!!.jsonPrimitive.content)
        return root["cases"]!!.jsonArray.map { it.jsonObject }.also { assertTrue(it.isNotEmpty()) }
    }

    private val JsonObject.input get() = this["input"]!!.jsonObject
    private val JsonObject.expected get() = this["expected"]!!
    private val JsonObject.name get() = this["name"]!!.jsonPrimitive.content
    private fun JsonElement.l(key: String) = jsonObject[key]!!.jsonPrimitive.long
    private fun JsonElement.i(key: String) = jsonObject[key]!!.jsonPrimitive.int

    @Test
    fun interest() = cases("interest").forEach { c ->
        assertEquals(
            c.expected.jsonPrimitive.long,
            Classifier.monthlyInterest(c.input.l("balance"), c.input.i("annualRateBp")),
            c.name,
        )
    }

    @Test
    fun budget() = cases("budget").forEach { c ->
        val inp = c.input
        assertEquals(c.expected.l("debtBudget"), Budget.debtBudget(inp.l("income"), inp.i("shareBp")), c.name)
        assertEquals(c.expected.i("safeShareBp"), Budget.safeShareBp(inp.l("income"), inp.l("livingMinimum")), c.name)
    }

    @Test
    fun fx() = cases("fx").forEach { c ->
        val rates = FxRates(mapOf(Currency.USD to c.input.l("rate")))
        assertEquals(c.expected.jsonPrimitive.long, rates.toUzs(c.input.l("amount"), Currency.USD), c.name)
    }

    @Test
    fun planner() = cases("planner").forEach { c ->
        val debts = c.input["debts"]!!.jsonArray.map {
            PlanDebt(it.jsonObject["id"]!!.jsonPrimitive.content, it.l("balance"), it.i("annualRateBp"), it.l("minPayment"))
        }
        val r = Planner.simulate(debts, c.input.l("budget"), Strategy.valueOf(c.input["strategy"]!!.jsonPrimitive.content))
        val e = c.expected.jsonObject
        assertEquals(e["months"]!!.jsonPrimitive.int, r.months, "${c.name}: months")
        assertEquals(e["finished"]!!.jsonPrimitive.boolean, r.finished, "${c.name}: finished")
        assertEquals(e["totalInterest"]!!.jsonPrimitive.long, r.totalInterest, "${c.name}: totalInterest")
        assertEquals(e["totalPaid"]!!.jsonPrimitive.long, r.totalPaid, "${c.name}: totalPaid")
        assertEquals(e["shortfall"]!!.jsonPrimitive.boolean, r.shortfall, "${c.name}: shortfall")
        assertEquals((e["firstMonth"] as JsonArray).map { it.jsonPrimitive.long }, r.firstMonth, "${c.name}: firstMonth")
        assertEquals(
            (e["payoffMonth"] as JsonArray).map { if (it is JsonNull) null else it.jsonPrimitive.int },
            r.payoffMonth,
            "${c.name}: payoffMonth",
        )
    }

    @Test
    fun installment() = cases("installment").forEach { c ->
        val inp = c.input
        val r = Installment.analyze(inp.l("cash"), inp.l("down"), inp.l("monthly"), inp.i("months"))
        val e = c.expected
        assertEquals(e.l("financed"), r.financed, c.name)
        assertEquals(e.l("totalPaid"), r.totalPaid, c.name)
        assertEquals(e.l("overpay"), r.overpay, c.name)
        assertEquals(e.i("overpayBp"), r.overpayBp, c.name)
        assertEquals(e.i("nominalAnnualBp"), r.nominalAnnualBp, "${c.name}: nominal")
        assertEquals(e.i("effectiveAnnualBp"), r.effectiveAnnualBp, "${c.name}: effective")
    }
}
