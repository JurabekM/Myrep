package uz.qarzsiz.app

import android.Manifest
import android.app.Application
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.core.app.ApplicationProvider
import com.github.takahirom.roborazzi.captureRoboImage
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import uz.qarzsiz.app.data.AppState
import uz.qarzsiz.app.data.ReminderSettings
import uz.qarzsiz.app.ui.QarzsizApp
import uz.qarzsiz.app.ui.QarzsizTheme
import uz.qarzsiz.core.Pin

/**
 * Google Play uchun telefon skrinshotlari: 1080×1920 (9:16, 360×640 dp × 3).
 * `./gradlew :app:testDebugUnitTest --tests '*StoreScreenshotsTest'` → app/build/outputs/play/ (PNG);
 * keyin `qarzsiz/play/make_graphics.py` ularni fastlane papkasiga ko'chiradi.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w360dp-h640dp-xxhdpi")
class StoreScreenshotsTest {
    @get:Rule val rule = createComposeRule()
    private val app: Application = ApplicationProvider.getApplicationContext()

    private fun start(state: AppState): AppViewModel {
        val vm = AppViewModel(app, MemoryStore(state))
        rule.setContent { QarzsizTheme { QarzsizApp(vm) } }
        rule.waitUntil(5_000) { vm.status.value == AppViewModel.Status.Ready }
        rule.waitForIdle()
        return vm
    }

    private fun shot(name: String) {
        rule.waitForIdle()
        rule.onRoot().captureRoboImage("build/outputs/play/$name.png")
    }

    private fun tab(key: String) = rule.onNodeWithTag("tab_$key").performClick()

    @Test
    fun playScreenshots() {
        shadowOf(app).grantPermissions(Manifest.permission.POST_NOTIFICATIONS)
        start(sampleState().copy(reminders = ReminderSettings(enabled = true, daysBefore = 2)))
        shot("01_home")

        tab("debts")
        shot("02_debts")

        tab("plan")
        // Kerakli blok to'liq ko'rinishi uchun undan keyingi elementgacha aylantiriladi.
        rule.onNodeWithText("Qarzsiz kun").performScrollTo()
        shot("03_plan_month")
        rule.onNodeWithText("Ta'limiy vosita", substring = true).performScrollTo()
        shot("04_plan_methods")

        tab("debts")
        rule.onNodeWithText("Ahmadjon").performScrollTo().performClick()
        rule.onNodeWithText("Har oy qancha bera olasiz").performScrollTo().performTextInput("300")
        rule.onNodeWithText("Qachondan").performScrollTo().performTextInput("dekabrdan")
        rule.onNodeWithText("Nusxa olish").performScrollTo()
        shot("05_negotiation")

        tab("calc")
        listOf("Naqd narxi" to "6000000", "Oylik to'lov" to "650000", "Necha oy" to "12").forEach { (label, value) ->
            rule.onNodeWithText(label).performScrollTo().performTextInput(value)
        }
        rule.waitUntil(10_000) { rule.onAllNodes(hasText("yiliga ~", substring = true)).fetchSemanticsNodes().isNotEmpty() }
        rule.onNodeWithText("To'xta va o'yla").performScrollTo()
        shot("06_calculator")

        tab("more")
        rule.onNodeWithText("To'lov eslatmalari").performClick()
        shot("07_reminders")
    }

    @Test
    fun playLockScreenshot() {
        start(sampleState().copy(pin = Pin.create("2580", iterations = 1000)))
        shot("08_lock")
    }
}
