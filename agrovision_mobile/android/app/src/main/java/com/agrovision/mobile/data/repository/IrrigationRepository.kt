package com.agrovision.mobile.data.repository

import com.agrovision.mobile.data.local.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class IrrigationRepository @Inject constructor(private val irrigationDao: IrrigationDao) {
    suspend fun usageByRegion(year: Int): List<RegionWaterRow> = irrigationDao.usageByRegion(year)
    suspend fun usageByMethod(year: Int): List<MethodWaterRow> = irrigationDao.usageByMethod(year)
    suspend fun monthlyUsage(year: Int): List<MonthWaterRow> = irrigationDao.monthlyUsage(year)
    suspend fun efficiencyByCrop(year: Int): List<CropEfficiencyRow> =
        irrigationDao.efficiencyByCrop(year).sortedBy { if (it.production > 0) it.waterM3 / it.production else Double.MAX_VALUE }
}
