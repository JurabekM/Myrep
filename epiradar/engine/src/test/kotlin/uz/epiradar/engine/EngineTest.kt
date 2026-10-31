package uz.epiradar.engine

import kotlinx.coroutines.test.runTest
import uz.epiradar.engine.Fixtures.NOW
import uz.epiradar.engine.Fixtures.signal
import uz.epiradar.engine.alert.AlertPolicy
import uz.epiradar.engine.json.StoredState
import uz.epiradar.engine.model.Settings
import uz.epiradar.engine.model.SignalFlag
import uz.epiradar.engine.model.SourceId
import uz.epiradar.engine.model.ThreatLevel
import java.time.Duration
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class EngineTest {
    private fun engine(http: Fixtures.FakeHttp = Fixtures.FakeHttp()) = Engine(http, Fixtures.catalog, Fixtures.countries) { NOW }

    @Test
    fun `full sync over real fixtures`() =
        runTest {
            val http = Fixtures.FakeHttp()
            val snap = engine(http).sync(Settings(country = "UZB"), previous = null)

            assertTrue(snap.sources.all { it.ok }, snap.sources.toString())
            assertEquals(SourceId.entries.toSet(), snap.sources.map { it.source }.toSet())
            // Ebola (WHO + ECDC + CDC) — bitta hodisa, bir nechta manba bilan tasdiqlangan.
            val ebola = snap.events.filter { it.diseaseId == "ebola" }.maxBy { it.signals.size }
            assertTrue(ebola.signals.map { it.source }.toSet().size >= 3, ebola.signals.map { it.source }.toString())
            assertTrue("KEN" in ebola.countries && "COD" in ebola.countries)
            assertEquals(4, ebola.travelLevel)
            // O'zbekiston uchun Rossiyadagi noma'lum pnevmoniya uzoq Afrika hodisalaridan oldinroq turadi.
            val rus = snap.events.first { it.diseaseId == "disease_x" }
            assertTrue(rus.assessment.personalScore > snap.events.first { it.diseaseId == "yellow_fever" }.assessment.personalScore)
            assertEquals(snap.events.sortedByDescending { it.assessment.personalScore }.map { it.id }, snap.events.map { it.id })
            assertTrue(snap.globalScore >= snap.events.maxOf { it.assessment.globalScore })
            // Gripp trendlari: o'zi + 5 qo'shni; faqat KAZ fixture'da ma'lumot bor.
            assertEquals(listOf("UZB", "AFG", "KAZ", "KGZ", "TJK", "TKM").toSet(), snap.trends.map { it.country }.toSet())
            assertNotNull(snap.trendsFetchedAt)
            assertEquals(6, http.requests.count { "FLUMART" in it })

            println("— Global: ${snap.globalScore} (${snap.globalLevel.uz}), shaxsiy: ${snap.personalScore} (${snap.personalLevel.uz})")
            snap.events.take(8).forEach { println("  ${it.assessment.personalScore}/${it.assessment.globalScore} ${it.title} ${it.flags}") }
        }

    @Test
    fun `failed source falls back to previous data and trends are reused`() =
        runTest {
            val first = engine().sync(Settings(), null)
            val prev = StoredState(first.generatedAt, first.signals, first.trends, first.trendsFetchedAt, first.sources)
            val http = Fixtures.FakeHttp(failing = setOf("diseaseoutbreaknews"))
            val second = engine(http).sync(Settings(), prev)

            val who = second.sources.first { it.source == SourceId.WHO_DON }
            assertFalse(who.ok)
            assertTrue(who.stale)
            assertEquals("Server xatosi (HTTP 503)", who.error)
            assertTrue(second.signals.any { it.source == SourceId.WHO_DON }, "eski WHO xabarlari saqlanadi")
            assertEquals(0, http.requests.count { "FLUMART" in it }, "12 soatdan yangi trendlar qayta yuklanmaydi")
            assertEquals(first.trends, second.trends)
        }

    @Test
    fun `codec round trip and reassessment for another country`() =
        runTest {
            val e = engine()
            val snap = e.sync(Settings(country = "UZB"), null)
            val json = e.codec.encode(snap).toString()
            val state = e.codec.decodeState(json)!!
            val again = e.reassess(state, Settings(country = "UZB"))
            assertEquals(snap.events.map { it.id to it.assessment }, again.events.map { it.id to it.assessment })

            val congo = e.reassess(state, Settings(country = "COD"))
            val ebolaHere = congo.events.first { it.diseaseId == "ebola" && "COD" in it.countries }
            assertEquals(0, ebolaHere.assessment.distanceKm)
            assertTrue(congo.personalScore > snap.personalScore, "Kongo uchun shaxsiy xavf yuqoriroq")
            assertNull(e.codec.decodeState("""{"schema":999}"""))
            assertNull(e.codec.decodeState("not json"))
        }

    /** Flutter widget testlari uchun haqiqiy yadro chiqishi: `EPIRADAR_EXPORT=../test/fixtures gradle test`. */
    @Test
    fun `export fixtures for flutter tests`() =
        runTest {
            val dir = System.getenv("EPIRADAR_EXPORT") ?: return@runTest
            val e = engine()
            val snap = e.sync(Settings(country = "UZB"), null)
            java.io.File(dir).mkdirs()
            java.io.File(dir, "snapshot.json").writeText(e.codec.encode(snap).toString())
            val catalog =
                kotlinx.serialization.json.buildJsonObject {
                    put("diseases", e.codec.diseases())
                    put("countries", e.codec.countryList())
                    put("levels", e.codec.levels())
                    put("trendCountries", kotlinx.serialization.json.JsonArray(e.trendCountries(Settings()).map { kotlinx.serialization.json.JsonPrimitive(it) }))
                }
            java.io.File(dir, "catalog.json").writeText(catalog.toString())
        }

    @Test
    fun `settings decoding sanitises input`() {
        val codec = engine().codec
        val s = codec.decodeSettings("""{"country":"XXX","alertThreshold":"CALM","syncHours":7,"watchCountries":["KAZ","KAZ","ZZZ","UZB"],"notificationsEnabled":false}""")
        assertEquals("UZB", s.country)
        assertEquals(ThreatLevel.ADVISORY, s.alertThreshold)
        assertEquals(3, s.syncHours)
        assertEquals(listOf("KAZ"), s.watchCountries)
        assertFalse(s.notificationsEnabled)
        assertEquals(Settings(), codec.decodeSettings(null))
        val round = Settings("KAZ", true, ThreatLevel.WARNING, 6, listOf("TUR"), listOf("water"), true, lightTheme = true)
        assertEquals(round, codec.decodeSettings(codec.encodeSettings(round).toString()))
    }

    @Test
    fun `alert policy notifies new and escalated events once`() {
        val e = engine()
        val state =
            StoredState(
                NOW,
                listOf(
                    signal("x1", "disease_x", listOf("UZB"), NOW, flags = setOf(SignalFlag.UNKNOWN_ETIOLOGY, SignalFlag.CLUSTER, SignalFlag.HUMAN_TO_HUMAN)),
                    signal("d1", "dengue", listOf("BRA"), NOW),
                    signal("old", "cchf", listOf("KAZ"), NOW.minus(Duration.ofDays(20)), flags = setOf(SignalFlag.DEATHS)),
                ),
                emptyList(),
                null,
                emptyList(),
            )
        val snap = e.reassess(state, Settings())
        val policy = AlertPolicy()

        val firstRun = policy.decide(snap, Settings(), emptyMap(), firstRun = true, now = NOW)
        val xEvent = snap.events.first { it.diseaseId == "disease_x" }
        val expectFirst = if (xEvent.assessment.personalLevel == ThreatLevel.EMERGENCY) 1 else 0
        assertEquals(expectFirst, firstRun.notifications.size, "birinchi ishga tushishda faqat Favqulodda")
        assertEquals(snap.events.size, firstRun.notified.size)

        val fresh = policy.decide(snap, Settings(), emptyMap(), firstRun = false, now = NOW)
        assertEquals(listOf(xEvent.id), fresh.notifications.map { it.eventId }, "dengue past, CCHF eski")
        assertTrue(fresh.notifications.single().critical)

        val repeat = policy.decide(snap, Settings(), fresh.notified, firstRun = false, now = NOW)
        assertTrue(repeat.notifications.isEmpty(), "takroriy xabar yo'q")

        val escalated = policy.decide(snap, Settings(), mapOf(xEvent.id to ThreatLevel.WATCH), firstRun = false, now = NOW)
        assertTrue(escalated.notifications.single().body.startsWith("Xavf darajasi oshdi"))

        val off = policy.decide(snap, Settings(notificationsEnabled = false), emptyMap(), firstRun = false, now = NOW)
        assertTrue(off.notifications.isEmpty())
        assertEquals(snap.events.size, off.notified.size, "o'chirilgan bo'lsa ham «ko'rilgan» deb belgilanadi")

        val watching = policy.decide(snap, Settings(watchCountries = listOf("BRA"), alertThreshold = ThreatLevel.WATCH), emptyMap(), false, NOW)
        assertTrue(watching.notifications.any { it.eventId.startsWith("dengue") }, "kuzatuv ro'yxatidagi mamlakat")
    }

    @Test
    fun `alert policy caps notifications per sync`() {
        val e = engine()
        val signals = (1..6).map { signal("x$it", "disease_x", listOf(listOf("UZB", "KAZ", "KGZ", "TJK", "TKM", "AFG")[it - 1]), NOW, flags = setOf(SignalFlag.UNKNOWN_ETIOLOGY)) }
        val snap = e.reassess(StoredState(NOW, signals, emptyList(), null, emptyList()), Settings())
        val d = AlertPolicy().decide(snap, Settings(alertThreshold = ThreatLevel.WATCH), emptyMap(), false, NOW)
        assertEquals(AlertPolicy.MAX_PER_SYNC + 1, d.notifications.size)
        assertEquals("summary", d.notifications.last().eventId)
    }
}
