package uz.qarzsiz.app

import android.Manifest
import android.app.AlarmManager
import android.app.Application
import android.app.NotificationManager
import androidx.core.app.NotificationCompat
import androidx.test.core.app.ApplicationProvider
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import uz.qarzsiz.app.data.AppState
import uz.qarzsiz.app.data.ReminderSettings
import uz.qarzsiz.app.data.Stores
import uz.qarzsiz.app.reminders.ReminderReceiver
import uz.qarzsiz.app.reminders.ReminderScheduler
import uz.qarzsiz.core.Debt
import uz.qarzsiz.core.DebtKind
import uz.qarzsiz.core.Script
import java.time.LocalDate
import java.time.LocalDateTime

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class RemindersTest {
    private val app: Application = ApplicationProvider.getApplicationContext()
    private val nm get() = app.getSystemService(NotificationManager::class.java)
    private val am get() = app.getSystemService(AlarmManager::class.java)

    @After fun reset() { Stores.factory = { uz.qarzsiz.app.data.Store(it.applicationContext) } }

    private fun stateDueToday(enabled: Boolean, script: Script = Script.LATIN) = AppState(
        onboardingDone = true,
        script = script,
        reminders = ReminderSettings(enabled = enabled, daysBefore = 2, hour = 9),
        debts = listOf(
            Debt("kaspi", "Kaspi", DebtKind.FOREIGN_BANK, balance = 1_000_000_00, monthlyPayment = 900_000_00,
                dueDay = LocalDate.now().dayOfMonth, createdOn = "2026-10-01"),
        ),
    )

    private fun run(state: AppState) {
        Stores.factory = { MemoryStore(state) }
        ReminderReceiver.handle(app, ReminderScheduler.ACTION_CHECK)
    }

    @Test
    fun postsNotificationAndSchedulesNextDay() {
        shadowOf(app).grantPermissions(Manifest.permission.POST_NOTIFICATIONS)
        run(stateDueToday(enabled = true))
        val posted = shadowOf(nm).allNotifications
        assertEquals(1, posted.size)
        val n = posted.single()
        assertEquals("Kaspi: bugun to'lov kuni", n.extras.getString(NotificationCompat.EXTRA_TITLE))
        assertTrue(n.extras.getCharSequence(NotificationCompat.EXTRA_BIG_TEXT).toString().contains("900 000 so'm"))
        // Qulflangan ekranda tafsilot yo'q.
        assertEquals(NotificationCompat.VISIBILITY_PRIVATE, n.visibility)
        assertNotNull(n.publicVersion)
        assertNotNull(shadowOf(am).nextScheduledAlarm)
    }

    @Test
    fun cyrillicNotification() {
        shadowOf(app).grantPermissions(Manifest.permission.POST_NOTIFICATIONS)
        run(stateDueToday(enabled = true, script = Script.CYRILLIC))
        val n = shadowOf(nm).allNotifications.single()
        assertEquals("Каспи: бугун тўлов куни", n.extras.getString(NotificationCompat.EXTRA_TITLE))
    }

    @Test
    fun disabledPostsNothingAndCancels() {
        shadowOf(app).grantPermissions(Manifest.permission.POST_NOTIFICATIONS)
        ReminderScheduler.schedule(app, 9)
        run(stateDueToday(enabled = false))
        assertEquals(0, shadowOf(nm).allNotifications.size)
        assertNull(shadowOf(am).nextScheduledAlarm)
    }

    @Test
    fun noPermissionNoNotificationButStillScheduled() {
        shadowOf(app).denyPermissions(Manifest.permission.POST_NOTIFICATIONS)
        run(stateDueToday(enabled = true))
        assertEquals(0, shadowOf(nm).allNotifications.size)
        assertNotNull(shadowOf(am).nextScheduledAlarm)
    }

    @Test
    fun bootReschedulesWithoutPosting() {
        shadowOf(app).grantPermissions(Manifest.permission.POST_NOTIFICATIONS)
        Stores.factory = { MemoryStore(stateDueToday(enabled = true)) }
        ReminderReceiver.handle(app, "android.intent.action.BOOT_COMPLETED")
        assertEquals(0, shadowOf(nm).allNotifications.size)
        assertNotNull(shadowOf(am).nextScheduledAlarm)
    }

    @Test
    fun nextTrigger() {
        val morning = LocalDateTime.of(2026, 10, 31, 7, 30)
        assertEquals(LocalDateTime.of(2026, 10, 31, 9, 0), ReminderScheduler.nextTrigger(morning, 9))
        val evening = LocalDateTime.of(2026, 10, 31, 9, 0)
        assertEquals(LocalDateTime.of(2026, 11, 1, 9, 0), ReminderScheduler.nextTrigger(evening, 9))
    }
}
