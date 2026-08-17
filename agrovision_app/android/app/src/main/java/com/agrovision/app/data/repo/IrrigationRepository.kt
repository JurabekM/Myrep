package com.agrovision.app.data.repo

import com.agrovision.app.data.local.*
import javax.inject.Inject
import javax.inject.Singleton

data class CropWaterEfficiency(
    val crop: String,
    val productionT: Double,
    val waterM3: Double,
    val m3PerTonne: Double,
)

@Singleton
class IrrigationRepository @Inject constructor(private val irrigationDao: IrrigationDao) {

    suspend fun byRegion(year: Int): List<RegionWaterRow> = irrigationDao.usageByRegion(year)
    suspend fun byMethod(year: Int): List<MethodWaterRow> = irrigationDao.usageByMethod(year)
    suspend fun monthly(year: Int): List<MonthWaterRow> = irrigationDao.monthlyUsage(year)
    suspend fun totalWaterMln(year: Int): Double = irrigationDao.totalWater(year) / 1_000_000

    /** Suv samaradorligi: 1 tonna mahsulotga sarflangan m³ (desktop `efficiency_by_crop`). */
    suspend fun efficiencyByCrop(year: Int): List<CropWaterEfficiency> =
        irrigationDao.efficiencyByCrop(year)
            .map {
                CropWaterEfficiency(
                    crop = it.crop,
                    productionT = it.production,
                    waterM3 = it.waterM3,
                    m3PerTonne = if (it.production > 0.1) it.waterM3 / it.production else 0.0,
                )
            }
            .filter { it.productionT > 0 }
            .sortedBy { it.m3PerTonne }

    /** Tomchilatib sug'orish ulushi, % — dashboard KPI. */
    suspend fun dripSharePercent(year: Int): Double {
        val methods = irrigationDao.usageByMethod(year)
        val total = methods.sumOf { it.waterMlnM3 }
        if (total <= 0) return 0.0
        val drip = methods.firstOrNull { it.method == "tomchilatib" }?.waterMlnM3 ?: 0.0
        return drip / total * 100
    }

    suspend fun recentList(): List<IrrigationListRow> = irrigationDao.recentList()
    suspend fun regionYearTotals(): List<RegionYearWaterRow> = irrigationDao.totalsByRegionYear()
    suspend fun fieldYearTotals(): List<FieldYearWaterRow> = irrigationDao.totalsByFieldYear()
}
