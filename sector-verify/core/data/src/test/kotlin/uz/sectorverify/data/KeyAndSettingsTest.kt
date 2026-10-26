package uz.sectorverify.data

import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import io.kotest.matchers.shouldBe
import io.kotest.matchers.shouldNotBe
import java.io.File
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import uz.sectorverify.data.security.DatabaseKeyStore
import uz.sectorverify.data.security.KeyWrapper
import uz.sectorverify.data.settings.AppTheme
import uz.sectorverify.data.settings.DataStoreSettingsRepository
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.AnalysisPreset
import uz.sectorverify.model.DeviceCapabilities

class KeyAndSettingsTest {
    /** Keystore o'rnini bosuvchi XOR (haqiqiy wrapper androidTest'da tekshiriladi). */
    private object FakeWrapper : KeyWrapper {
        override fun wrap(plain: ByteArray) = plain.map { (it.toInt() xor 0x5A).toByte() }.toByteArray()

        override fun unwrap(wrapped: ByteArray) = wrap(wrapped)
    }

    @Test
    fun `database key is 32 random bytes stored only wrapped`(@TempDir dir: File) {
        val file = File(dir, DatabaseKeyStore.FILE_NAME)
        val key = DatabaseKeyStore(file, FakeWrapper).passphrase()
        key.size shouldBe 32
        file.readBytes().toList() shouldNotBe key.toList()
        DatabaseKeyStore(file, FakeWrapper).passphrase().toList() shouldBe key.toList()
        DatabaseKeyStore(File(dir, "other"), FakeWrapper).passphrase().toList() shouldNotBe key.toList()
    }

    @Test
    fun `settings persist and the effective config follows preset or override`(@TempDir dir: File) = runTest {
        val store = PreferenceDataStoreFactory.create(scope = TestScope(UnconfinedTestDispatcher(testScheduler))) {
            File(dir, "s.preferences_pb")
        }
        val repo = DataStoreSettingsRepository(store)
        repo.current().theme shouldBe AppTheme.DARK
        repo.current().effectiveConfig shouldBe AnalysisConfig()
        repo.update { it.copy(preset = AnalysisPreset.URBAN, trafficUrl = "https://x", theme = AppTheme.SUN, engineerName = "Ali") }
        repo.current().effectiveConfig.rMaxM shouldBe 600.0
        repo.current().engineerName shouldBe "Ali"
        val caps = DeviceCapabilities("P", "G", 35, null, null, 60, 1.0, true, true, true, false, 0)
        repo.update {
            it.copy(configOverride = AnalysisConfig(rMaxM = 800.0), capabilities = caps, appLanguage = "ru", reportLanguage = "en")
        }
        repo.current().let {
            it.effectiveConfig.rMaxM shouldBe 800.0
            it.capabilities shouldBe caps
            it.appLanguage shouldBe "ru"
            it.reportLanguage shouldBe "en"
            it.theme shouldBe AppTheme.SUN
        }
        repo.update { it.copy(configOverride = null, capabilities = null) }
        repo.current().effectiveConfig.rMaxM shouldBe 600.0
        repo.current().capabilities shouldBe null
    }
}
