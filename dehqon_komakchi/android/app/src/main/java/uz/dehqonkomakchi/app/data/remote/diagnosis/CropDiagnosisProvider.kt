package uz.dehqonkomakchi.app.data.remote.diagnosis

/** Diagnosis categories the classifier can return. Kept small and safety-first on purpose. */
enum class DiagnosisCategory {
    PEST, FUNGAL, NUTRIENT, WATERING, HEAT_STRESS, UNCLEAR
}

data class PhotoQualityIssue(val reasonKey: String)

data class DiagnosisResult(
    val category: DiagnosisCategory,
    /** 0f..1f. Below [CropDiagnosisProvider.LOW_CONFIDENCE_THRESHOLD] the UI must present this
     * as low-confidence and avoid asserting a firm diagnosis. */
    val confidence: Float,
    val causeUzbek: String,
    val safeStepsUzbek: List<String>,
    val watchForUzbek: List<String>,
    val consultAdviceUzbek: String,
)

/**
 * Provider-agnostic interface for tomato leaf/fruit photo diagnosis.
 *
 * Swap [MockCropDiagnosisProvider] for a real implementation (on-device TFLite model, or a
 * backend HTTP call to `/v1/diagnosis` in the FastAPI service) without touching any UI or
 * ViewModel code — everything upstream only depends on this interface via Hilt DI
 * (see `di/ProviderModule.kt`).
 *
 * IMPORTANT SAFETY CONTRACT for any implementation:
 *  - Never return [DiagnosisCategory] with confidence implying certainty when the underlying
 *    signal is weak; prefer [DiagnosisCategory.UNCLEAR] with low confidence.
 *  - Never include specific chemical brand names, dosages, or banned/off-label treatment
 *    instructions in [DiagnosisResult.safeStepsUzbek]. Keep guidance generic (e.g. "consult a
 *    licensed agronomist before applying any chemical treatment").
 *  - Must not require network access to function (mock fallback is mandatory) so the app keeps
 *    working with zero API keys and offline.
 */
interface CropDiagnosisProvider {
    /** Returns null when the photo is analyzable; returns an issue describing why a retake is needed. */
    suspend fun checkPhotoQuality(imageBytes: ByteArray): PhotoQualityIssue?

    suspend fun diagnose(imageBytes: ByteArray): DiagnosisResult

    companion object {
        const val LOW_CONFIDENCE_THRESHOLD = 0.45f
        const val MEDIUM_CONFIDENCE_THRESHOLD = 0.7f
    }
}
