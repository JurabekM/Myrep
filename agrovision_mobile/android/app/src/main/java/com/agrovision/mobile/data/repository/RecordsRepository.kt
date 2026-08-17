package com.agrovision.mobile.data.repository

import com.agrovision.mobile.data.local.FieldEntity
import com.agrovision.mobile.data.local.FinanceDao
import com.agrovision.mobile.data.local.FinanceListRow
import com.agrovision.mobile.data.local.FinanceRecordEntity
import com.agrovision.mobile.data.local.IrrigationDao
import com.agrovision.mobile.data.local.IrrigationListRow
import com.agrovision.mobile.data.local.IrrigationRecordEntity
import com.agrovision.mobile.data.local.SatelliteDao
import com.agrovision.mobile.data.local.SatelliteIndexEntity
import com.agrovision.mobile.data.local.SatelliteListRow
import com.agrovision.mobile.data.local.YieldDao
import com.agrovision.mobile.data.local.YieldListRow
import com.agrovision.mobile.data.local.YieldRecordEntity
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Foydalanuvchi qo'lda kiritadigan yozuvlar: hosildorlik, sug'orish, moliya,
 * NDVI. Bularning barchasi real fermer xo'jaligi ma'lumotlari — o'ylab
 * topilgan demo emas.
 */
@Singleton
class RecordsRepository @Inject constructor(
    private val yieldDao: YieldDao,
    private val irrigationDao: IrrigationDao,
    private val financeDao: FinanceDao,
    private val satelliteDao: SatelliteDao,
) {
    suspend fun addYieldRecord(field: FieldEntity, cropId: Long, year: Int, yieldTHa: Double) {
        val production = yieldTHa * field.areaHa
        yieldDao.insertAll(
            listOf(
                YieldRecordEntity(
                    fieldId = field.id, cropId = cropId, year = year,
                    areaHa = field.areaHa, yieldTHa = yieldTHa, productionT = production,
                ),
            ),
        )
    }

    suspend fun addIrrigationRecord(fieldId: Long, date: LocalDate, waterM3: Double, method: String) {
        irrigationDao.insertAll(listOf(IrrigationRecordEntity(fieldId = fieldId, epochDay = date.toEpochDay(), waterM3 = waterM3, method = method)))
    }

    suspend fun addFinanceRecord(farmId: Long, year: Int, category: String, amount: Double, note: String) {
        financeDao.insertAll(listOf(FinanceRecordEntity(farmId = farmId, year = year, category = category, amount = amount, note = note)))
    }

    suspend fun addSatelliteRecord(fieldId: Long, date: LocalDate, ndvi: Double) {
        val evi = (ndvi * 0.85).coerceIn(0.0, 1.0)
        satelliteDao.insertAll(listOf(SatelliteIndexEntity(fieldId = fieldId, epochDay = date.toEpochDay(), ndvi = ndvi, evi = evi)))
    }

    suspend fun yieldList(): List<YieldListRow> = yieldDao.recentList()
    suspend fun irrigationList(): List<IrrigationListRow> = irrigationDao.recentList()
    suspend fun financeList(): List<FinanceListRow> = financeDao.recentList()
    suspend fun satelliteList(): List<SatelliteListRow> = satelliteDao.recentList()
}
