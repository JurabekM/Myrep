package uz.sectorverify.app

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import io.kotest.matchers.shouldBe
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import uz.sectorverify.data.repo.SiteSummary
import uz.sectorverify.feature.plan.SitesScreen
import uz.sectorverify.model.Verdict
import uz.sectorverify.ui.theme.SectorVerifyTheme

/** Stateless sites screen: import button, search and opening a site (Uzbek default strings). */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], qualifiers = "b+uz")
class SitesScreenTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun importSearchAndOpen() {
        var imports = 0
        var query = ""
        var opened = -1L
        compose.setContent {
            SectorVerifyTheme {
                SitesScreen(
                    sites = listOf(SiteSummary(7, "NAV-7", "Navoiy", 3, Verdict.PASS, null)),
                    query = query,
                    onQuery = { query = it },
                    onImport = { imports++ },
                    onOpenSite = { opened = it },
                    onSettings = {},
                )
            }
        }
        compose.onNodeWithText("CSV reja import").assertExists()
        compose.onNodeWithTag("import").performClick()
        compose.onNodeWithTag("search").performTextInput("NAV")
        compose.onNodeWithTag("site-NAV-7").performClick()
        imports shouldBe 1
        query shouldBe "NAV"
        opened shouldBe 7L
    }
}
