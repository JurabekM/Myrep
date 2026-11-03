package uz.havoradar.engine

import kotlinx.coroutines.test.runTest
import uz.havoradar.engine.Fixtures.FakeHttp
import uz.havoradar.engine.Fixtures.JULY
import uz.havoradar.engine.Fixtures.Scenario
import uz.havoradar.engine.alert.AlertPolicy
import uz.havoradar.engine.model.Hazard
import uz.havoradar.engine.model.RiskLevel
import uz.havoradar.engine.model.Settings
import uz.havoradar.engine.model.Snapshot
import uz.havoradar.engine.model.Vulnerability
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class AlertPolicyTest {
    private val policy = AlertPolicy()
    private val morning = LocalTime.of(9, 0)
    private val night = LocalTime.of(23, 30)

    private suspend fun snapshot(
        settings: Settings,
        now: Instant = JULY,
    ): Snapshot = Engine(FakeHttp(Scenario.JULY), Fixtures.places, Fixtures.guide) { now }.sync(settings, null).snapshot

    @Test
    fun `heatwave is announced once, then only on escalation`() =
        runTest {
            val settings = Settings()
            val snap = snapshot(settings)
            val d1 = policy.decide(snap, settings, emptyMap(), firstRun = false, localTime = morning)
            // Bugun (15-iyul) «Xavfli» issiqlik — bitta xabar; ertangi kun to'lqin davomi sifatida jim belgilanadi.
            val heat = d1.notifications.filter { it.key.contains("HEAT") }
            assertEquals(1, heat.size, d1.notifications.toString())
            val n = heat.single()
            assertEquals("Xavfli issiqlik — Toshkent, bugun", n.title)
            assertTrue(n.critical)
            assertTrue("41°C" in n.body || "42°C" in n.body, n.body)
            assertTrue("kun davom etishi kutilmoqda" in n.body, n.body)
            assertEquals(RiskLevel.WARNING, d1.notified[AlertPolicy.key("tashkent", Hazard.HEAT, LocalDate.parse("2026-07-15"))])
            assertEquals(RiskLevel.WARNING, d1.notified[AlertPolicy.key("tashkent", Hazard.HEAT, LocalDate.parse("2026-07-16"))])

            // Xuddi shu ma'lumot bilan qayta sinxronlash — takroriy xabar yo'q.
            val d2 = policy.decide(snap, settings, d1.notified, firstRun = false, localTime = morning)
            assertTrue(d2.notifications.none { it.key.contains("HEAT") }, d2.notifications.toString())

            // Ertasiga: 17-iyul «Favqulodda» bo'ladi — daraja oshgani haqida yangi xabar.
            val next = snapshot(settings, JULY.plusSeconds(24 * 3600))
            val d3 = policy.decide(next, settings, d2.notified, firstRun = false, localTime = morning)
            val esc = d3.notifications.single { it.key.contains("HEAT") }
            assertEquals(RiskLevel.EMERGENCY, esc.level)
            assertTrue(esc.title.startsWith("Favqulodda issiqlik — Toshkent, ertaga"), esc.title)
            assertTrue(esc.body.startsWith("Xavf darajasi oshdi."), esc.body)
        }

    @Test
    fun `no late 'today' heat alert after the peak, tomorrow is still announced`() =
        runTest {
            val settings = Settings()
            // Toshkentda 19:00 — bugungi cho'qqi (15:00) o'tgan.
            val evening = snapshot(settings, Instant.parse("2026-07-15T14:00:00Z"))
            val d = policy.decide(evening, settings, emptyMap(), firstRun = false, localTime = LocalTime.of(19, 0))
            val heat = d.notifications.filter { it.key.contains("HEAT") }
            assertEquals(listOf("tashkent|HEAT|2026-07-16"), heat.map { it.key })
            assertTrue(heat.single().title.endsWith("ertaga"), heat.single().title)
            assertTrue("tashkent|HEAT|2026-07-15" !in d.notified)
        }

    @Test
    fun `quiet hours defer non-emergency alerts until morning`() =
        runTest {
            val settings = Settings()
            val snap = snapshot(settings)
            val quiet = policy.decide(snap, settings, emptyMap(), firstRun = false, localTime = night)
            assertTrue(quiet.notifications.isEmpty())
            assertTrue(quiet.notified.isEmpty(), "kechiktirilgan xabar «yuborilgan» deb belgilanmaydi")
            val morningRun = policy.decide(snap, settings, quiet.notified, firstRun = false, localTime = LocalTime.of(7, 5))
            assertEquals(1, morningRun.notifications.count { it.key.contains("HEAT") })
            // Sokin soatlar o'chirilgan bo'lsa — darhol.
            val off = settings.copy(quietHours = false)
            assertEquals(1, policy.decide(snap, off, emptyMap(), firstRun = false, localTime = night).notifications.size)
        }

    @Test
    fun `first run and disabled notifications mark without sending`() =
        runTest {
            val settings = Settings()
            val snap = snapshot(settings)
            val first = policy.decide(snap, settings, emptyMap(), firstRun = true, localTime = morning)
            assertTrue(first.notifications.isEmpty())
            assertTrue(first.notified.isNotEmpty())
            val disabled = policy.decide(snap, settings.copy(notificationsEnabled = false), emptyMap(), firstRun = false, localTime = morning)
            assertTrue(disabled.notifications.isEmpty())
            assertEquals(first.notified, disabled.notified)
        }

    @Test
    fun `threshold, profile and the per-sync cap`() =
        runTest {
            val strict = Settings(alertThreshold = RiskLevel.EMERGENCY)
            assertTrue(policy.decide(snapshot(strict), strict, emptyMap(), false, morning).notifications.isEmpty())

            // Ehtiyot darajasidan, sezgir profil va 4 ta joy bilan — ko'p xabar, lekin ko'pi bilan 3 + jamlovchi.
            val wide =
                Settings(
                    alertThreshold = RiskLevel.WATCH,
                    profile = setOf(Vulnerability.LUNG),
                    extraPlaces = listOf("delhi"),
                )
            val snap = snapshot(wide)
            val d = policy.decide(snap, wide, emptyMap(), false, morning)
            assertTrue(d.notifications.size <= AlertPolicy.MAX_PER_SYNC + 1)
            assertTrue(d.notifications.take(AlertPolicy.MAX_PER_SYNC).zipWithNext().all { (a, b) -> a.level >= b.level })
            if (d.notifications.size > AlertPolicy.MAX_PER_SYNC) assertEquals("summary", d.notifications.last().key)
            assertTrue(d.notifications.any { it.title.startsWith("Havo ifloslanishi") }, d.notifications.toString())
        }

    @Test
    fun `stale keys are pruned`() =
        runTest {
            val settings = Settings()
            val old =
                mapOf(
                    "tashkent|HEAT|2026-07-01" to RiskLevel.WARNING,
                    "tashkent|HEAT|2026-07-14" to RiskLevel.WARNING,
                    "samarkand|AIR|2026-07-15" to RiskLevel.WARNING,
                )
            val d = policy.decide(snapshot(settings), settings, old, false, morning)
            assertTrue("tashkent|HEAT|2026-07-01" !in d.notified)
            assertTrue("samarkand|AIR|2026-07-15" !in d.notified, "ro'yxatdan chiqqan joy")
            // Kecha xabar qilingan — bugun to'lqin davomi, takror yo'q.
            assertTrue(d.notifications.none { it.key == "tashkent|HEAT|2026-07-15" }, d.notifications.toString())
        }
}
