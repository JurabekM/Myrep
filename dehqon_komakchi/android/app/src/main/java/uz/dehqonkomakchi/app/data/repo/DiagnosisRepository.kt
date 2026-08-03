package uz.dehqonkomakchi.app.data.repo

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import uz.dehqonkomakchi.app.data.db.dao.DiagnosisDao
import uz.dehqonkomakchi.app.data.db.entity.DiagnosisRecordEntity
import uz.dehqonkomakchi.app.data.remote.diagnosis.CropDiagnosisProvider
import uz.dehqonkomakchi.app.data.remote.diagnosis.DiagnosisCategory
import uz.dehqonkomakchi.app.data.remote.diagnosis.DiagnosisResult
import uz.dehqonkomakchi.app.data.remote.diagnosis.PhotoQualityIssue
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

data class DiagnosisRecord(
    val id: String,
    val photoPath: String,
    val category: DiagnosisCategory,
    val confidence: Float,
    val cause: String,
    val steps: List<String>,
    val watch: List<String>,
    val consult: String,
    val createdAtEpochMillis: Long,
    val usefulRating: Int?,
)

@Singleton
class DiagnosisRepository @Inject constructor(
    private val provider: CropDiagnosisProvider,
    private val dao: DiagnosisDao,
) {
    suspend fun checkPhotoQuality(imageBytes: ByteArray): PhotoQualityIssue? =
        provider.checkPhotoQuality(imageBytes)

    suspend fun diagnoseAndSave(imageBytes: ByteArray, photoPath: String): DiagnosisRecord {
        val result: DiagnosisResult = provider.diagnose(imageBytes)
        val id = UUID.randomUUID().toString()
        val entity = DiagnosisRecordEntity(
            id = id,
            photoPath = photoPath,
            category = result.category.name,
            confidence = result.confidence,
            causeText = result.causeUzbek,
            stepsText = result.safeStepsUzbek.joinToString("\n"),
            watchText = result.watchForUzbek.joinToString("\n"),
            consultText = result.consultAdviceUzbek,
            createdAtEpochMillis = System.currentTimeMillis(),
        )
        dao.insert(entity)
        return entity.toRecord()
    }

    suspend fun rate(id: String, useful: Boolean) {
        val existing = dao.getById(id) ?: return
        dao.update(existing.copy(usefulRating = if (useful) 1 else 0))
    }

    fun observeHistory(): Flow<List<DiagnosisRecord>> =
        dao.observeAll().map { list -> list.map { it.toRecord() } }

    private fun DiagnosisRecordEntity.toRecord() = DiagnosisRecord(
        id = id,
        photoPath = photoPath,
        category = runCatching { DiagnosisCategory.valueOf(category) }.getOrDefault(DiagnosisCategory.UNCLEAR),
        confidence = confidence,
        cause = causeText,
        steps = stepsText.split("\n").filter { it.isNotBlank() },
        watch = watchText.split("\n").filter { it.isNotBlank() },
        consult = consultText,
        createdAtEpochMillis = createdAtEpochMillis,
        usefulRating = usefulRating,
    )
}
