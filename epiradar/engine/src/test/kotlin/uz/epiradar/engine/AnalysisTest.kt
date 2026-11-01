package uz.epiradar.engine

import uz.epiradar.engine.Fixtures.NOW
import uz.epiradar.engine.Fixtures.countries
import uz.epiradar.engine.Fixtures.signal
import uz.epiradar.engine.model.SignalFlag
import uz.epiradar.engine.model.SourceId
import uz.epiradar.engine.model.ThreatLevel
import uz.epiradar.engine.model.TrendStatus
import uz.epiradar.engine.risk.EventClusterer
import uz.epiradar.engine.risk.RiskScorer
import uz.epiradar.engine.trend.Aberration
import uz.epiradar.engine.trend.FluNetSource
import uz.epiradar.engine.trend.FluWeek
import uz.epiradar.engine.trend.TrendAnalyzer
import java.time.Duration
import java.time.LocalDate
import kotlin.math.PI
import kotlin.math.cos
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class AnalysisTest {
    private val scorer = RiskScorer(Fixtures.catalog, countries)

    @Test
    fun `countries resource and geography`() {
        val uz = countries["UZB"]!!
        assertEquals("O'zbekiston", uz.nameUz)
        assertEquals(setOf("AFG", "KAZ", "KGZ", "TJK", "TKM"), uz.borders.toSet())
        assertTrue(countries.isSecondDegree("UZB", "RUS"))
        assertEquals(1.0, countries.proximity("UZB", "UZB"))
        assertEquals(0.9, countries.proximity("UZB", "KAZ"))
        assertEquals(0.75, countries.proximity("UZB", "RUS"))
        assertEquals(0.25, countries.proximity("UZB", "BRA"))
        val km = countries.distanceKm("UZB", "SAU")!!
        assertTrue(km in 2000..3500, "UZB–SAU $km km")
    }

    @Test
    fun `clusterer merges corroborating signals and bridges countries`() {
        val signals =
            listOf(
                signal("a", "ebola", listOf("COD"), NOW.minus(Duration.ofDays(30))),
                signal("b", "ebola", listOf("KEN"), NOW.minus(Duration.ofDays(20)), SourceId.CDC_TRAVEL),
                signal("c", "ebola", listOf("COD", "KEN"), NOW.minus(Duration.ofDays(5)), SourceId.ECDC),
                signal("d", "dengue", listOf("COD"), NOW),
                signal("e", "other", listOf("COD"), NOW),
                signal("f", "other", listOf("COD"), NOW),
                signal("g", "ebola", listOf("COD"), NOW.minus(Duration.ofDays(200))),
            )
        val clusters = EventClusterer.cluster(signals)
        val ebola = clusters.filter { it.diseaseId == "ebola" }
        assertEquals(2, ebola.size, "200 kunlik eski xabar alohida qoladi")
        assertEquals(setOf("a", "b", "c"), ebola.maxBy { it.signals.size }.signals.map { it.id }.toSet())
        assertEquals(2, clusters.count { it.diseaseId == "other" }, "'other' hech qachon birlashtirilmaydi")
    }

    @Test
    fun `scores rank proximity, hazard, corroboration and recency`() {
        fun score(
            disease: String,
            country: String,
            ageDays: Long = 1,
            flags: Set<SignalFlag> = emptySet(),
        ) = scorer.assess(
            EventClusterer.cluster(listOf(signal("x", disease, listOf(country), NOW.minus(Duration.ofDays(ageDays)), flags = flags))).single(),
            "UZB",
            NOW,
        ).assessment

        val homeX = score("disease_x", "UZB", flags = setOf(SignalFlag.UNKNOWN_ETIOLOGY, SignalFlag.CLUSTER))
        val farX = score("disease_x", "BRA", flags = setOf(SignalFlag.UNKNOWN_ETIOLOGY, SignalFlag.CLUSTER))
        val homeDengue = score("dengue", "UZB")
        val oldX = score("disease_x", "UZB", ageDays = 90, flags = setOf(SignalFlag.UNKNOWN_ETIOLOGY, SignalFlag.CLUSTER))

        assertEquals(homeX.globalScore, farX.globalScore, "global ball joylashuvga bog'liq emas")
        assertTrue(homeX.personalScore > farX.personalScore)
        assertTrue(homeX.personalScore > homeDengue.personalScore)
        assertTrue(oldX.personalScore < homeX.personalScore / 4, "90 kunlik xabar ~1/8 ga so'nadi")
        assertEquals(0, homeX.distanceKm)
        assertTrue(homeX.personalLevel >= ThreatLevel.WARNING, "o'z mamlakatida noma'lum klaster: ${homeX.personalScore}")
        assertTrue(farX.personalLevel <= ThreatLevel.ADVISORY, "uzoqdagi: ${farX.personalScore}")
        assertTrue(homeX.reasons.any { it.contains("Sizning mamlakatingizda") })
    }

    @Test
    fun `cdc level 4 raises intensity`() {
        val base = signal("x", "ebola", listOf("COD"), NOW, SourceId.CDC_TRAVEL)
        val l1 = scorer.assess(EventClusterer.cluster(listOf(base.copy(travelLevel = 1))).single(), "UZB", NOW)
        val l4 = scorer.assess(EventClusterer.cluster(listOf(base.copy(travelLevel = 4))).single(), "UZB", NOW)
        assertTrue(l4.assessment.globalScore > l1.assessment.globalScore)
        assertTrue(l4.assessment.reasons.any { it.startsWith("CDC sayohat darajasi: 4") })
    }

    @Test
    fun `combine keeps the top score dominant`() {
        assertEquals(0, RiskScorer.combine(emptyList()))
        assertEquals(50, RiskScorer.combine(listOf(50)))
        assertEquals(55, RiskScorer.combine(listOf(40, 50, 30)))
        assertEquals(57, RiskScorer.combine(listOf(50, 50, 50)))
        assertEquals(100, RiskScorer.combine(listOf(95, 90, 90)))
        assertEquals("6 200", RiskScorer.formatKm(6234))
        assertEquals("4 300", RiskScorer.formatKm(4284))
        assertEquals("0", RiskScorer.formatKm(0))
    }

    @Test
    fun `ears c2 flags a sharp rise only`() {
        val flat = List(12) { 5.0 } + listOf(5.5)
        assertEquals(false, Aberration.earsC2(flat, flat.lastIndex)!!.alarm)
        val spike = List(12) { 5.0 } + listOf(20.0)
        assertEquals(true, Aberration.earsC2(spike, spike.lastIndex)!!.alarm)
        assertNull(Aberration.earsC2(spike, 5), "baza uchun tarix yetarli emas")
        val sparse = List(9) { null } + listOf(1.0, null, null, 30.0)
        assertNull(Aberration.earsC2(sparse, sparse.lastIndex))
    }

    @Test
    fun `historical limit uses seasonal baseline`() {
        val r = Aberration.historicalLimit(30.0, listOf(10.0, 12.0, 11.0, 9.0, 13.0, 10.0))!!
        assertTrue(r.alarm)
        assertTrue(!Aberration.historicalLimit(12.0, listOf(10.0, 12.0, 11.0, 9.0, 13.0, 10.0))!!.alarm)
        assertNull(Aberration.historicalLimit(30.0, listOf(1.0, 2.0)))
    }

    private fun seasonalWeeks(
        end: LocalDate,
        years: Int,
        lastValue: Double? = null,
    ): List<FluWeek> {
        val n = years * 52
        return (0 until n).map { i ->
            val week = end.minusWeeks((n - 1 - i).toLong())
            // Qishda yuqori (≈25%), yozda past (≈2%) musbatlik.
            val seasonal = 13.5 + 11.5 * cos(2 * PI * (week.dayOfYear - 20) / 365.0)
            val pct = if (i == n - 1 && lastValue != null) lastValue else seasonal
            FluWeek(week, 200, (pct * 2).toInt(), 0, 0)
        }
    }

    @Test
    fun `seasonal flu peak is normal but an off-season surge is unusual`() {
        val analyzer = TrendAnalyzer(countries)
        val winter = LocalDate.parse("2026-01-19")
        val normal = analyzer.analyze("KAZ", seasonalWeeks(winter, 4), winter.plusDays(10))
        assertEquals(TrendStatus.NORMAL, normal.series.status, normal.series.note)
        assertTrue(normal.signals.isEmpty())

        val summer = LocalDate.parse("2026-07-20")
        val surge = analyzer.analyze("KAZ", seasonalWeeks(summer, 4, lastValue = 22.0), summer.plusDays(10))
        assertEquals(TrendStatus.UNUSUAL, surge.series.status, surge.series.note)
        val s = surge.signals.single()
        assertEquals("influenza", s.diseaseId)
        assertEquals(SourceId.WHO_FLUNET, s.source)
        assertTrue(s.title.contains("Qozog'iston"))
        assertTrue(surge.series.anomalies.isNotEmpty())
    }

    @Test
    fun `sparse or stale flunet data is reported as no data and h5 is signalled`() {
        val analyzer = TrendAnalyzer(countries)
        val end = LocalDate.parse("2026-10-12")
        val weeks = listOf(FluWeek(end, 3, 0, 1, 0), FluWeek(end.minusWeeks(1), 0, 0, 0, 0))
        val out = analyzer.analyze("UZB", weeks, end.plusDays(5))
        assertEquals(TrendStatus.NO_DATA, out.series.status)
        val novel = out.signals.single()
        assertEquals("avian_flu", novel.diseaseId)
        assertTrue(SignalFlag.NOVEL_PATHOGEN in novel.flags)
        assertEquals(listOf(end.toString()), out.series.novelFluWeeks)

        val stale = analyzer.analyze("KAZ", seasonalWeeks(LocalDate.parse("2026-01-19"), 2), LocalDate.parse("2026-10-30"))
        assertEquals(TrendStatus.NO_DATA, stale.series.status)
    }

    @Test
    fun `flunet rows are aggregated per week`() {
        val weeks = FluNetSource().parse(Fixtures.text("flunet_kaz.json"))
        assertEquals(weeks.map { it.weekStart }.sorted(), weeks.map { it.weekStart })
        assertEquals(weeks.size, weeks.map { it.weekStart }.toSet().size)
        val w = weeks.first { it.weekStart == LocalDate.parse("2026-10-12") }
        assertEquals(281 + 86, w.tested)
        val oct5 = weeks.first { it.weekStart == LocalDate.parse("2026-10-05") }
        assertTrue(oct5.positive >= 1)
        assertNotNull(oct5.positivity)
        val trend = TrendAnalyzer(countries).analyze("KAZ", weeks, LocalDate.parse("2026-10-31"))
        assertTrue(trend.series.points.isNotEmpty())
        assertTrue(trend.series.status != TrendStatus.NO_DATA, trend.series.note)
    }
}
