package com.agrovision.mobile.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface UserDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(user: UserEntity): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(users: List<UserEntity>)

    @Update
    suspend fun update(user: UserEntity)

    @Query("SELECT * FROM users WHERE username = :username AND active = 1 LIMIT 1")
    suspend fun findActive(username: String): UserEntity?

    @Query("SELECT * FROM users WHERE username = :username LIMIT 1")
    suspend fun findAny(username: String): UserEntity?

    @Query("SELECT * FROM users ORDER BY id")
    fun observeAll(): Flow<List<UserEntity>>

    @Query("SELECT COUNT(*) FROM users")
    suspend fun count(): Int
}

@Dao
interface AuditDao {
    @Insert
    suspend fun insert(entry: AuditLogEntity)

    @Query("SELECT * FROM audit_log ORDER BY id DESC LIMIT :limit")
    fun observeRecent(limit: Int = 200): Flow<List<AuditLogEntity>>
}

@Dao
interface SettingDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(setting: SettingEntity)

    @Query("SELECT value FROM settings WHERE key = :key LIMIT 1")
    suspend fun get(key: String): String?

    @Query("SELECT * FROM settings")
    suspend fun getAll(): List<SettingEntity>

    @Query("SELECT COUNT(*) FROM settings")
    suspend fun count(): Int
}

@Dao
interface GeoDao {
    @Insert
    suspend fun insertRegions(regions: List<RegionEntity>): List<Long>

    @Insert
    suspend fun insertDistricts(districts: List<DistrictEntity>): List<Long>

    @Insert
    suspend fun insertFarmers(farmers: List<FarmerEntity>): List<Long>

    @Insert
    suspend fun insertFarms(farms: List<FarmEntity>): List<Long>

    @Update
    suspend fun updateFarm(farm: FarmEntity)

    @Insert
    suspend fun insertFields(fields: List<FieldEntity>): List<Long>

    @Query("SELECT * FROM regions ORDER BY name")
    suspend fun regions(): List<RegionEntity>

    @Query("SELECT * FROM districts ORDER BY name")
    suspend fun districts(): List<DistrictEntity>

    @Query("SELECT * FROM districts WHERE regionId = :regionId ORDER BY name")
    suspend fun districtsByRegion(regionId: Long): List<DistrictEntity>

    @Query("SELECT * FROM farmers ORDER BY name")
    suspend fun farmers(): List<FarmerEntity>

    @Query("SELECT * FROM farms ORDER BY name")
    suspend fun farms(): List<FarmEntity>

    @Query("SELECT * FROM farms WHERE id = :id LIMIT 1")
    suspend fun farm(id: Long): FarmEntity?

    @Query("SELECT * FROM fields ORDER BY name")
    suspend fun fields(): List<FieldEntity>

    @Query("SELECT * FROM fields WHERE farmId = :farmId ORDER BY name")
    suspend fun fieldsByFarm(farmId: Long): List<FieldEntity>

    @Query("SELECT id, name AS label FROM fields ORDER BY id")
    suspend fun fieldOptions(): List<FieldLabelRow>

    @Query("SELECT COUNT(*) FROM regions")
    suspend fun regionCount(): Int

    @Query(
        "SELECT 'Fermer' AS turi, fm.name AS nomi, d.name || ', tel: ' || fm.phone AS tafsilot " +
            "FROM farmers fm JOIN districts d ON d.id = fm.districtId WHERE fm.name LIKE :like " +
            "UNION ALL " +
            "SELECT 'Xo''jalik', fa.name, r.name || ' - ' || CAST(ROUND(fa.areaHa) AS INTEGER) || ' ga' " +
            "FROM farms fa JOIN districts d ON d.id = fa.districtId JOIN regions r ON r.id = d.regionId " +
            "WHERE fa.name LIKE :like " +
            "UNION ALL " +
            "SELECT 'Dala', f.name, fa.name || ' - ' || CAST(f.areaHa AS TEXT) || ' ga, ' || f.soilType " +
            "FROM fields f JOIN farms fa ON fa.id = f.farmId WHERE f.name LIKE :like " +
            "UNION ALL " +
            "SELECT 'Ekin', c.name, c.category || ', ' || c.season " +
            "FROM crops c WHERE c.name LIKE :like " +
            "UNION ALL " +
            "SELECT 'Viloyat', r.name, 'Markaz: ' || CAST(ROUND(r.lat,2) AS TEXT) || ', ' || CAST(ROUND(r.lon,2) AS TEXT) " +
            "FROM regions r WHERE r.name LIKE :like " +
            "UNION ALL " +
            "SELECT 'Tuman', d.name, r.name FROM districts d JOIN regions r ON r.id = d.regionId WHERE d.name LIKE :like " +
            "LIMIT 30",
    )
    suspend fun search(like: String): List<SearchRow>

    @Query(
        "SELECT fm.id, fm.name, fm.phone, d.name AS district FROM farmers fm " +
            "JOIN districts d ON d.id = fm.districtId ORDER BY fm.id DESC",
    )
    suspend fun farmerList(): List<FarmerListRow>

    @Query(
        "SELECT fa.id, fa.name, fm.name AS farmer, fa.areaHa FROM farms fa " +
            "JOIN farmers fm ON fm.id = fa.farmerId ORDER BY fa.id DESC",
    )
    suspend fun farmList(): List<FarmListRow>

    @Query(
        "SELECT f.id, f.name, fa.name AS farm, f.areaHa, f.soilType FROM fields f " +
            "JOIN farms fa ON fa.id = f.farmId ORDER BY f.id DESC",
    )
    suspend fun fieldList(): List<FieldListRow>
}

@Dao
interface CropDao {
    @Insert
    suspend fun insertAll(crops: List<CropEntity>): List<Long>

    @Query("SELECT * FROM crops ORDER BY name")
    suspend fun all(): List<CropEntity>

    @Query("SELECT * FROM crops WHERE id = :id LIMIT 1")
    suspend fun byId(id: Long): CropEntity?

    @Query("SELECT COUNT(*) FROM crops")
    suspend fun count(): Int
}

@Dao
interface YieldDao {
    @Insert
    suspend fun insertAll(records: List<YieldRecordEntity>)

    @Query("SELECT DISTINCT year FROM yield_records ORDER BY year")
    suspend fun years(): List<Int>

    @Query("SELECT MAX(year) FROM yield_records")
    suspend fun latestYear(): Int?

    @Query(
        "SELECT year, ROUND(AVG(yieldTHa),2) AS avgYield, ROUND(SUM(productionT),0) AS production " +
            "FROM yield_records GROUP BY year ORDER BY year",
    )
    suspend fun trend(): List<YearYieldRow>

    @Query(
        "SELECT r.name AS region, ROUND(AVG(y.yieldTHa),2) AS avgYield, " +
            "ROUND(SUM(y.productionT),0) AS production, ROUND(SUM(y.areaHa),0) AS area " +
            "FROM yield_records y JOIN fields f ON f.id = y.fieldId JOIN farms fa ON fa.id = f.farmId " +
            "JOIN districts d ON d.id = fa.districtId JOIN regions r ON r.id = d.regionId " +
            "WHERE y.year = :year GROUP BY r.name ORDER BY production DESC",
    )
    suspend fun byRegion(year: Int): List<RegionYieldRow>

    @Query(
        "SELECT c.name AS crop, ROUND(SUM(y.areaHa),0) AS area, ROUND(SUM(y.productionT),0) AS production, " +
            "ROUND(AVG(y.yieldTHa),2) AS avgYield FROM yield_records y JOIN crops c ON c.id = y.cropId " +
            "WHERE y.year = :year GROUP BY c.name ORDER BY area DESC",
    )
    suspend fun cropDistribution(year: Int): List<CropAreaRow>

    @Query(
        "SELECT r.name AS region, c.name AS crop, AVG(y.yieldTHa) AS avgYield " +
            "FROM yield_records y JOIN crops c ON c.id = y.cropId JOIN fields f ON f.id = y.fieldId " +
            "JOIN farms fa ON fa.id = f.farmId JOIN districts d ON d.id = fa.districtId " +
            "JOIN regions r ON r.id = d.regionId WHERE y.year = :year GROUP BY r.name, c.name",
    )
    suspend fun regionCropMatrix(year: Int): List<RegionCropYieldRow>

    @Query(
        "SELECT fa.name AS farm, r.name AS region, ROUND(SUM(y.productionT),0) AS production, " +
            "ROUND(AVG(y.yieldTHa),2) AS avgYield FROM yield_records y JOIN fields f ON f.id = y.fieldId " +
            "JOIN farms fa ON fa.id = f.farmId JOIN districts d ON d.id = fa.districtId " +
            "JOIN regions r ON r.id = d.regionId WHERE y.year = :year GROUP BY fa.id " +
            "ORDER BY production DESC LIMIT :limit",
    )
    suspend fun topFarms(year: Int, limit: Int = 10): List<FarmProductionRow>

    @Query(
        "SELECT d.id AS districtId, d.name AS district, y.year, AVG(y.yieldTHa) AS avgYield " +
            "FROM yield_records y JOIN fields f ON f.id = y.fieldId JOIN farms fa ON fa.id = f.farmId " +
            "JOIN districts d ON d.id = fa.districtId GROUP BY d.id, y.year",
    )
    suspend fun districtYearYield(): List<DistrictYearYieldRow>

    @Query(
        "SELECT (SELECT COUNT(*) FROM farms) AS farms, (SELECT COUNT(*) FROM farmers) AS farmers, " +
            "(SELECT COUNT(*) FROM fields) AS fields, (SELECT COUNT(*) FROM crops) AS crops, " +
            "(SELECT COALESCE(SUM(areaHa),0) FROM fields) AS area",
    )
    suspend fun kpiCounts(): KpiCountsRow

    @Query(
        "SELECT COALESCE(AVG(yieldTHa),0) FROM yield_records WHERE year = :year",
    )
    suspend fun avgYield(year: Int): Double

    @Query("SELECT COALESCE(SUM(productionT),0) FROM yield_records WHERE year = :year")
    suspend fun totalProduction(year: Int): Double

    @Query(
        "SELECT y.fieldId, d.id AS districtId, y.year, y.cropId, r.id AS regionId, y.areaHa, " +
            "c.waterNeedMm, r.fertility, y.yieldTHa " +
            "FROM yield_records y JOIN crops c ON c.id = y.cropId JOIN fields f ON f.id = y.fieldId " +
            "JOIN farms fa ON fa.id = f.farmId JOIN districts d ON d.id = fa.districtId " +
            "JOIN regions r ON r.id = d.regionId",
    )
    suspend fun trainingRowsBase(): List<YieldTrainRow>

    @Query(
        "SELECT y.id, f.name AS field, c.name AS crop, y.year, y.yieldTHa, y.productionT " +
            "FROM yield_records y JOIN fields f ON f.id = y.fieldId JOIN crops c ON c.id = y.cropId " +
            "ORDER BY y.id DESC LIMIT :limit",
    )
    suspend fun recentList(limit: Int = 50): List<YieldListRow>

    @Query("SELECT COUNT(*) FROM yield_records")
    suspend fun count(): Int
}

@Dao
interface WeatherDao {
    @Insert
    suspend fun insertAll(records: List<WeatherRecordEntity>)

    @Query("DELETE FROM weather_records WHERE districtId = :districtId AND epochDay BETWEEN :startEpochDay AND :endEpochDay")
    suspend fun deleteRange(districtId: Long, startEpochDay: Long, endEpochDay: Long)

    @Query("SELECT MAX(epochDay) FROM weather_records WHERE districtId = :districtId")
    suspend fun latestEpochDay(districtId: Long): Long?

    @Query("SELECT COUNT(*) FROM weather_records WHERE districtId = :districtId")
    suspend fun countForDistrict(districtId: Long): Int

    @Query(
        "SELECT epochDay, tMin, tMax, precipitationMm, humidity FROM weather_records " +
            "WHERE districtId = :districtId AND epochDay >= :sinceEpochDay ORDER BY epochDay",
    )
    suspend fun history(districtId: Long, sinceEpochDay: Long): List<WeatherDailyRow>

    @Query(
        "SELECT CAST(strftime('%m', epochDay*86400, 'unixepoch') AS INTEGER) AS month, " +
            "ROUND(AVG(tMax),1) AS tMax, ROUND(AVG(tMin),1) AS tMin, " +
            "ROUND(SUM(precipitationMm)/COUNT(DISTINCT strftime('%Y', epochDay*86400, 'unixepoch')),1) AS precip, " +
            "ROUND(AVG(humidity),1) AS humidity FROM weather_records WHERE districtId = :districtId " +
            "GROUP BY month ORDER BY month",
    )
    suspend fun monthlyClimate(districtId: Long): List<WeatherMonthlyClimateRow>

    @Query(
        "SELECT district.id AS districtId, y.year, SUM(w.precipitationMm) AS precip, " +
            "AVG((w.tMin+w.tMax)/2) AS tAvg, AVG(w.humidity) AS humidity " +
            "FROM weather_records w JOIN districts district ON district.id = w.districtId, " +
            "(SELECT DISTINCT year FROM yield_records) y " +
            "WHERE CAST(strftime('%Y', w.epochDay*86400,'unixepoch') AS INTEGER) = y.year " +
            "AND CAST(strftime('%m', w.epochDay*86400,'unixepoch') AS INTEGER) BETWEEN 4 AND 9 " +
            "GROUP BY district.id, y.year",
    )
    suspend fun seasonalByDistrictYear(): List<DistrictYearPrecipRow>

    @Query(
        "SELECT SUM(w.precipitationMm) AS precip, AVG((w.tMin+w.tMax)/2) AS tAvg, AVG(w.humidity) AS humidity " +
            "FROM weather_records w JOIN districts d ON d.id = w.districtId JOIN regions r ON r.id = d.regionId " +
            "WHERE r.name = :region AND CAST(strftime('%Y', w.epochDay*86400,'unixepoch') AS INTEGER) = :year " +
            "AND CAST(strftime('%m', w.epochDay*86400,'unixepoch') AS INTEGER) BETWEEN 4 AND 9",
    )
    suspend fun seasonSummaryRaw(region: String, year: Int): DistrictYearPrecipRowLite?

    @Query("SELECT COUNT(*) FROM weather_records")
    suspend fun count(): Int
}

/** seasonSummaryRaw uchun yengil natija (districtId shart emas). */
data class DistrictYearPrecipRowLite(val precip: Double?, val tAvg: Double?, val humidity: Double?)

@Dao
interface MarketDao {
    @Insert
    suspend fun insertAll(records: List<MarketPriceEntity>)

    @Insert
    suspend fun insertOne(record: MarketPriceEntity)

    @Query(
        "SELECT m.cropId, c.name AS crop, m.pricePerKg AS price, m.epochDay " +
            "FROM market_prices m JOIN crops c ON c.id = m.cropId " +
            "WHERE m.epochDay = (SELECT MAX(epochDay) FROM market_prices WHERE cropId = m.cropId) " +
            "ORDER BY c.name",
    )
    suspend fun latestPrices(): List<LatestPriceRow>

    @Query(
        "SELECT epochDay, pricePerKg AS price FROM market_prices WHERE cropId = :cropId " +
            "AND epochDay >= :sinceEpochDay ORDER BY epochDay",
    )
    suspend fun history(cropId: Long, sinceEpochDay: Long): List<PricePointRow>

    @Query("SELECT COUNT(*) FROM market_prices")
    suspend fun count(): Int
}

@Dao
interface IrrigationDao {
    @Insert
    suspend fun insertAll(records: List<IrrigationRecordEntity>)

    @Query(
        "SELECT r.name AS region, ROUND(SUM(i.waterM3)/1000000.0,2) AS waterMlnM3, " +
            "ROUND(SUM(DISTINCT f.areaHa),0) AS area FROM irrigation_records i " +
            "JOIN fields f ON f.id = i.fieldId JOIN farms fa ON fa.id = f.farmId " +
            "JOIN districts d ON d.id = fa.districtId JOIN regions r ON r.id = d.regionId " +
            "WHERE CAST(strftime('%Y', i.epochDay*86400,'unixepoch') AS INTEGER) = :year " +
            "GROUP BY r.name ORDER BY waterMlnM3 DESC",
    )
    suspend fun usageByRegion(year: Int): List<RegionWaterRow>

    @Query(
        "SELECT method, ROUND(SUM(waterM3)/1000000.0,2) AS waterMlnM3, COUNT(*) AS events " +
            "FROM irrigation_records WHERE CAST(strftime('%Y', epochDay*86400,'unixepoch') AS INTEGER) = :year " +
            "GROUP BY method ORDER BY waterMlnM3 DESC",
    )
    suspend fun usageByMethod(year: Int): List<MethodWaterRow>

    @Query(
        "SELECT CAST(strftime('%m', epochDay*86400,'unixepoch') AS INTEGER) AS month, " +
            "ROUND(SUM(waterM3)/1000000.0,2) AS waterMlnM3 FROM irrigation_records " +
            "WHERE CAST(strftime('%Y', epochDay*86400,'unixepoch') AS INTEGER) = :year GROUP BY month ORDER BY month",
    )
    suspend fun monthlyUsage(year: Int): List<MonthWaterRow>

    @Query(
        "SELECT c.name AS crop, SUM(y.productionT) AS production, SUM(iw.water) AS waterM3 " +
            "FROM yield_records y JOIN crops c ON c.id = y.cropId JOIN " +
            "(SELECT fieldId, CAST(strftime('%Y', epochDay*86400,'unixepoch') AS INTEGER) AS yr, " +
            "SUM(waterM3) AS water FROM irrigation_records GROUP BY fieldId, yr) iw " +
            "ON iw.fieldId = y.fieldId AND iw.yr = y.year WHERE y.year = :year GROUP BY c.name",
    )
    suspend fun efficiencyByCrop(year: Int): List<CropEfficiencyRow>

    @Query(
        "SELECT fieldId, CAST(strftime('%Y', epochDay*86400,'unixepoch') AS INTEGER) AS year, " +
            "SUM(waterM3) AS waterM3 FROM irrigation_records GROUP BY fieldId, year",
    )
    suspend fun totalsByFieldYear(): List<FieldYearWaterRow>

    @Query(
        "SELECT i.id, f.name AS field, i.epochDay, i.waterM3, i.method " +
            "FROM irrigation_records i JOIN fields f ON f.id = i.fieldId ORDER BY i.id DESC LIMIT :limit",
    )
    suspend fun recentList(limit: Int = 50): List<IrrigationListRow>

    @Query("SELECT COUNT(*) FROM irrigation_records")
    suspend fun count(): Int
}

data class FieldYearWaterRow(val fieldId: Long, val year: Int, val waterM3: Double)

@Dao
interface FinanceDao {
    @Insert
    suspend fun insertAll(records: List<FinanceRecordEntity>)

    @Query(
        "SELECT year, SUM(CASE WHEN category='income' THEN amount ELSE 0 END) AS income, " +
            "SUM(CASE WHEN category='expense' THEN amount ELSE 0 END) AS expense, " +
            "SUM(CASE WHEN category='credit' THEN amount ELSE 0 END) AS credit, " +
            "SUM(CASE WHEN category='subsidy' THEN amount ELSE 0 END) AS subsidy " +
            "FROM finance_records GROUP BY year ORDER BY year",
    )
    suspend fun yearlySummary(): List<YearFinanceRow>

    @Query(
        "SELECT r.name AS region, " +
            "SUM(CASE WHEN fr.category='income' THEN fr.amount ELSE 0 END) AS income, " +
            "SUM(CASE WHEN fr.category='expense' THEN fr.amount ELSE 0 END) AS expense " +
            "FROM finance_records fr JOIN farms fa ON fa.id = fr.farmId JOIN districts d ON d.id = fa.districtId " +
            "JOIN regions r ON r.id = d.regionId WHERE fr.year = :year GROUP BY r.name",
    )
    suspend fun byRegion(year: Int): List<RegionFinanceRow>

    @Query(
        "SELECT fa.name AS farm, r.name AS region, " +
            "SUM(CASE WHEN fr.category='income' THEN fr.amount ELSE 0 END) AS income, " +
            "SUM(CASE WHEN fr.category='expense' THEN fr.amount ELSE 0 END) AS expense " +
            "FROM finance_records fr JOIN farms fa ON fa.id = fr.farmId JOIN districts d ON d.id = fa.districtId " +
            "JOIN regions r ON r.id = d.regionId WHERE fr.year = :year GROUP BY fa.id",
    )
    suspend fun farmProfitability(year: Int): List<FarmFinanceRow>

    @Query(
        "SELECT fr.id, fa.name AS farm, fr.year, fr.category, fr.amount, fr.note " +
            "FROM finance_records fr JOIN farms fa ON fa.id = fr.farmId ORDER BY fr.id DESC LIMIT :limit",
    )
    suspend fun recentList(limit: Int = 50): List<FinanceListRow>

    @Query("SELECT COUNT(*) FROM finance_records")
    suspend fun count(): Int
}

@Dao
interface SatelliteDao {
    @Insert
    suspend fun insertAll(records: List<SatelliteIndexEntity>)

    @Query(
        "SELECT f.id AS fieldId, f.name AS field, fa.name AS farm, r.name AS region, s.ndvi, s.evi " +
            "FROM satellite_indices s JOIN fields f ON f.id = s.fieldId JOIN farms fa ON fa.id = f.farmId " +
            "JOIN districts d ON d.id = fa.districtId JOIN regions r ON r.id = d.regionId " +
            "WHERE s.epochDay = (SELECT MAX(epochDay) FROM satellite_indices WHERE fieldId = f.id) " +
            "ORDER BY s.ndvi DESC",
    )
    suspend fun fieldHealth(): List<FieldHealthRow>

    @Query(
        "SELECT epochDay, ndvi, evi FROM satellite_indices WHERE fieldId = :fieldId ORDER BY epochDay",
    )
    suspend fun series(fieldId: Long): List<NdviPointRow>

    @Query(
        "SELECT s.id, f.name AS field, s.epochDay, s.ndvi " +
            "FROM satellite_indices s JOIN fields f ON f.id = s.fieldId ORDER BY s.id DESC LIMIT :limit",
    )
    suspend fun recentList(limit: Int = 50): List<SatelliteListRow>

    @Query("SELECT COUNT(*) FROM satellite_indices")
    suspend fun count(): Int
}

@Dao
interface MlModelDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(model: MlModelEntity)

    @Query("SELECT * FROM ml_models WHERE name = :name LIMIT 1")
    suspend fun get(name: String): MlModelEntity?
}
