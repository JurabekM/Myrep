package com.agrovision.app.data.repo

import com.agrovision.app.core.round1
import com.agrovision.app.data.local.*
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

/** Foydalanuvchi qo'lda kiritadigan yozuvlar (hosildorlik/sug'orish/moliya/NDVI). */
@Singleton
class RecordsRepository @Inject constructor(
    private val yieldDao: YieldDao,
    private val irrigationDao: IrrigationDao,
    private val financeDao: FinanceDao,
    private val satelliteDao: SatelliteDao,
    private val geoDao: GeoDao,
) {
    suspend fun addYield(field: FieldEntity, cropId: Long, year: Int, yieldTHa: Double) {
        yieldDao.insertAll(
            listOf(
                YieldRecordEntity(
                    fieldId = field.id, cropId = cropId, year = year, areaHa = field.areaHa,
                    yieldTHa = yieldTHa, productionT = (yieldTHa * field.areaHa).round1(),
                ),
            ),
        )
    }

    suspend fun addIrrigation(fieldId: Long, date: LocalDate, waterM3: Double, method: String) {
        irrigationDao.insertAll(
            listOf(IrrigationRecordEntity(fieldId = fieldId, epochDay = date.toEpochDay(), waterM3 = waterM3, method = method)),
        )
    }

    suspend fun addFinance(farmId: Long, year: Int, category: String, amount: Double, note: String) {
        financeDao.insertAll(
            listOf(FinanceRecordEntity(farmId = farmId, year = year, category = category, amount = amount, note = note.trim())),
        )
    }

    suspend fun addNdvi(fieldId: Long, date: LocalDate, ndvi: Double) {
        satelliteDao.insertAll(
            listOf(
                SatelliteIndexEntity(
                    fieldId = fieldId, epochDay = date.toEpochDay(), ndvi = ndvi,
                    evi = (ndvi * 0.85).coerceIn(0.0, 1.0), source = "manual",
                ),
            ),
        )
    }

    suspend fun yieldList(): List<YieldListRow> = yieldDao.recentList()
    suspend fun irrigationList(): List<IrrigationListRow> = irrigationDao.recentList()
    suspend fun financeList(): List<FinanceListRow> = financeDao.recentList()
    suspend fun ndviList(): List<NdviListRow> = satelliteDao.recentList()
    suspend fun fields(): List<FieldEntity> = geoDao.fields()
    suspend fun farms(): List<FarmEntity> = geoDao.farms()
}
