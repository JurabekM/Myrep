package uz.dehqonkomakchi.app.data.remote.diagnosis

import android.graphics.BitmapFactory
import android.graphics.Color
import kotlinx.coroutines.delay
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.abs
import kotlin.random.Random

/**
 * Deterministic-ish heuristic classifier that runs entirely on-device from basic image
 * properties (brightness, blur proxy via edge-variance, and dominant hue bucket). This is a
 * stand-in for a real ML model — see [CropDiagnosisProvider] for the swap contract.
 *
 * The heuristic is intentionally simple and honest about its limits: it produces a
 * category + confidence from pixel statistics, never a "trust me" answer, and always routes
 * ambiguous input to UNCLEAR with low confidence rather than guessing hard.
 */
@Singleton
class MockCropDiagnosisProvider @Inject constructor() : CropDiagnosisProvider {

    override suspend fun checkPhotoQuality(imageBytes: ByteArray): PhotoQualityIssue? {
        val bitmap = runCatching {
            BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size)
        }.getOrNull() ?: return PhotoQualityIssue("decode_failed")

        if (bitmap.width < 200 || bitmap.height < 200) {
            return PhotoQualityIssue("too_small")
        }

        val stats = computeStats(bitmap)
        return when {
            stats.meanBrightness < 35 -> PhotoQualityIssue("too_dark")
            stats.meanBrightness > 235 -> PhotoQualityIssue("too_bright")
            stats.edgeVariance < 8.0 -> PhotoQualityIssue("too_blurry")
            else -> null
        }
    }

    override suspend fun diagnose(imageBytes: ByteArray): DiagnosisResult {
        // Simulate on-device inference latency so the UI's loading state is exercised honestly.
        delay(600)

        val bitmap = runCatching {
            BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size)
        }.getOrNull()

        val stats = bitmap?.let { computeStats(it) }
        val seed = imageBytes.size + (stats?.meanHue?.toInt() ?: 0)
        val random = Random(seed)

        if (stats == null) {
            return unclear(0.2f)
        }

        // Heuristic bucket selection from hue/brightness/saturation-like signals.
        val category = when {
            stats.brownRatio > 0.30 -> DiagnosisCategory.FUNGAL
            stats.yellowRatio > 0.30 -> DiagnosisCategory.NUTRIENT
            stats.darkSpotRatio > 0.12 -> DiagnosisCategory.PEST
            stats.meanBrightness > 190 && stats.edgeVariance < 25 -> DiagnosisCategory.HEAT_STRESS
            stats.wiltProxy > 0.25 -> DiagnosisCategory.WATERING
            else -> DiagnosisCategory.UNCLEAR
        }

        val baseConfidence = when (category) {
            DiagnosisCategory.UNCLEAR -> 0.25f + random.nextFloat() * 0.15f
            else -> 0.5f + random.nextFloat() * 0.35f
        }

        return buildResult(category, baseConfidence.coerceIn(0f, 0.95f))
    }

    private fun unclear(confidence: Float) = buildResult(DiagnosisCategory.UNCLEAR, confidence)

    private fun buildResult(category: DiagnosisCategory, confidence: Float): DiagnosisResult {
        val (cause, steps, watch, consult) = CONTENT[category]!!
        return DiagnosisResult(
            category = category,
            confidence = confidence,
            causeUzbek = cause,
            safeStepsUzbek = steps,
            watchForUzbek = watch,
            consultAdviceUzbek = consult,
        )
    }

    private data class ImgStats(
        val meanBrightness: Double,
        val meanHue: Double,
        val edgeVariance: Double,
        val brownRatio: Double,
        val yellowRatio: Double,
        val darkSpotRatio: Double,
        val wiltProxy: Double,
    )

    private fun computeStats(bitmap: android.graphics.Bitmap): ImgStats {
        val w = bitmap.width
        val h = bitmap.height
        val stepX = maxOf(1, w / 64)
        val stepY = maxOf(1, h / 64)

        var sumBrightness = 0.0
        var sumHue = 0.0
        var count = 0
        var brown = 0
        var yellow = 0
        var dark = 0
        var prevBrightness = -1.0
        var edgeDeltaSum = 0.0

        var y = 0
        while (y < h) {
            var x = 0
            while (x < w) {
                val pixel = bitmap.getPixel(x, y)
                val r = Color.red(pixel)
                val g = Color.green(pixel)
                val b = Color.blue(pixel)
                val brightness = (r + g + b) / 3.0
                val hsv = FloatArray(3)
                Color.RGBToHSV(r, g, b, hsv)

                sumBrightness += brightness
                sumHue += hsv[0]
                count++

                if (prevBrightness >= 0) edgeDeltaSum += abs(brightness - prevBrightness)
                prevBrightness = brightness

                // brown: low value, hue in orange/brown range
                if (hsv[0] in 15f..40f && hsv[2] in 0.15f..0.55f) brown++
                // yellow: hue in yellow band with decent saturation (chlorosis-like)
                if (hsv[0] in 45f..65f && hsv[1] > 0.35f) yellow++
                // dark spot: very low brightness relative to leaf green
                if (brightness < 60) dark++

                x += stepX
            }
            y += stepY
        }

        val mean = if (count > 0) sumBrightness / count else 128.0
        val meanHue = if (count > 0) sumHue / count else 90.0
        val brownRatio = if (count > 0) brown.toDouble() / count else 0.0
        val yellowRatio = if (count > 0) yellow.toDouble() / count else 0.0
        val darkRatio = if (count > 0) dark.toDouble() / count else 0.0
        val edgeVariance = if (count > 1) edgeDeltaSum / (count - 1) else 0.0
        val wiltProxy = (yellowRatio * 0.5 + darkRatio * 0.3)

        return ImgStats(mean, meanHue, edgeVariance, brownRatio, yellowRatio, darkRatio, wiltProxy)
    }

    companion object {
        private data class Content(
            val cause: String,
            val steps: List<String>,
            val watch: List<String>,
            val consult: String,
        )

        private val CONTENT: Map<DiagnosisCategory, Content> = mapOf(
            DiagnosisCategory.PEST to Content(
                cause = "Bargda zararkunanda hasharotlar ta'siri belgilari ko'rinmoqda (masalan, tunlamlar yoki oddiy so'ruvchi hasharotlar).",
                steps = listOf(
                    "Barglarning orqa tomonini tekshiring — tuxum yoki hasharotlarni qo'lda yig'ib oling.",
                    "Zararlangan barglarni kesib, ekin maydonidan uzoqlashtiring.",
                    "Har qanday kimyoviy dori qo'llashdan oldin agronom yoki o'simliklar himoyasi mutaxassisi bilan maslahatlashing.",
                ),
                watch = listOf("Yangi teshiklar yoki chaqqan izlar", "Barglarning tez sarg'ayishi", "Hasharotlar sonining ko'payishi"),
                consult = "Agar 2-3 kun ichida yangi bargларga tarqalsa yoki hosil miqdoriga ta'sir qilsa, mahalliy agronomga murojaat qiling.",
            ),
            DiagnosisCategory.FUNGAL to Content(
                cause = "Barg yoki mevada zamburug' kasalligiga xos qorong'i dog'lar/bo'yalish ehtimoli bor.",
                steps = listOf(
                    "Sug'orishni ildiz ostidan qiling, barglarga suv tegishidan saqlaning.",
                    "Zararlangan qismlarni olib tashlang va yoqib yuboring (kompostga qo'shmang).",
                    "Ekinlar orasidagi havo aylanishini yaxshilash uchun ortiqcha barglarni siyraklashtiring.",
                    "Fungitsid qo'llash kerak bo'lsa, faqat ro'yxatdan o'tgan va ruxsat etilgan preparatlarni, yorliqdagi ko'rsatmalarga qat'iy rioya qilib ishlating.",
                ),
                watch = listOf("Dog'larning kattalashishi", "Barglarning to'kilishi", "Namlik ko'p bo'lgan joylarda tez tarqalishi"),
                consult = "Agar dog'lar tez tarqalsa yoki poyaga o'tsa, zudlik bilan agronomga murojaat qiling.",
            ),
            DiagnosisCategory.NUTRIENT to Content(
                cause = "Barglarning sarg'ayishi oziqa moddalari (ehtimol azot yoki magniy) yetishmovchiligiga o'xshaydi.",
                steps = listOf(
                    "Tuproq namligini tekshiring — haddan tashqari quruq yoki nam tuproq oziqa so'rilishiga xalaqit beradi.",
                    "Muvozanatli, yorliqda ko'rsatilgan me'yordagi o'g'itlardan foydalaning.",
                    "O'g'itni haddan tashqari ko'p solishdan saqlaning — bu ildizlarga zarar yetkazishi mumkin.",
                ),
                watch = listOf("Sarg'ayish naqshi (tomirlar orasi yoki butun barg)", "O'sishning sekinlashishi", "Barglarning erta to'kilishi"),
                consult = "Agar o'g'itdan keyin 1-2 haftada yaxshilanish bo'lmasa, tuproq tahlili uchun agronomga murojaat qiling.",
            ),
            DiagnosisCategory.WATERING to Content(
                cause = "Barglarning so'lishi yoki teksturasi sug'orish tartibi bilan bog'liq muammoga ishora qiladi.",
                steps = listOf(
                    "So'nggi sug'orish sanasini va tuproq namligini tekshiring.",
                    "Sug'orishni erta tong yoki kech kechqurun, issiq kunning cho'qqisida emas, amalga oshiring.",
                    "Tuproqning haddan tashqari nam yoki quruq bo'lmasligiga ishonch hosil qiling.",
                ),
                watch = listOf("Barglarning kunduzi so'lishi, kechqurun tiklanishi", "Tuproqning qattiq qatqaloq bog'lashi", "Ildiz chirishi belgilari"),
                consult = "Agar sug'orish tartibini to'g'rilagandan keyin ham holat yomonlashsa, agronomga murojaat qiling.",
            ),
            DiagnosisCategory.HEAT_STRESS to Content(
                cause = "Yorug' va tekis rangdagi barglar issiqlik/quyosh stressiga xos ko'rinishga ega.",
                steps = listOf(
                    "Kunning eng issiq soatlarida vaqtinchalik soyabon qo'ying.",
                    "Tuproq namligini barqaror saqlang, lekin haddan tashqari sug'ormang.",
                    "Mulchalash (somon yoki organik qoplama) tuproq haroratini pasaytirishga yordam beradi.",
                ),
                watch = listOf("Barg qirralarining qovjirashi", "Mevaning kuyishi (quyosh kuyishi dog'lari)", "O'simlikning umumiy so'lishi"),
                consult = "Agar issiq havo davom etsa va o'simlik tiklanmasa, agronom bilan maslahatlashing.",
            ),
            DiagnosisCategory.UNCLEAR to Content(
                cause = "Suratdan aniq xulosa chiqarib bo'lmadi — belgilar bir nechta sabab bilan bog'liq bo'lishi mumkin.",
                steps = listOf(
                    "Bargning old va orqa tomonidan, yaxshi yorug'likda yana surat oling.",
                    "O'simlikni bir necha kun kuzatib boring — yangi belgilar paydo bo'lishi yoki yo'qolishiga e'tibor bering.",
                    "Shubha bo'lsa, hech qanday kimyoviy vosita qo'llamasdan avval mutaxassis bilan maslahatlashing.",
                ),
                watch = listOf("Belgilarning kuchayishi yoki tarqalishi", "Yangi o'zgarishlar (rang, shakl, hid)"),
                consult = "Ishonchli tashxis kerak bo'lsa, eng yaqin agronomlik xizmatiga yoki qishloq xo'jaligi markaziga murojaat qiling.",
            ),
        )
    }
}
