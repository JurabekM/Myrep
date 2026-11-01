package uz.epiradar.app

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
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import uz.epiradar.engine.alert.AlertNotification
import uz.epiradar.engine.model.ThreatLevel
import java.io.File
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Haqiqiy qurilma/emulyatorda Kotlin qatlami: fon sinxronlash (jonli internet), saqlash,
 * bildirishnoma kanallari va WorkManager jadvali. CI: tool/emulator_test.sh.
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
    fun syncWorkerFetchesLiveSourcesAndPersistsState() {
        File(context.filesDir, "state.json").delete()
        val worker = TestListenableWorkerBuilder<SyncWorker>(context).build()
        val result = runBlocking { worker.doWork() }
        assertEquals(ListenableWorker.Result.success(), result, "SyncWorker natijasi")

        assertTrue(File(context.filesDir, "state.json").length() > 1000, "holat fayli yozildi")
        val snapshot = runBlocking { repo.current() }
        assertNotNull(snapshot)
        val ok = snapshot.sources.count { it.ok }
        println("EPIRADAR-DEVICE: manbalar ok=$ok/${snapshot.sources.size}, hodisalar=${snapshot.events.size}, shaxsiy=${snapshot.personalScore} (${snapshot.personalLevel.uz})")
        snapshot.sources.forEach { println("EPIRADAR-DEVICE:   ${it.source} ok=${it.ok} n=${it.itemCount} ${it.error ?: ""}") }
        assertTrue(ok >= 2, "kamida 2 ta manba ishlashi kerak: ${snapshot.sources}")
        assertTrue(snapshot.events.isNotEmpty(), "hodisalar bo'sh")
        // Qurilmada R8/resurslar to'g'ri: kasalliklar ma'lumotnomasi va mamlakatlar yuklangan.
        assertTrue(repo.catalogJson().contains("\"cchf\""))
    }

    @Test
    fun notificationChannelsAndCriticalAlert() {
        val nm = context.getSystemService(NotificationManager::class.java)
        val critical = nm.getNotificationChannel(Notifier.CHANNEL_CRITICAL)
        assertNotNull(critical)
        assertEquals(NotificationManager.IMPORTANCE_HIGH, critical.importance)
        assertNotNull(nm.getNotificationChannel(Notifier.CHANNEL_ALERTS))

        val n = AlertNotification("test:event", "Favqulodda: test", "Qurilma testi", ThreatLevel.EMERGENCY, critical = true)
        Notifier.show(context, n)
        Thread.sleep(500)
        assertTrue(nm.activeNotifications.any { it.id == n.eventId.hashCode() }, "bildirishnoma ko'rsatildi")
        nm.cancel(n.eventId.hashCode())
    }

    @Test
    fun settingsAreSanitisedAndScheduleUpdated() {
        val saved = repo.saveSettings("""{"country":"KAZ","syncHours":6,"alertThreshold":"CALM","watchCountries":["TUR","XXX"]}""")
        assertEquals("KAZ", saved.country)
        assertEquals(6, saved.syncHours)
        assertEquals(ThreatLevel.ADVISORY, saved.alertThreshold, "CALM chegara sifatida qabul qilinmaydi")
        assertEquals(listOf("TUR"), saved.watchCountries)
        val work = WorkManager.getInstance(context).getWorkInfosForUniqueWork("epiradar-sync").get()
        assertTrue(work.any { it.state == WorkInfo.State.ENQUEUED || it.state == WorkInfo.State.RUNNING }, "fon jadvali: $work")
        repo.saveSettings("""{"country":"UZB","syncHours":3}""")
    }

    @Test
    fun widgetUpdateWithoutWidgetsIsSafe() {
        val snapshot = runBlocking { repo.current() } ?: return
        RiskWidgetProvider.update(context, snapshot)
    }
}
