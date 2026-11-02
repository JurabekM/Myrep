package uz.havoradar.engine

import uz.havoradar.engine.model.AirDay
import uz.havoradar.engine.model.RiskLevel
import uz.havoradar.engine.model.UvCategory
import uz.havoradar.engine.model.Vulnerability
import uz.havoradar.engine.risk.AirRisk
import uz.havoradar.engine.risk.HeatIndex
import uz.havoradar.engine.risk.HeatRisk
import uz.havoradar.engine.risk.ReportBuilder
import kotlin.math.abs
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

class RiskTest {
    private fun near(
        expected: Double,
        actual: Double,
        tol: Double,
    ) = assertTrue(abs(expected - actual) <= tol, "kutilgan $expected ± $tol, olindi $actual")

    @Test
    fun `heat index matches the NWS chart`() {
        // NWS issiqlik indeksi jadvali (°F): https://www.weather.gov/safety/heat-index
        near(95.0, HeatIndex.fahrenheit(90.0, 50.0), 1.0)
        near(109.0, HeatIndex.fahrenheit(100.0, 40.0), 1.0)
        near(105.0, HeatIndex.fahrenheit(86.0, 90.0), 1.5)
        near(80.0, HeatIndex.fahrenheit(80.0, 40.0), 1.0)
        // 80°F dan past — Steadman'ning oddiy formulasi.
        near(0.5 * (75.0 + 61.0 + 7.0 * 1.2 + 50 * 0.094), HeatIndex.fahrenheit(75.0, 50.0), 1e-9)
        // °C o'giruvi: 32,2°C / 50% ≈ 35°C.
        near(35.0, HeatIndex.celsius(32.2, 50.0), 0.6)
    }

    @Test
    fun `dry heat is never rated below the air temperature`() {
        // 44°C va 12% namlikda NWS indeksi havo haroratidan past — xavf ko'rsatkichi harorat bo'ladi.
        assertTrue(HeatIndex.celsius(44.0, 12.0) < 44.0)
        assertEquals(44.0, HeatIndex.feels(44.0, 12.0))
        assertEquals(30.0, HeatIndex.feels(30.0, null))
        // Namlikda indeks yuqori.
        assertTrue(HeatIndex.feels(35.0, 60.0) > 40.0)
    }

    @Test
    fun `heat score is anchored to NWS categories`() {
        fun base(feels: Double) = HeatRisk.assess(feels, feels, 15, 15.0, 0, emptySet()).baseScore
        assertEquals(0, base(20.0))
        assertEquals(20, base(26.7))
        assertEquals(40, base(32.2))
        assertEquals(60, base(39.4))
        assertEquals(80, base(51.7))
        assertEquals(RiskLevel.WARNING, RiskLevel.of(base(44.0)))
        assertEquals(RiskLevel.ADVISORY, RiskLevel.of(base(36.0)))
    }

    @Test
    fun `tropical nights and long heatwaves raise the score`() {
        val plain = HeatRisk.assess(42.0, 42.0, 15, 19.0, 1, emptySet())
        val night = HeatRisk.assess(42.0, 42.0, 15, 27.0, 1, emptySet())
        val wave = HeatRisk.assess(42.0, 42.0, 15, 27.0, 3, emptySet())
        assertEquals(plain.baseScore + HeatRisk.TROPICAL_BONUS, night.baseScore)
        assertEquals(night.baseScore + HeatRisk.STREAK_BONUS, wave.baseScore)
        assertTrue(night.reasons.any { "tunda" in it.lowercase() }, night.reasons.toString())
        assertTrue(wave.reasons.any { "3-kun" in it }, wave.reasons.toString())
        // Salqin kunda tropik tun qo'shimchasi qo'llanmaydi.
        assertEquals(0, HeatRisk.assess(18.0, 18.0, 15, 21.0, 0, emptySet()).baseScore)
    }

    @Test
    fun `sensitive profile lowers the warning threshold`() {
        val general = HeatRisk.assess(37.0, 37.0, 15, 18.0, 0, emptySet())
        val elderly = HeatRisk.assess(37.0, 37.0, 15, 18.0, 0, setOf(Vulnerability.ELDERLY))
        assertEquals(RiskLevel.ADVISORY, general.personalLevel)
        assertEquals(RiskLevel.WARNING, elderly.personalLevel)
        assertEquals(general.baseScore, elderly.baseScore)
        assertTrue(elderly.reasons.last().contains("65 yoshdan kattalar"))
        // Havo sifatiga sezgir emas guruh (diabet) havo xavfini o'zgartirmaydi.
        val day = AirDay(30.0, 50.0, 90.0, 20.0, 40.0, 0.1, 9)
        assertEquals(AirRisk.assess(day, emptySet())!!.personalScore, AirRisk.assess(day, setOf(Vulnerability.DIABETES))!!.personalScore)
    }

    @Test
    fun `heat advice grows with the level`() {
        assertTrue(HeatRisk.advice(RiskLevel.CALM, emptySet(), 15).isEmpty())
        val watch = HeatRisk.advice(RiskLevel.WATCH, emptySet(), 15)
        val warning = HeatRisk.advice(RiskLevel.WARNING, setOf(Vulnerability.OUTDOOR, Vulnerability.DIABETES), 15)
        assertTrue(watch.size < warning.size)
        assertTrue(warning.any { "103" in it })
        assertTrue(warning.any { "NIOSH" in it })
        assertTrue(warning.any { "Insulin" in it })
        assertTrue(warning.any { "15:00" in it })
    }

    @Test
    fun `air score follows WHO guidelines and the worst pollutant wins`() {
        fun pm25(v: Double) = AirRisk.assess(AirDay(v, null, null, null, null, null, null), emptySet())!!.baseScore
        assertEquals(20, pm25(15.0))
        assertEquals(40, pm25(37.5))
        assertEquals(60, pm25(75.0))
        assertEquals(80, pm25(125.5))
        assertEquals(100, pm25(300.0))

        val ozoneDay = AirDay(10.0, 20.0, 170.0, 10.0, 30.0, null, 14)
        val r = AirRisk.assess(ozoneDay, emptySet())!!
        assertEquals(43, r.baseScore) // 160 → 40, 240 → 60: 170 → 42,5
        assertTrue(r.reasons.first().startsWith("Ozon"), r.reasons.toString())

        val clean = AirRisk.assess(AirDay(8.0, 20.0, 60.0, 10.0, 30.0, 0.1, 8), emptySet())!!
        assertEquals(RiskLevel.CALM, clean.baseLevel)
        assertEquals(listOf("Barcha ko'rsatkichlar JSST tavsiyasi doirasida."), clean.reasons)
        assertTrue(clean.advice.isEmpty())

        val dusty = AirRisk.assess(AirDay(30.0, 160.0, null, null, null, 0.7, 13), emptySet())!!
        assertTrue(dusty.reasons.any { "chang" in it }, dusty.reasons.toString())
        assertTrue(dusty.advice.any { "N95" in it })

        assertNull(AirRisk.assess(AirDay(null, null, 120.0, null, null, null, null), emptySet()))
        // NO₂ 1 soatlik JSST chegarasi.
        assertEquals(50, AirRisk.assess(AirDay(5.0, 10.0, null, 30.0, 210.0, null, null), emptySet())!!.baseScore)
    }

    @Test
    fun `ozone uses the max 8-hour running mean`() {
        val values = List(24) { h -> if (h in 12..19) 160.0 else 40.0 }
        assertEquals(160.0, ReportBuilder.max8h(values))
        assertNull(ReportBuilder.max8h(List(24) { null }))
        // 8 soatlik oynada kamida 6 qiymat kerak.
        assertNull(ReportBuilder.max8h(List(24) { h -> if (h % 2 == 0) 100.0 else null }))
    }

    @Test
    fun `uv categories follow WHO`() {
        assertEquals(UvCategory.LOW, UvCategory.of(2.9))
        assertEquals(UvCategory.MODERATE, UvCategory.of(3.0))
        assertEquals(UvCategory.HIGH, UvCategory.of(7.9))
        assertEquals(UvCategory.VERY_HIGH, UvCategory.of(10.9))
        assertEquals(UvCategory.EXTREME, UvCategory.of(11.0))
    }
}
