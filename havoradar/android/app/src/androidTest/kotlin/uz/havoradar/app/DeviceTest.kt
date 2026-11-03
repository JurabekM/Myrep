package uz.havoradar.app

import android.Manifest
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.test.platform.app.InstrumentationRegistry
import androidx.work.ListenableWorker
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.testing.TestListenableWorkerBuilder
import kotlinx.coroutines.runBlocking
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import uz.havoradar.engine.alert.AlertNotification
import uz.havoradar.engine.model.RiskLevel
import uz.havoradar.engine.model.Vulnerability
import java.io.File
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Haqiqiy qurilma/emulyatorda Kotlin qatlami: fon sinxronlash (jonli Open-Meteo), saqlash,
 * bildirishnoma kanallari, WorkManager jadvali va vidjet. CI: tool/emulator_test.sh.
 */
// androidx.test.ext:junit (yangi AndroidJUnit4) Flutter qo'shadigan eski androidx.test:core bilan manifest
// to'qnashuviga olib keladi — runner'dagi AndroidJUnit4 yetarli.
@Suppress("DEPRECATION")
@RunWith(androidx.test.runner.AndroidJUnit4::class)
class DeviceTest {
    private val context: Context = InstrumentationRegistry.getInstrumentation().targetContext
    private val repo get() = Repository.get(context)

    @Before
    fun setUp() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            InstrumentationRegistry
                .getInstrumentation()
                .uiAutomation
                .grantRuntimePermission(context.packageName, Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    @Test
    fun syncWorkerWaitsForOnboarding() {
        File(context.filesDir, "state.json").delete()
        repo.saveSettings("""{"placeId":"tashkent","onboardingDone":false}""")
        val result = runBlocking { TestListenableWorkerBuilder<SyncWorker>(context).build().doWork() }
        assertEquals(ListenableWorker.Result.success(), result)
        assertFalse(File(context.filesDir, "state.json").exists(), "onboarding'dan oldin tarmoqqa chiqilmaydi")
    }

    @Test
    fun syncWorkerFetchesLiveForecastAndPersistsState() {
        File(context.filesDir, "state.json").delete()
        repo.saveSettings("""{"placeId":"tashkent","extraPlaces":["termez"],"onboardingDone":true}""")
        val result = runBlocking { TestListenableWorkerBuilder<SyncWorker>(context).build().doWork() }
        val snapshot = runBlocking { repo.current() }
        assertNotNull(snapshot, "holat fayli yozildi va o'qildi")
        snapshot.sources.forEach { println("HAVORADAR-DEVICE:   ${it.source} ok=${it.ok} ${it.error ?: ""}") }
        // Open-Meteo bepul limiti IP bo'yicha: umumiy CI IP'sida 429 bo'lsa — jonli qism o'tkazib yuboriladi (xato emas).
        val limited = snapshot.sources.none { it.ok } && snapshot.sources.all { it.error.orEmpty().contains("429") }
        assumeTrue("Open-Meteo limiti (HTTP 429) — jonli tekshiruv o'tkazib yuborildi", !limited)
        assertEquals(ListenableWorker.Result.success(), result, "SyncWorker natijasi: ${snapshot.sources}")
        assertTrue(snapshot.sources.all { it.ok }, "manbalar: ${snapshot.sources}")
        assertEquals(listOf("tashkent", "termez"), snapshot.places.map { it.place.id })
        for (p in snapshot.places) {
            val today = p.today
            println("HAVORADAR-DEVICE: ${p.place.name}: bugun ${today?.personalScore} · ${p.days.size} kun · issiq ${today?.heatRisk?.baseScore} havo ${today?.airRisk?.baseScore}")
            assertTrue(p.days.size >= 5, "${p.place.name}: kunlar ${p.days.size}")
            assertNotNull(today, "${p.place.name}: bugungi kun")
            assertNotNull(today.heatRisk, "${p.place.name}: bugungi issiqlik bahosi")
            assertNotNull(today.airRisk, "${p.place.name}: bugungi havo bahosi")
            assertEquals(48, p.hours.size)
        }
        // Qurilmada resurslar to'g'ri yuklangan: ma'lumotnoma va shaharlar.
        assertTrue(repo.catalogJson().contains("\"heat_stroke\"") && repo.catalogJson().contains("\"Termiz\""))
    }

    @Test
    fun notificationChannelsAndCriticalAlert() {
        val nm = context.getSystemService(NotificationManager::class.java)
        val critical = nm.getNotificationChannel(Notifier.CHANNEL_CRITICAL)
        assertNotNull(critical)
        assertEquals(NotificationManager.IMPORTANCE_HIGH, critical.importance)
        assertNotNull(nm.getNotificationChannel(Notifier.CHANNEL_ALERTS))

        val n = AlertNotification("tashkent", "tashkent|HEAT|test", "Xavfli issiqlik — Toshkent, bugun", "Qurilma testi", RiskLevel.WARNING, critical = true)
        Notifier.show(context, n)
        Thread.sleep(500)
        assertTrue(nm.activeNotifications.any { it.id == n.key.hashCode() }, "bildirishnoma ko'rsatildi")
        nm.cancel(n.key.hashCode())
    }

    @Test
    fun settingsAreSanitisedAndScheduleUpdated() {
        val saved =
            repo.saveSettings(
                """{"placeId":"samarkand","syncHours":6,"alertThreshold":"CALM","extraPlaces":["mecca","atlantis"],"profile":["ELDERLY","X"],"onboardingDone":true}""",
            )
        assertEquals("samarkand", saved.placeId)
        assertEquals(6, saved.syncHours)
        assertEquals(RiskLevel.WARNING, saved.alertThreshold, "CALM chegara sifatida qabul qilinmaydi")
        assertEquals(listOf("mecca"), saved.extraPlaces)
        assertEquals(setOf(Vulnerability.ELDERLY), saved.profile)
        val work = WorkManager.getInstance(context).getWorkInfosForUniqueWork("havoradar-sync").get()
        assertTrue(work.any { it.state == WorkInfo.State.ENQUEUED || it.state == WorkInfo.State.RUNNING }, "fon jadvali: $work")
        repo.saveSettings("""{"placeId":"tashkent","syncHours":3,"onboardingDone":true}""")
    }

    @Test
    fun widgetUpdateWithoutWidgetsIsSafe() {
        val snapshot = runBlocking { repo.current() } ?: return
        RiskWidgetProvider.update(context, snapshot)
    }
}
