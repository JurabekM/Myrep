package uz.dehqonkomakchi.app

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.google.common.truth.Truth.assertThat
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import uz.dehqonkomakchi.app.data.db.DehqonDatabase
import uz.dehqonkomakchi.app.data.remote.diagnosis.CropDiagnosisProvider
import uz.dehqonkomakchi.app.data.remote.diagnosis.DiagnosisCategory
import uz.dehqonkomakchi.app.data.remote.diagnosis.DiagnosisResult
import uz.dehqonkomakchi.app.data.remote.diagnosis.PhotoQualityIssue
import uz.dehqonkomakchi.app.data.repo.DiagnosisRepository

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class DiagnosisRepositoryTest {

    private lateinit var db: DehqonDatabase
    private lateinit var repository: DiagnosisRepository

    private class FakeProvider(
        private val issue: PhotoQualityIssue? = null,
    ) : CropDiagnosisProvider {
        override suspend fun checkPhotoQuality(imageBytes: ByteArray) = issue

        override suspend fun diagnose(imageBytes: ByteArray) = DiagnosisResult(
            category = DiagnosisCategory.NUTRIENT,
            confidence = 0.6f,
            causeUzbek = "test cause",
            safeStepsUzbek = listOf("step1", "step2"),
            watchForUzbek = listOf("watch1"),
            consultAdviceUzbek = "consult",
        )
    }

    @Before
    fun setUp() {
        db = Room.inMemoryDatabaseBuilder(ApplicationProvider.getApplicationContext(), DehqonDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        repository = DiagnosisRepository(FakeProvider(), db.diagnosisDao())
    }

    @After
    fun tearDown() {
        db.close()
    }

    @Test
    fun `diagnoseAndSave persists a record retrievable from history`() = runTest {
        val record = repository.diagnoseAndSave(byteArrayOf(1, 2, 3), "path/to/photo.jpg")

        val history = repository.observeHistory().first()
        assertThat(history).hasSize(1)
        assertThat(history.first().id).isEqualTo(record.id)
        assertThat(history.first().category).isEqualTo(DiagnosisCategory.NUTRIENT)
        assertThat(history.first().steps).containsExactly("step1", "step2").inOrder()
    }

    @Test
    fun `rating a record updates usefulRating`() = runTest {
        val record = repository.diagnoseAndSave(byteArrayOf(1, 2, 3), "path/to/photo.jpg")
        repository.rate(record.id, useful = true)

        val history = repository.observeHistory().first()
        assertThat(history.first().usefulRating).isEqualTo(1)
    }

    @Test
    fun `unrated record has null usefulRating`() = runTest {
        repository.diagnoseAndSave(byteArrayOf(1, 2, 3), "path/to/photo.jpg")
        val history = repository.observeHistory().first()
        assertThat(history.first().usefulRating).isNull()
    }
}
