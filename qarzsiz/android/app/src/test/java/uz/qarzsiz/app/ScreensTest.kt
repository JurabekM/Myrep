package uz.qarzsiz.app

import android.app.Application
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.core.app.ApplicationProvider
import com.github.takahirom.roborazzi.captureRoboImage
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import uz.qarzsiz.app.data.AppState
import uz.qarzsiz.app.data.LoadResult
import uz.qarzsiz.app.data.StateStore
import uz.qarzsiz.app.ui.QarzsizApp
import uz.qarzsiz.app.ui.QarzsizTheme
import uz.qarzsiz.core.Currency
import uz.qarzsiz.core.Debt
import uz.qarzsiz.core.DebtKind
import uz.qarzsiz.core.FxRates
import uz.qarzsiz.core.PlanSettings
import uz.qarzsiz.core.TalkStatus

/** Xotiradagi saqlash joyi: Robolectric'da Android Keystore yo'q. */
class MemoryStore(private var initial: AppState?) : StateStore {
    var saved: AppState? = null
    override fun load(): LoadResult = initial?.let { LoadResult.Ok(it) } ?: LoadResult.Empty
    override fun save(state: AppState) { saved = state }
    override fun wipe() { initial = null; saved = null }
}

/** Matndagi misolga yaqin namunaviy holat (ismlar o'ylab topilgan). */
fun sampleState() = AppState(
    onboardingDone = true,
    settings = PlanSettings(
        monthlyIncome = 12_000_000_00,
        livingMinimum = 3_500_000_00,
        rates = FxRates(mapOf(Currency.USD to 12_650_00)),
    ),
    debts = listOf(
        Debt("ipoteka", "Ipoteka banki", DebtKind.MORTGAGE, balance = 120_000_000_00, annualRateBp = 1700,
            monthlyPayment = 2_400_000_00, dueDay = 10, createdOn = "2026-10-01"),
        Debt("kaspi", "Kaspi (Qozog'iston)", DebtKind.FOREIGN_BANK, balance = 12_650_000_00, annualRateBp = 4500,
            monthlyPayment = 900_000_00, dueDay = 5, hasPenalty = true, createdOn = "2026-10-01"),
        Debt("nasiya", "Telefon nasiyasi", DebtKind.INSTALLMENT, balance = 4_800_000_00, startBalance = 7_200_000_00,
            annualRateBp = 3800, monthlyPayment = 600_000_00, dueDay = 20, createdOn = "2026-09-01"),
        Debt("ahmad", "Ahmadjon", DebtKind.PERSONAL, Currency.USD, balance = 10_000_00, createdOn = "2026-10-01"),
        Debt("toshmat", "Toshmatjon", DebtKind.PERSONAL, Currency.USD, balance = 3_000_00, monthlyPayment = 100_00,
            talkStatus = TalkStatus.AGREED, note = "Dekabrdan har oy 100 $", createdOn = "2026-10-01"),
    ),
)

@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w411dp-h891dp-xxhdpi")
class ScreensTest {
    @get:Rule val rule = createComposeRule()

    private fun start(state: AppState?): Pair<AppViewModel, MemoryStore> {
        val store = MemoryStore(state)
        val vm = AppViewModel(ApplicationProvider.getApplicationContext<Application>(), store)
        rule.setContent { QarzsizTheme { QarzsizApp(vm) } }
        rule.waitUntil(5_000) { vm.status.value == AppViewModel.Status.Ready }
        rule.waitForIdle()
        return vm to store
    }

    private fun shot(name: String) = rule.onRoot().captureRoboImage("build/outputs/roborazzi/$name.png")

    private fun tab(key: String) = rule.onNodeWithTag("tab_$key").performClick()

    @Test
    fun onboarding() {
        start(null)
        rule.onNodeWithText("Qarzdan chiqish mumkin").assertIsDisplayed()
        shot("01_onboarding_1")
        rule.onNodeWithText("Davom etish").performClick()
        shot("02_onboarding_2")
        rule.onNodeWithText("Davom etish").performClick()
        rule.onNodeWithText("Boshlash").assertIsDisplayed()
        shot("03_onboarding_3")
    }

    @Test
    fun mainFlow() {
        val (vm, _) = start(sampleState())
        rule.onNodeWithText("Jami qarz (so'mda)").assertIsDisplayed()
        shot("10_home")

        tab("debts")
        rule.onNodeWithText("A — issiq qarzlar").assertIsDisplayed()
        shot("11_debts")

        rule.onNodeWithText("Kaspi (Qozog'iston)").performClick()
        rule.onNodeWithText("To'lov yozish").assertIsDisplayed()
        shot("12_debt_detail_a")
        rule.onNodeWithText("To'lov yozish").performClick()
        rule.onNodeWithText("Yozish").performScrollTo().performClick()
        rule.waitForIdle()
        val kaspi = vm.state.value.debts.first { it.id == "kaspi" }
        assertEquals(12_650_000_00L - 900_000_00L, kaspi.balance)
        assertEquals(1, vm.state.value.payments.size)
        shot("13_debt_after_payment")

        tab("debts")
        rule.onNodeWithText("Ahmadjon").performScrollTo().performClick()
        rule.onNodeWithText("3-qadam: kelishish").performScrollTo().assertIsDisplayed()
        shot("14_debt_detail_b")
        assertFalse(rule.onAllNodes(hasText("o'lib", substring = true)).fetchSemanticsNodes().isNotEmpty())

        tab("plan")
        rule.onNodeWithText("Shu oy kimga qancha").performScrollTo().assertIsDisplayed()
        shot("15_plan")
        rule.onNodeWithText("Usullarni taqqoslash").performScrollTo()
        shot("16_plan_methods")

        tab("calc")
        shot("17_calculator_empty")

        tab("more")
        shot("18_more")
        rule.onNodeWithText("Yo'l xaritasi").performClick()
        shot("19_guide")
    }

    @Test
    fun calculatorShowsHiddenRate() {
        start(sampleState())
        tab("calc")
        val fields = listOf("Naqd narxi" to "6000000", "Oylik to'lov" to "650000", "Necha oy" to "12")
        fields.forEach { (label, value) ->
            rule.onNodeWithText(label).performScrollTo().performTextInput(value)
        }
        rule.onNodeWithText("yiliga ~51,44%").performScrollTo().assertIsDisplayed()
        shot("20_calculator_result")
    }

    @Test
    fun newDebtForm() {
        start(sampleState())
        tab("debts")
        rule.onNodeWithText("+ Qarz qo'shish").performClick()
        rule.onNodeWithText("Yangi qarz").assertIsDisplayed()
        shot("21_debt_form")
        rule.onNodeWithText("Saqlash").performScrollTo().performClick()
        rule.onNodeWithText("Nomini yozing").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun habitsAndHelp() {
        val (vm, _) = start(sampleState())
        tab("more")
        rule.onNodeWithText("Kun tartibi").performClick()
        rule.onNodeWithText("Erta turdim").performClick()
        rule.waitForIdle()
        shot("22_habits")
        tab("more")
        rule.onNodeWithText("Yordam va huquqlar").performClick()
        rule.onNodeWithText("Juda og'ir bo'lsa").assertIsDisplayed()
        shot("23_help")
        assertEquals(1, vm.state.value.habitDone.count { it.endsWith("|early") })
    }
}
