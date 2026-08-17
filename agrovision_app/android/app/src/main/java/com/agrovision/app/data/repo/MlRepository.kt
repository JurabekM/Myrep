package com.agrovision.app.data.repo

import com.agrovision.app.core.ml.GradientBoostingClassifier
import com.agrovision.app.core.ml.Metrics
import com.agrovision.app.core.ml.RandomForestClassifier
import com.agrovision.app.core.ml.RandomForestRegressor
import com.agrovision.app.core.ml.TreeParams
import com.agrovision.app.core.round2
import com.agrovision.app.core.round3
import com.agrovision.app.data.local.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.PI
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.sin
import kotlin.random.Random

data class ModelInfo(
    val name: String,
    val title: String,
    val algorithm: String,
    val metricName: String,
    val metric: Double,
    val rows: Int,
    val trainedAt: Long,
)

data class CropRecommendation(val crop: String, val confidence: Double)

/**
 * ML xizmati — desktop `ml/service.py` ning to'liq porti, 4 model:
 *  1. Hosildorlik prognozi — RandomForest regressor (8 xususiyat)
 *  2. Kasallik xavfi      — GradientBoosting klassifikator (4 xususiyat)
 *  3. Suv ehtiyoji        — RandomForest regressor (4 xususiyat)
 *  4. Ekin tavsiyasi      — RandomForest klassifikator (4 xususiyat)
 *
 * Modellar qurilmada o'qitiladi (core/ml/Trees.kt — haqiqiy CART ansambllari)
 * va JSON sifatida `ml_models` jadvalida saqlanadi.
 */
@Singleton
class MlRepository @Inject constructor(
    private val yieldDao: YieldDao,
    private val weatherDao: WeatherDao,
    private val irrigationDao: IrrigationDao,
    private val cropDao: CropDao,
    private val geoDao: GeoDao,
    private val mlModelDao: MlModelDao,
) {
    companion object {
        const val YIELD = "yield"
        const val DISEASE = "disease"
        const val WATER = "water"
        const val CROP = "crop"

        private val TITLES = mapOf(
            YIELD to "Hosildorlik prognozi",
            DISEASE to "Kasallik xavfi",
            WATER to "Suv ehtiyoji",
            CROP to "Ekin tavsiyasi",
        )
    }

    // Yuklangan modellar keshi
    private var yieldModel: RandomForestRegressor? = null
    private var waterModel: RandomForestRegressor? = null
    private var diseaseModel: GradientBoostingClassifier? = null
    private var cropModel: RandomForestClassifier? = null

    suspend fun status(): List<ModelInfo> = mlModelDao.all().map {
        ModelInfo(
            name = it.name, title = TITLES[it.name] ?: it.name, algorithm = it.algorithm,
            metricName = it.metricName, metric = it.metric, rows = it.rows, trainedAt = it.trainedAt,
        )
    }

    suspend fun isTrained(): Boolean = mlModelDao.all().size >= 4

    /** Modellar mavjud bo'lmasa o'qitadi (birinchi ishga tushirish oqimi). */
    suspend fun trainIfNeeded(onProgress: (String) -> Unit = {}): List<ModelInfo> {
        if (isTrained()) return status()
        return trainAll(onProgress)
    }

    suspend fun trainAll(onProgress: (String) -> Unit = {}): List<ModelInfo> = withContext(Dispatchers.Default) {
        onProgress("Hosildorlik modeli")
        trainYield()
        onProgress("Kasallik xavfi modeli")
        trainDisease()
        onProgress("Suv ehtiyoji modeli")
        trainWater()
        onProgress("Ekin tavsiyasi modeli")
        trainCrop()
        yieldModel = null; waterModel = null; diseaseModel = null; cropModel = null
        status()
    }

    // -----------------------------------------------------------------------
    // 1) Hosildorlik — RandomForest regressor
    // -----------------------------------------------------------------------
    private suspend fun trainYield() {
        val rows = yieldDao.yieldTrainRows()
        if (rows.size < 20) return
        val seasons = weatherDao.seasonByDistrictYear().associateBy { it.districtId to it.year }
        val irrigation = irrigationDao.totalsByFieldYear().associateBy { it.fieldId to it.year }

        val features = mutableListOf<DoubleArray>()
        val targets = mutableListOf<Double>()
        rows.forEach { row ->
            val season = seasons[row.districtId to row.year] ?: return@forEach
            val water = irrigation[row.fieldId to row.year]?.waterM3 ?: 0.0
            val irrigationMm = water / max(0.1, row.areaHa * 10)
            features += doubleArrayOf(
                row.cropId.toDouble(), row.regionId.toDouble(), row.areaHa,
                season.precip, season.tAvg, irrigationMm, row.waterNeedMm, row.fertility,
            )
            targets += row.yieldTHa
        }
        if (features.size < 20) return

        val x = features.toTypedArray()
        val y = targets.toDoubleArray()
        val (trainIdx, testIdx) = Metrics.trainTestSplit(x.size)
        val model = RandomForestRegressor.train(
            x = trainIdx.map { x[it] }.toTypedArray(),
            y = trainIdx.map { y[it] }.toDoubleArray(),
            nEstimators = 80,
        )
        val actual = testIdx.map { y[it] }.toDoubleArray()
        val predicted = testIdx.map { model.predict(x[it]) }.toDoubleArray()
        save(YIELD, model.toJson(), "random_forest", "R²", Metrics.r2(actual, predicted).round3(), x.size)
    }

    /**
     * Kasallik xavfi o'qitish to'plami — desktop `_disease_frame`:
     * zamburug'li kasallik xavfi namlik bilan o'sadi va 18–28°C oralig'ida
     * eng yuqori bo'ladi; NDVI mavsumiy sinus bilan modellashtiriladi.
     */
    private suspend fun trainDisease() {
        val monthly = weatherDao.monthlyAggregates()
        if (monthly.size < 30) return
        val rng = Random(7)
        val features = mutableListOf<DoubleArray>()
        val labels = mutableListOf<Int>()
        monthly.forEach { row ->
            val ndvi = (0.2 + 0.5 * sin((row.month - 2) / 12.0 * PI) + rng.gaussian(0.0, 0.05))
                .coerceIn(0.05, 0.9)
            val tempWindow = if (row.tAvg > 18 && row.tAvg < 28) 1.0 else 0.0
            val risk = 1.0 / (1.0 + exp(-(0.09 * (row.humidity - 62)))) * (0.4 + 0.6 * tempWindow)
            features += doubleArrayOf(row.humidity, row.tAvg, row.precip, ndvi)
            labels += if (rng.nextDouble() < risk) 1 else 0
        }
        val x = features.toTypedArray()
        val y = labels.toIntArray()
        val (trainIdx, testIdx) = Metrics.trainTestSplit(x.size)
        val model = GradientBoostingClassifier.train(
            x = trainIdx.map { x[it] }.toTypedArray(),
            y = trainIdx.map { y[it] }.toIntArray(),
            nEstimators = 60,
        )
        val accuracy = model.accuracy(testIdx.map { x[it] }.toTypedArray(), testIdx.map { y[it] }.toIntArray())
        save(DISEASE, model.toJson(), "gradient_boosting", "Aniqlik", accuracy.round3(), x.size)
    }

    /**
     * Suv ehtiyoji to'plami — desktop `_water_frame`:
     * deficit(m³/ga) = max(0, need + max(0, tAvg−24)·12 − 0.7·precip) × 10
     */
    private suspend fun trainWater() {
        val crops = cropDao.all()
        val seasons = weatherDao.seasonByDistrictYear()
        if (crops.isEmpty() || seasons.isEmpty()) return
        val features = mutableListOf<DoubleArray>()
        val targets = mutableListOf<Double>()
        crops.forEach { crop ->
            val rng = Random(11 + crop.id)
            val sample = seasons.shuffled(rng).take(minOf(60, seasons.size))
            sample.forEach { season ->
                val heatExtra = max(0.0, season.tAvg - 24) * 12
                val deficit = max(0.0, crop.waterNeedMm + heatExtra - 0.7 * season.precip) * 10
                features += doubleArrayOf(crop.waterNeedMm, season.precip, season.tAvg, rng.nextDouble(5.0, 120.0))
                targets += deficit * (1 + rng.gaussian(0.0, 0.05))
            }
        }
        if (features.size < 20) return
        val x = features.toTypedArray()
        val y = targets.toDoubleArray()
        val (trainIdx, testIdx) = Metrics.trainTestSplit(x.size)
        val model = RandomForestRegressor.train(
            x = trainIdx.map { x[it] }.toTypedArray(),
            y = trainIdx.map { y[it] }.toDoubleArray(),
            nEstimators = 60,
        )
        val actual = testIdx.map { y[it] }.toDoubleArray()
        val predicted = testIdx.map { model.predict(x[it]) }.toDoubleArray()
        save(WATER, model.toJson(), "random_forest", "R²", Metrics.r2(actual, predicted).round3(), x.size)
    }

    /**
     * Ekin tavsiyasi — desktop `_crop_frame`: har bir tuman×yil uchun eng
     * foydali ekin (profit = hosildorlik·1000·narx − tannarx) belgi sifatida.
     */
    private suspend fun trainCrop() {
        val rows = yieldDao.cropProfitRows()
        if (rows.isEmpty()) return
        val seasons = weatherDao.seasonByDistrictYear().associateBy { it.districtId to it.year }

        val best = rows
            .groupBy { it.districtId to it.year }
            .mapNotNull { (_, group) ->
                group.maxByOrNull { it.avgYield * 1000 * it.basePricePerKg - it.costPerHa }
            }

        val features = mutableListOf<DoubleArray>()
        val labels = mutableListOf<Long>()
        best.forEach { row ->
            val season = seasons[row.districtId to row.year] ?: return@forEach
            features += doubleArrayOf(row.regionId.toDouble(), season.precip, season.tAvg, row.fertility)
            labels += row.cropId
        }
        if (features.size < 5 || labels.distinct().size < 2) return

        val x = features.toTypedArray()
        val model = RandomForestClassifier.train(x, labels, nEstimators = 60, params = TreeParams(maxDepth = 10))
        save(CROP, model.toJson(), "random_forest", "Aniqlik", model.accuracy(x, labels).round3(), x.size)
    }

    private suspend fun save(
        name: String, payload: String, algorithm: String,
        metricName: String, metric: Double, rows: Int,
    ) {
        mlModelDao.upsert(
            MlModelEntity(
                name = name, payload = payload, algorithm = algorithm,
                metric = metric, metricName = metricName, rows = rows,
                trainedAt = System.currentTimeMillis(),
            ),
        )
    }

    // -----------------------------------------------------------------------
    // Bashorat API
    // -----------------------------------------------------------------------
    suspend fun predictYield(
        cropId: Long, regionId: Long, areaHa: Double, precip: Double,
        tAvg: Double, irrigationMm: Double, waterNeedMm: Double, fertility: Double,
    ): Double? {
        val model = yieldModel ?: mlModelDao.get(YIELD)?.let {
            RandomForestRegressor.fromJson(it.payload).also { m -> yieldModel = m }
        } ?: return null
        return model.predict(
            doubleArrayOf(
                cropId.toDouble(), regionId.toDouble(), areaHa,
                precip, tAvg, irrigationMm, waterNeedMm, fertility,
            ),
        ).coerceAtLeast(0.0).round2()
    }

    suspend fun predictDiseaseRisk(humidity: Double, tAvg: Double, precip: Double, ndvi: Double): Double? {
        val model = diseaseModel ?: mlModelDao.get(DISEASE)?.let {
            GradientBoostingClassifier.fromJson(it.payload).also { m -> diseaseModel = m }
        } ?: return null
        return model.predictProba(doubleArrayOf(humidity, tAvg, precip, ndvi)).round3()
    }

    suspend fun predictWaterNeed(waterNeedMm: Double, precip: Double, tAvg: Double, areaHa: Double): Double? {
        val model = waterModel ?: mlModelDao.get(WATER)?.let {
            RandomForestRegressor.fromJson(it.payload).also { m -> waterModel = m }
        } ?: return null
        return kotlin.math.round(model.predict(doubleArrayOf(waterNeedMm, precip, tAvg, areaHa)).coerceAtLeast(0.0))
    }

    suspend fun recommendCrops(regionId: Long, precip: Double, tAvg: Double, fertility: Double, topN: Int = 3): List<CropRecommendation> {
        val model = cropModel ?: mlModelDao.get(CROP)?.let {
            RandomForestClassifier.fromJson(it.payload).also { m -> cropModel = m }
        } ?: return emptyList()
        val probabilities = model.predictProba(doubleArrayOf(regionId.toDouble(), precip, tAvg, fertility))
        val names = cropDao.all().associate { it.id to it.name }
        return model.classes.indices
            .sortedByDescending { probabilities[it] }
            .take(topN)
            .map { index ->
                val cropId = model.classes[index]
                CropRecommendation(
                    crop = names[cropId] ?: "Ekin #$cropId",
                    confidence = (probabilities[index] * 1000).let { kotlin.math.round(it) / 10.0 },
                )
            }
    }

    suspend fun regions() = geoDao.regions()
    suspend fun crops() = cropDao.all()

    private fun Random.gaussian(mean: Double, std: Double): Double {
        val u1 = nextDouble().coerceAtLeast(1e-12)
        val u2 = nextDouble()
        return mean + std * kotlin.math.sqrt(-2.0 * kotlin.math.ln(u1)) * kotlin.math.cos(2.0 * PI * u2)
    }
}
