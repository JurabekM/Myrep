package uz.havoradar.engine

import kotlinx.coroutines.test.runTest
import uz.havoradar.engine.Fixtures.FakeHttp
import uz.havoradar.engine.Fixtures.JULY
import uz.havoradar.engine.Fixtures.NOVEMBER
import uz.havoradar.engine.Fixtures.Scenario
import uz.havoradar.engine.model.RiskLevel
import uz.havoradar.engine.model.Settings
import uz.havoradar.engine.model.SourceId
import uz.havoradar.engine.model.Vulnerability
import uz.havoradar.engine.sources.OpenMeteo
import uz.havoradar.engine.sources.SourceFormatException
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class EngineTest {
    private fun engine(
        http: FakeHttp,
        now: Instant,
    ) = Engine(http, Fixtures.places, Fixtures.guide) { now }

    @Test
    fun `real air quality responses parse`() {
        val tash = OpenMeteo.parseAir(Fixtures.text("air_tashkent_2026-11-02.json"), "tashkent", NOVEMBER)
        assertEquals(18000, tash.utcOffsetSeconds)
        assertEquals(96, tash.times.size)
        assertEquals(LocalDateTime.parse("2026-11-01T00:00"), tash.times.first())
        assertTrue(tash.pm25.all { it != null } && tash.dust.all { it != null })
        val delhi = OpenMeteo.parseAir(Fixtures.text("air_delhi_2026-11-02.json"), "delhi", NOVEMBER)
        assertEquals(19800, delhi.utcOffsetSeconds)
        assertTrue(delhi.pm25.filterNotNull().max() > 100)

        val w = OpenMeteo.parseWeather(Fixtures.text("weather_tashkent_2026-07.json"), "tashkent", JULY)
        assertEquals(9 * 24, w.times.size)
        assertEquals(w.times.size, w.uv.size)
    }

    @Test
    fun `source errors and bad formats are reported`() {
        assertFailsWith<SourceFormatException> {
            OpenMeteo.parseWeather("""{"error":true,"reason":"Daily API request limit exceeded."}""", "x", JULY)
        }.also { assertTrue("limit" in it.message!!) }
        assertFailsWith<SourceFormatException> { OpenMeteo.parseAir("<html>", "x", JULY) }
        assertFailsWith<SourceFormatException> {
            OpenMeteo.parseAir("""{"hourly":{"time":["2026-07-15T00:00"],"pm2_5":[1,2],"pm10":[1]}}""", "x", JULY)
        }
        // Ixtiyoriy maydonlar bo'lmasa — null'lar bilan.
        val a = OpenMeteo.parseAir("""{"hourly":{"time":["2026-07-15T00:00"],"pm2_5":[null],"pm10":[12.5]}}""", "x", JULY)
        assertEquals(listOf<Double?>(null), a.pm25)
        assertEquals(listOf<Double?>(null), a.ozone)
    }

    @Test
    fun `urls ask for local time and enough history`() {
        val p = Fixtures.places["tashkent"]!!
        val w = OpenMeteo.weatherUrl(p)
        assertTrue(w.startsWith("https://api.open-meteo.com/v1/forecast?latitude=41.2995&longitude=69.2401"), w)
        assertTrue("past_days=2" in w && "timezone=auto" in w && "relative_humidity_2m" in w)
        val a = OpenMeteo.airUrl(p)
        assertTrue(a.startsWith("https://air-quality-api.open-meteo.com/v1/air-quality?"), a)
        assertTrue("pm2_5" in a && "past_days=1" in a)
    }

    @Test
    fun `july heatwave in Tashkent`() =
        runTest {
            val snap = engine(FakeHttp(Scenario.JULY), JULY).sync(Settings(), null).snapshot
            assertTrue(snap.sources.all { it.ok }, snap.sources.toString())
            val r = snap.main!!
            assertEquals(LocalDateTime.parse("2026-07-15T09:00"), r.localNow)
            assertEquals(LocalDate.parse("2026-07-15"), r.days.first().date)
            assertEquals(7, r.days.size)
            assertEquals(48, r.hours.size)
            assertEquals(LocalDateTime.parse("2026-07-15T09:00"), r.current!!.time)

            val today = r.today!!
            assertEquals(41.5, today.tempMax)
            assertEquals(15, today.feelsPeakHour)
            assertEquals(RiskLevel.WARNING, today.heatRisk!!.baseLevel)
            assertTrue(today.uvMax!! > 9)
            // 14 va 15-iyul — «Xavf» toifasi, 16-iyul — uchinchi kun: qo'shimcha ball.
            val d16 = r.days[1]
            assertTrue(d16.heatRisk!!.reasons.any { "3-kun" in it }, d16.heatRisk.reasons.toString())
            val hottest = r.days.maxBy { it.heatRisk?.baseScore ?: 0 }
            assertEquals(LocalDate.parse("2026-07-17"), hottest.date)
            assertEquals(RiskLevel.EMERGENCY, hottest.heatRisk!!.baseLevel)
            // Tropik tun — issiq kundan KEYINGI tun bo'yicha (16-iyul ertalab ~27,5°C), 15-iyul ertalabgi 26,5°C emas.
            assertTrue(today.heatRisk.reasons.any { "eng past 27" in it || "eng past 28" in it }, today.heatRisk.reasons.toString())
            // Havo: 17-iyulda chang ko'tarilishi; CAMS prognozi 5 kun (oxirgi kunlarda havo bahosi yo'q).
            assertTrue(hottest.airRisk!!.reasons.any { "chang" in it }, hottest.airRisk.reasons.toString())
            assertNull(r.days.last().airRisk)
            assertNotNull(r.days.last().heatRisk)
            // Umumiy daraja — eng yomon xavf.
            assertEquals(maxOf(today.heatRisk.personalScore, today.airRisk!!.personalScore), today.personalScore)

            r.days.forEach { d ->
                println("  ${d.date} ${d.tempMin}..${d.tempMax} his ${"%.1f".format(d.feelsMax)} → issiq ${d.heatRisk?.baseScore} havo ${d.airRisk?.baseScore}")
            }
        }

    @Test
    fun `november real air in Tashkent and Delhi with a failing weather source`() =
        runTest {
            val http = FakeHttp(Scenario.NOVEMBER)
            val snap = engine(http, NOVEMBER).sync(Settings(placeId = "tashkent", extraPlaces = listOf("delhi")), null).snapshot
            assertEquals(4, http.requests.size)
            val weather = snap.sources.first { it.source == SourceId.WEATHER }
            assertFalse(weather.ok)
            assertTrue(weather.error!!.startsWith("Dehli (Hindiston): Server xatosi (HTTP 404)"), weather.error)
            assertTrue(snap.sources.first { it.source == SourceId.AIR }.ok)

            val tash = snap.places[0]
            assertEquals(RiskLevel.CALM, tash.today!!.heatRisk!!.baseLevel)
            assertNotNull(tash.today!!.airRisk)
            val delhi = snap.places[1]
            assertEquals("delhi", delhi.place.id)
            // Dehlida ob-havo yo'q, lekin havo sifati bor: bugun (2-noyabr) — Hindiston vaqti bilan.
            assertEquals(LocalDate.parse("2026-11-02"), delhi.today!!.date)
            assertNull(delhi.today!!.heatRisk)
            assertTrue(delhi.today!!.airRisk!!.baseLevel >= RiskLevel.WARNING, delhi.today!!.airRisk.toString())
            assertTrue(delhi.today!!.airRisk!!.reasons.first().startsWith("PM2.5") || delhi.today!!.airRisk!!.reasons.first().startsWith("PM10"))
            assertTrue(delhi.today!!.air!!.pm25Mean!! > tash.today!!.air!!.pm25Mean!!)
            println("  Toshkent havo: ${tash.today!!.airRisk!!.baseScore} ${tash.today!!.airRisk!!.reasons}")
            println("  Dehli havo: ${delhi.today!!.airRisk!!.baseScore} ${delhi.today!!.airRisk!!.reasons}")
        }

    @Test
    fun `failed source falls back to the previous forecast`() =
        runTest {
            val first = engine(FakeHttp(Scenario.JULY), JULY).sync(Settings(), null)
            val later = JULY.plusSeconds(6 * 3600)
            val second = engine(FakeHttp(Scenario.JULY, failing = setOf("api.open-meteo.com")), later).sync(Settings(), first.state)
            val w = second.snapshot.sources.first { it.source == SourceId.WEATHER }
            assertFalse(w.ok)
            assertTrue(w.stale)
            assertEquals(JULY, w.fetchedAt, "oxirgi muvaffaqiyatli vaqt saqlanadi")
            assertEquals("Toshkent: Server xatosi (HTTP 503)", w.error)
            assertNotNull(second.snapshot.main!!.today!!.heatRisk, "eski prognoz ishlatiladi")
            assertEquals(JULY, second.snapshot.main!!.weatherFetchedAt)

            // Ketma-ket ikkinchi xato: oxirgi muvaffaqiyatli vaqt yo'qolmaydi.
            val again = engine(FakeHttp(Scenario.JULY, failing = setOf("api.open-meteo.com")), later.plusSeconds(3600)).sync(Settings(), second.state)
            assertEquals(JULY, again.snapshot.sources.first { it.source == SourceId.WEATHER }.fetchedAt)

            // 3 kundan eski prognoz ishlatilmaydi.
            val muchLater = JULY.plus(Engine.STALE_MAX).plusSeconds(3600)
            val third = engine(FakeHttp(Scenario.JULY, failing = setOf("api.open-meteo.com")), muchLater).sync(Settings(), first.state)
            assertFalse(third.snapshot.sources.first { it.source == SourceId.WEATHER }.stale)
            assertNull(third.snapshot.main!!.weatherFetchedAt)
        }

    @Test
    fun `reassess applies a new profile offline`() =
        runTest {
            val e = engine(FakeHttp(Scenario.JULY), JULY)
            val synced = e.sync(Settings(), null)
            val again = e.reassess(synced.state, Settings(profile = setOf(Vulnerability.ELDERLY)))
            val before = synced.snapshot.main!!.today!!
            val after = again.main!!.today!!
            assertEquals(before.heatRisk!!.baseScore, after.heatRisk!!.baseScore)
            assertTrue(after.heatRisk.personalScore > before.heatRisk.personalScore)
            assertEquals(setOf(Vulnerability.ELDERLY), again.profile)
        }

    @Test
    fun `unknown places are ignored`() =
        runTest {
            val snap = engine(FakeHttp(Scenario.JULY), JULY).sync(Settings(placeId = "tashkent", extraPlaces = listOf("atlantis")), null).snapshot
            assertEquals(listOf("tashkent"), snap.places.map { it.place.id })
        }

    @Test
    fun `places and guide resources are valid`() {
        val all = Fixtures.places.all
        assertEquals(all.size, all.map { it.id }.toSet().size)
        assertTrue(all.size >= 25)
        assertTrue(all.all { it.lat in -90.0..90.0 && it.lon in -180.0..180.0 })
        // O'zbekiston shaharlari taxminiy chegaralar ichida.
        assertTrue(all.filter { !it.abroad }.all { it.lat in 37.0..45.6 && it.lon in 55.9..73.2 })
        assertEquals("Toshkent", Fixtures.places.name("tashkent"))
        assertTrue(listOf("heat_stroke", "heat_exhaustion", "air", "uv").all { it in Fixtures.guide.ids })
    }
}
