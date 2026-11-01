package uz.qarzsiz.app

import android.Manifest
import android.app.Application
import android.app.NotificationManager
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.core.app.NotificationCompat
import androidx.test.core.app.ApplicationProvider
import com.github.takahirom.roborazzi.captureRoboImage
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import uz.qarzsiz.app.data.AppState
import uz.qarzsiz.app.data.ReminderSettings
import uz.qarzsiz.app.data.Stores
import uz.qarzsiz.app.reminders.ReminderNotifier
import uz.qarzsiz.app.ui.QarzsizApp
import uz.qarzsiz.app.ui.QarzsizTheme
import uz.qarzsiz.core.Pin
import uz.qarzsiz.core.Script
import java.time.LocalDate

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w411dp-h891dp-xxhdpi")
class PinLockTest {
    @get:Rule val rule = createComposeRule()
    private val app: Application = ApplicationProvider.getApplicationContext()

    @After fun reset() { Stores.factory = { uz.qarzsiz.app.data.Store(it.applicationContext) } }

    /** Testda tez bo'lishi uchun kam takrorlash (ilovada — 120 000). */
    private fun locked(script: Script = Script.LATIN) =
        sampleState().copy(pin = Pin.create("2580", iterations = 1000), script = script)

    private fun start(state: AppState): AppViewModel {
        val vm = AppViewModel(app, MemoryStore(state))
        rule.setContent { QarzsizTheme { QarzsizApp(vm) } }
        rule.waitUntil(5_000) { vm.status.value == AppViewModel.Status.Ready }
        rule.waitForIdle()
        return vm
    }

    private fun type(pin: String) {
        pin.forEach { rule.onNodeWithText(it.toString()).performClick() }
        rule.waitForIdle()
    }

    private fun waitText(text: String) =
        rule.waitUntil(5_000) { rule.onAllNodes(hasText(text, substring = true)).fetchSemanticsNodes().isNotEmpty() }

    private fun shot(name: String) = rule.onRoot().captureRoboImage("build/outputs/roborazzi/$name.png")

    @Test
    fun lockedAppHidesDataUntilCorrectPin() {
        val vm = start(locked())
        assertTrue(vm.locked.value)
        rule.onNodeWithText("PIN-kodni kiriting").assertIsDisplayed()
        assertTrue(rule.onAllNodes(hasText("Jami qarz", substring = true)).fetchSemanticsNodes().isEmpty())
        shot("40_lock")

        type("1111")
        waitText("Noto'g'ri PIN. Yana 4 ta urinish")
        assertEquals(1, vm.state.value.pin!!.failures)

        type("2580")
        rule.waitUntil(5_000) { !vm.locked.value }
        rule.onNodeWithText("Jami qarz (so'mda)").assertIsDisplayed()
        assertEquals(0, vm.state.value.pin!!.failures)
    }

    @Test
    fun tooManyWrongAttemptsWait() {
        val vm = start(locked())
        repeat(5) {
            type("1111")
            rule.waitUntil(5_000) { vm.state.value.pin!!.failures == it + 1 }
        }
        waitText("Ko'p xato urinish")
        // Kutish paytida to'g'ri PIN ham qabul qilinmaydi.
        assertEquals(AppViewModel.PinCheck.Wait::class, runBlocking { vm.checkPin("2580") }::class)
        assertTrue(vm.locked.value)
    }

    @Test
    fun cyrillicLockScreen() {
        start(locked(Script.CYRILLIC))
        rule.onNodeWithText("ПИН-кодни киритинг").assertIsDisplayed()
        shot("41_lock_cyr")
    }

    @Test
    fun backgroundGrace() {
        val vm = start(locked())
        runBlocking { vm.unlock("2580") }
        assertFalse(vm.locked.value)
        vm.onBackground(1_000)
        vm.onForeground(20_000) // 19 s < 30 s
        assertFalse(vm.locked.value)
        vm.onBackground(30_000)
        vm.onForeground(61_000) // 31 s
        assertTrue(vm.locked.value)
    }

    @Test
    fun setPinThroughSettings() {
        val vm = start(sampleState())
        rule.onNodeWithTag("tab_more").performClick()
        rule.onNodeWithText("PIN-kod").performScrollTo().performClick()
        shot("42_pin_settings")
        rule.onNodeWithText("PIN-kod o'rnatish").performClick()
        // Oson PIN rad etiladi.
        type("1234")
        rule.onNodeWithText("Davom etish").performClick()
        waitText("juda oson topiladi")
        type("2580")
        rule.onNodeWithText("Davom etish").performClick()
        type("2580")
        rule.waitUntil(10_000) { vm.state.value.pin != null }
        val lock = vm.state.value.pin!!
        assertEquals(Pin.DEFAULT_ITERATIONS, lock.iterations)
        assertTrue(Pin.matches(lock, "2580"))
        rule.waitForIdle()
        rule.onNodeWithText("PIN-kod yoqilgan").assertIsDisplayed()
        shot("43_pin_enabled")
    }

    @Test
    fun backupNeverCarriesPin() {
        val vm = start(locked())
        runBlocking { vm.unlock("2580") }
        val exported = vm.exportText()
        assertFalse(exported.contains("\"pin\": {"))
        val currentPin = vm.state.value.pin
        // Import: joriy qurilma PIN'i saqlanadi.
        assertNull(vm.importText(exported))
        assertEquals(currentPin, vm.state.value.pin)
    }

    @Test
    fun notificationHidesDetailsWhenPinSet() {
        shadowOf(app).grantPermissions(Manifest.permission.POST_NOTIFICATIONS)
        val state = locked().copy(
            reminders = ReminderSettings(enabled = true),
            debts = sampleState().debts.map { it.copy(dueDay = LocalDate.now().dayOfMonth) },
        )
        ReminderNotifier.postDue(app, state, LocalDate.now())
        val n = shadowOf(app.getSystemService(NotificationManager::class.java)).allNotifications.single()
        assertEquals("To'lov eslatmasi", n.extras.getString(NotificationCompat.EXTRA_TITLE))
        val body = n.extras.getCharSequence(NotificationCompat.EXTRA_BIG_TEXT).toString()
        assertFalse(body.contains("Kaspi"))
        assertNotNull(body)
    }
}
