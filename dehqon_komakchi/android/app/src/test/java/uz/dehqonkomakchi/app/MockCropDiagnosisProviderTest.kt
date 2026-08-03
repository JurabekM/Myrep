package uz.dehqonkomakchi.app

import android.graphics.Bitmap
import android.graphics.Color
import com.google.common.truth.Truth.assertThat
import kotlinx.coroutines.test.runTest
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import uz.dehqonkomakchi.app.data.remote.diagnosis.CropDiagnosisProvider
import uz.dehqonkomakchi.app.data.remote.diagnosis.MockCropDiagnosisProvider
import java.io.ByteArrayOutputStream

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class MockCropDiagnosisProviderTest {

    private val provider = MockCropDiagnosisProvider()

    private fun bitmapBytes(width: Int, height: Int, color: Int): ByteArray {
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        bitmap.eraseColor(color)
        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
        return stream.toByteArray()
    }

    @Test
    fun `too small photo is rejected for retake`() = runTest {
        val bytes = bitmapBytes(50, 50, Color.GREEN)
        val issue = provider.checkPhotoQuality(bytes)
        assertThat(issue).isNotNull()
        assertThat(issue!!.reasonKey).isEqualTo("too_small")
    }

    @Test
    fun `too dark photo is rejected for retake`() = runTest {
        val bytes = bitmapBytes(300, 300, Color.BLACK)
        val issue = provider.checkPhotoQuality(bytes)
        assertThat(issue).isNotNull()
        assertThat(issue!!.reasonKey).isEqualTo("too_dark")
    }

    @Test
    fun `well-lit uniform photo without edges is rejected as blurry`() = runTest {
        // A perfectly flat mid-gray image has zero edge variance -> treated as blur/no-detail.
        val bytes = bitmapBytes(300, 300, Color.rgb(140, 140, 140))
        val issue = provider.checkPhotoQuality(bytes)
        assertThat(issue).isNotNull()
        assertThat(issue!!.reasonKey).isEqualTo("too_blurry")
    }

    @Test
    fun `garbled bytes fail to decode and are rejected`() = runTest {
        val issue = provider.checkPhotoQuality(byteArrayOf(1, 2, 3, 4, 5))
        // Depending on the platform's image decoder, unreadable bytes either fail to decode
        // outright or decode to a degenerate (too-small) bitmap -- both must be rejected.
        assertThat(issue).isNotNull()
        assertThat(issue!!.reasonKey).isAnyOf("decode_failed", "too_small")
    }

    @Test
    fun `diagnose never returns confidence above the provider ceiling`() = runTest {
        val bytes = bitmapBytes(400, 400, Color.rgb(90, 160, 70))
        val result = provider.diagnose(bytes)
        assertThat(result.confidence).isAtMost(0.95f)
        assertThat(result.confidence).isAtLeast(0f)
    }

    @Test
    fun `diagnose result always includes a consult disclaimer and safe steps`() = runTest {
        val bytes = bitmapBytes(400, 400, Color.rgb(90, 160, 70))
        val result = provider.diagnose(bytes)
        assertThat(result.safeStepsUzbek).isNotEmpty()
        assertThat(result.consultAdviceUzbek).isNotEmpty()
    }
}
