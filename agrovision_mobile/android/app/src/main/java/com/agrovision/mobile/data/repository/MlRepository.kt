package com.agrovision.mobile.data.repository

import com.agrovision.mobile.core.LinearRegression
import com.agrovision.mobile.data.local.CropDao
import com.agrovision.mobile.data.local.MlModelDao
import com.agrovision.mobile.data.local.MlModelEntity
import com.agrovision.mobile.data.local.WeatherDao
import com.agrovision.mobile.data.local.YieldDao
import javax.inject.Inject
import javax.inject.Singleton

data class CropRecommendation(val crop: String, val confidencePercent: Double)

data class ModelStatus(val trained: Boolean, val rSquared: Double, val rows: Int, val trainedAt: Long)

/**
 * On-device Machine Learning: hosildorlikni bashorat qilish uchun ko'p
 * o'zgaruvchili chiziqli regressiya (eng kichik kvadratlar), qurilmada
 * mahalliy ma'lumotlar asosida o'qitiladi. Desktop versiyadagi
 * RandomForest/XGBoost ансamбl modellaridan farqli — mobil qurilmaning
 * cheklangan resurslari uchun yengil, lekin haqiqiy o'qitilgan model
 * (Sklearn emas, lekin bir xil matematik tamoyil: eng kichik kvadratlar).
 * Xususiyatlar: [areaHa, waterNeedMm, fertility, precip, tAvg, irrigationMm].
 */
@Singleton
class MlRepository @Inject constructor(
    private val yieldDao: YieldDao,
    private val weatherDao: WeatherDao,
    private val irrigationTotals: com.agrovision.mobile.data.local.IrrigationDao,
    private val mlModelDao: MlModelDao,
    private val cropDao: CropDao,
) {
    companion object {
        private const val MODEL_NAME = "yield"
        val FEATURE_NAMES = listOf("areaHa", "waterNeedMm", "fertility", "precip", "tAvg", "irrigationMm")
    }

    suspend fun trainYieldModel(): ModelStatus {
        val baseRows = yieldDao.trainingRowsBase()
        val seasonalMap = weatherDao.seasonalByDistrictYear()
            .associateBy { it.districtId to it.year }
        val irrigationMap = irrigationTotals.totalsByFieldYear()
            .associateBy { it.fieldId to it.year }

        val features = mutableListOf<DoubleArray>()
        val targets = mutableListOf<Double>()
        for (row in baseRows) {
            val season = seasonalMap[row.districtId to row.year]
            val precip = season?.precip ?: 150.0
            val tAvg = season?.tAvg ?: 24.0
            val waterM3 = irrigationMap[row.fieldId to row.year]?.waterM3 ?: 0.0
            val irrigationMm = if (row.areaHa > 0.1) waterM3 / (row.areaHa * 10) else 0.0
            features += doubleArrayOf(row.areaHa, row.waterNeedMm, row.fertility, precip, tAvg, irrigationMm)
            targets += row.yieldTHa
        }
        if (features.size < 10) {
            return ModelStatus(trained = false, rSquared = 0.0, rows = features.size, trainedAt = 0)
        }
        val (coefficients, rawRSquared) = LinearRegression.fit(features, targets)
        val rSquared = Math.round(rawRSquared * 1000) / 1000.0
        val entity = MlModelEntity(
            name = MODEL_NAME,
            coefficients = coefficients.joinToString(",") { it.toString() },
            rSquared = rSquared,
            trainedAt = System.currentTimeMillis(),
        )
        mlModelDao.upsert(entity)
        return ModelStatus(true, rSquared, features.size, entity.trainedAt)
    }

    suspend fun modelStatus(): ModelStatus {
        val model = mlModelDao.get(MODEL_NAME) ?: return trainYieldModel()
        return ModelStatus(true, model.rSquared, -1, model.trainedAt)
    }

    suspend fun predictYield(
        areaHa: Double, waterNeedMm: Double, fertility: Double,
        precip: Double, tAvg: Double, irrigationMm: Double,
    ): Double {
        val model = mlModelDao.get(MODEL_NAME) ?: run { trainYieldModel(); mlModelDao.get(MODEL_NAME) }
            ?: return 0.0
        val coefficients = model.coefficients.split(",").map { it.toDouble() }.toDoubleArray()
        val prediction = LinearRegression.predict(
            coefficients, doubleArrayOf(areaHa, waterNeedMm, fertility, precip, tAvg, irrigationMm),
        )
        return (Math.round(prediction.coerceAtLeast(0.1) * 100) / 100.0)
    }

    /** Kasallik xavfi — namlik/harorat/NDVI ga asoslangan sodda logistik formula. */
    fun diseaseRisk(humidity: Double, tAvg: Double, ndvi: Double): Double {
        val tempWindow = if (tAvg in 18.0..28.0) 1.0 else 0.5
        val raw = 1.0 / (1.0 + Math.exp(-0.09 * (humidity - 62))) * tempWindow
        val ndviAdjust = if (ndvi < 0.3) raw * 1.15 else raw
        return Math.round(ndviAdjust.coerceIn(0.0, 1.0) * 1000) / 1000.0
    }

    /** Suv ehtiyoji: yetishmovchilikni issiqlik ta'siri bilan hisoblaydi (desktop bilan bir xil formula). */
    fun waterNeed(waterNeedMm: Double, precip: Double, tAvg: Double, areaHa: Double): Double {
        val heatExtra = (tAvg - 24).coerceAtLeast(0.0) * 12
        val deficitMm = (waterNeedMm + heatExtra - 0.7 * precip).coerceAtLeast(0.0)
        return Math.round(deficitMm * 10 * areaHa).toDouble()
    }

    /** Ekin tavsiyasi: hudud+ekin tarixiy hosildorligidan taxminiy foyda bo'yicha reyting. */
    suspend fun recommendCrops(regionName: String, year: Int, topN: Int = 3): List<CropRecommendation> {
        val matrix = yieldDao.regionCropMatrix(year).filter { it.region == regionName }
        if (matrix.isEmpty()) return emptyList()
        val crops = cropDao.all().associateBy { it.name }
        val profits = matrix.mapNotNull { row ->
            val crop = crops[row.crop] ?: return@mapNotNull null
            val profit = row.avgYield * 1000 * crop.basePricePerKg - crop.costPerHa
            row.crop to profit
        }.sortedByDescending { it.second }.take(topN)
        val total = profits.sumOf { it.second.coerceAtLeast(0.0) }.coerceAtLeast(1.0)
        return profits.map { (crop, profit) ->
            CropRecommendation(crop, Math.round(profit.coerceAtLeast(0.0) / total * 1000) / 10.0)
        }
    }
}
