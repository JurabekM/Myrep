package uz.sectorverify.telephony

import app.cash.turbine.test
import io.kotest.matchers.shouldBe
import io.kotest.matchers.types.shouldBeInstanceOf
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Test
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.Rat

class TrafficAndProbeTest {
    private class FakeConnection(url: URL, private val code: Int, private val fail: Boolean) : HttpURLConnection(url) {
        override fun connect() = Unit
        override fun disconnect() = Unit
        override fun usingProxy() = false
        override fun getResponseCode(): Int = if (fail) throw IOException("offline") else code
    }

    @Test
    fun `only https urls without query enable the generator`() {
        TrafficGenerator.isValidUrl("") shouldBe false
        TrafficGenerator.isValidUrl("http://example.com") shouldBe false
        TrafficGenerator.isValidUrl("https://example.com/ping") shouldBe true
        TrafficGenerator.isValidUrl("https://example.com/?imsi=1") shouldBe false
        TrafficGenerator.isValidUrl("not a url") shouldBe false
    }

    @Test
    fun `HEAD ping reports code or error`() {
        var method = ""
        val ok =
            TrafficGenerator("https://example.com", open = { u -> FakeConnection(u, 204, false).also { c -> method = c.requestMethod } })
        ok.ping().shouldBeInstanceOf<TrafficStatus.Ok>().httpCode shouldBe 204
        TrafficGenerator("https://example.com", open = { FakeConnection(it, 0, true) }).ping() shouldBe TrafficStatus.Error("IOException")
        method shouldBe "GET" // ping() jonli ulanishda HEAD qo'yishidan oldingi standart qiymat
    }

    @Test
    fun `disabled generator emits once and completes`() = runTest {
        TrafficGenerator("").run().test {
            awaitItem() shouldBe TrafficStatus.Disabled
            awaitComplete()
        }
    }

    @Test
    fun `capability evaluation`() {
        fun s(t: Long, reg: Boolean, rat: Rat = Rat.LTE, rsrp: Double? = -90.0, ta: Int? = null) =
            CellSample(t, rat, 1300, 1, reg, rsrp, null, null, ta, null, null, t)
        val dev = DeviceInfo("Pixel", "Google", 35, "Tensor", null)
        val samples = (0..10).map { s(it * 1_000_000_000L, true, ta = 3) } + s(0, false, rsrp = null)
        val c = CapabilityEvaluator.evaluate(samples, 60, dev, 1)
        c.measuredRateHz shouldBe 1.0
        c.neighborsReported shouldBe true
        c.neighborRsrpReported shouldBe false
        c.timingAdvanceReported shouldBe true
        c.nrSaFieldsReported shouldBe false
        CapabilityEvaluator.evaluate(listOf(s(0, true, Rat.NR)), 60, dev, 1).let {
            it.nrSaFieldsReported shouldBe true
            it.measuredRateHz shouldBe 1.0 / 60
        }
        CapabilityEvaluator.evaluate(emptyList(), 0, dev, 1).measuredRateHz shouldBe 0.0
    }
}
