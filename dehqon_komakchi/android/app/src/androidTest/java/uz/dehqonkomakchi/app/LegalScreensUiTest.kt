package uz.dehqonkomakchi.app

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test
import uz.dehqonkomakchi.app.ui.settings.PrivacyPolicyScreen
import uz.dehqonkomakchi.app.ui.settings.TermsScreen
import uz.dehqonkomakchi.app.ui.theme.DehqonTheme

/**
 * Compose UI tests for the two screens that need no Hilt-provided ViewModel, keeping the
 * instrumentation setup lightweight while still exercising real rendering on a device/emulator.
 */
class LegalScreensUiTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun privacyPolicyScreen_showsTitle() {
        composeRule.setContent {
            DehqonTheme { PrivacyPolicyScreen() }
        }
        composeRule.onNodeWithText("Maxfiylik siyosati").assertExists()
    }

    @Test
    fun termsScreen_showsTitle() {
        composeRule.setContent {
            DehqonTheme { TermsScreen() }
        }
        composeRule.onNodeWithText("Foydalanish shartlari").assertExists()
    }
}
