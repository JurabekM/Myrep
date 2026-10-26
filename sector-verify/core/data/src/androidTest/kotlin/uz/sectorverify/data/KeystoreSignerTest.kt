package uz.sectorverify.data

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import uz.sectorverify.data.security.KeystoreReportSigner
import uz.sectorverify.format.ReportIntegrity
import uz.sectorverify.format.ReportJson

/** §8.3 signature round-trip with the real Android Keystore key. */
@RunWith(AndroidJUnit4::class)
class KeystoreSignerTest {
    @Test
    fun signsAndVerifies() {
        val signer = KeystoreReportSigner(ApplicationProvider.getApplicationContext(), "sv_test_report_key")
        val report = buildJsonObject {
            put("schema", ReportJson.SCHEMA)
            put("verdict", "PASS")
        }
        val text = ReportJson.toText(ReportIntegrity.seal(report, signer))
        assertTrue(signer.certificateChain().isNotEmpty())
        assertTrue(ReportIntegrity.verify(text).ok)
        assertFalse(ReportIntegrity.verify(text.replace("PASS", "FAIL")).ok)
    }
}
