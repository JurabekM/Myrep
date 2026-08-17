package com.agrovision.app.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

/**
 * DAO qatlami — desktop versiyadagi SQL so'rovlarning aynan ko'chirmasi.
 * Sana ustunlari epochDay bo'lgani uchun `strftime('%Y', epochDay*86400,'unixepoch')`
 * ishlatiladi (desktopdagi `strftime('%Y', date)` ekvivalenti).
 */

private const val YEAR_OF = "CAST(strftime('%Y', epochDay*86400,'unixepoch') AS INTEGER)"

@Dao
interface UserDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(users: List<UserEntity>)

    @Insert
    suspend fun insert(user: UserEntity): Long

    @Update
    suspend fun update(user: UserEntity)

    @Query("SELECT * FROM users WHERE username = :username LIMIT 1")
    suspend fun find(username: String): UserEntity?

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

    @Query("SELECT COUNT(*) FROM settings")
    suspend fun count(): Int
}

@Dao
interface GeoDao {
    @Insert suspend fun insertRegions(rows: List<RegionEntity>): List<Long>
    @Insert suspend fun insertDistricts(rows: List<DistrictEntity>): List<Long>
    @Insert suspend fun insertFarmers(rows: List<FarmerEntity>): List<Long>
    @Insert suspend fun insertFarms(rows: List<FarmEntity>): List<Long>
    @Insert suspend fun insertFields(rows: List<FieldEntity>): List<Long>
    @Update suspend fun updateFarm(farm: FarmEntity)
    @Update suspend fun updateFarms(farms: List<FarmEntity>)

    @Query("SELECT * FROM regions ORDER BY name")
    suspend fun regions(): List<RegionEntity>

    @Query("SELECT * FROM regions WHERE name = :name LIMIT 1")
    suspend fun regionByName(name: String): RegionEntity?

    @Query("SELECT * FROM districts ORDER BY name")
    suspend fun districts(): List<DistrictEntity>

    @Query("SELECT * FROM districts WHERE id = :id LIMIT 1")
    suspend fun district(id: Long): DistrictEntity?

    @Query("SELECT * FROM farmers ORDER BY name")
    suspend fun farmers(): List<FarmerEntity>

    @Query("SELECT * FROM farms ORDER BY name")
    suspend fun farms(): List<FarmEntity>

    @Query("SELECT * FROM farms WHERE id = :id LIMIT 1")
    suspend fun farm(id: Long): FarmEntity?

    @Query("SELECT * FROM fields ORDER BY id")
    suspend fun fields(): List<FieldEntity>

    @Query("SELECT * FROM fields WHERE id = :id LIMIT 1")
    suspend fun field(id: Long): FieldEntity?

    @Query(
        "SELECT id, name || ' — ' || " +
            "(SELECT fa.name FROM farms fa WHERE fa.id = fields.farmId) AS label, " +
            "lat, lon, polygon FROM fields ORDER BY id",
    )
    suspend fun fieldOptions(): List<FieldLabelRow>

    @Query("SELECT COUNT(*) FROM regions")
    suspend fun regionCount(): Int

    // ---- CRUD ro'yxatlari ----
    @Query(
        "SELECT fm.id, fm.name, fm.phone, d.name AS district FROM farmers fm " +
            "JOIN districts d ON d.id = fm.districtId ORDER BY fm.id DESC LIMIT :limit",
    )
    suspend fun farmerList(limit: Int = 200): List<FarmerListRow>

    @Query(
        "SELECT fa.id, fa.name, fm.name AS farmer, d.name AS district, fa.areaHa FROM farms fa " +
            "JOIN farmers fm ON fm.id = fa.farmerId JOIN districts d ON d.id = fa.districtId " +
            "ORDER BY fa.id DESC LIMIT :limit",
    )
    suspend fun farmList(limit: Int = 200): List<FarmListRow>

    @Query(
        "SELECT f.id, f.name, fa.name AS farm, f.areaHa, f.soilType FROM fields f " +
            "JOIN farms fa ON fa.id = f.farmId ORDER BY f.id DESC LIMIT :limit",
    )
    suspend fun fieldList(limit: Int = 200): List<FieldListRow>

    // ---- Global qidiruv (desktop utils/search.py) ----
    @Query(
        "SELECT 'Fermer' AS turi, fm.name AS nomi, d.name || ', tel: ' || fm.phone AS tafsilot " +
            "FROM farmers fm JOIN districts d ON d.id = fm.districtId WHERE fm.name LIKE :like " +
            "UNION ALL " +
            "SELECT 'Xo''jalik', fa.name, r.name || ' — ' || CAST(CAST(ROUND(fa.areaHa) AS INTEGER) AS TEXT) || ' ga' " +
            "FROM farms fa JOIN districts d ON d.id = fa.districtId JOIN regions r ON r.id = d.regionId " +
            "WHERE fa.name LIKE :like " +
            "UNION ALL " +
            "SELECT 'Dala', f.name, fa.name || ' — ' || CAST(f.areaHa AS TEXT) || ' ga, ' || f.soilType " +
            "FROM fields f JOIN farms fa ON fa.id = f.farmId WHERE f.name LIKE :like " +
            "UNION ALL " +
            "SELECT 'Ekin', c.name, c.category || ', ' || c.season || ' — bazaviy narx ' || " +
            "CAST(CAST(c.basePricePerKg AS INTEGER) AS TEXT) || ' so''m/kg' " +
            "FROM crops c WHERE c.name LIKE :like " +
            "UNION ALL " +
            "SELECT 'Viloyat', r.name, 'Markaz: ' || CAST(ROUND(r.lat,2) AS TEXT) || ', ' || CAST(ROUND(r.lon,2) AS TEXT) " +
            "FROM regions r WHERE r.name LIKE :like " +
            "UNION ALL " +
            "SELECT 'Tuman', d.name, r.name FROM districts d JOIN regions r ON r.id = d.regionId WHERE d.name LIKE :like " +
            "LIMIT :limit",
    )
    suspend fun search(like: String, limit: Int = 30): List<SearchRow>

    // ---- Tuproq tahlili (desktop plugins/soil_analysis.py) ----
    @Query(
        "SELECT f.soilType, COUNT(*) AS fields, ROUND(SUM(f.areaHa),0) AS areaHa, " +
            "COALESCE(ROUND(AVG((SELECT AVG(y.yieldTHa) FROM yield_records y WHERE y.fieldId = f.id)),2),0) AS avgYield " +
            "FROM fields f GROUP BY f.soilType ORDER BY areaHa DESC",
    )
    suspend fun soilStats(): List<SoilStatRow>

    // ---- Xarita ----
    @Query(
        "SELECT f.id, f.name, f.areaHa, f.soilType, f.lat, f.lon, f.polygon, " +
            "fa.name AS farm, fm.name AS farmer, r.name AS region, r.id AS regionId, d.name AS district, " +
            "COALESCE(y.yieldTHa, 0) AS yieldTHa, COALESCE(c.name, '-') AS crop, COALESCE(s.ndvi, 0) AS ndvi " +
            "FROM fields f " +
            "JOIN farms fa ON fa.id = f.farmId " +
            "JOIN farmers fm ON fm.id = fa.farmerId " +
            "JOIN districts d ON d.id = fa.districtId " +
            "JOIN regions r ON r.id = d.regionId " +
            "LEFT JOIN yield_records y ON y.fieldId = f.id AND y.year = :year " +
            "LEFT JOIN crops c ON c.id = y.cropId " +
            "LEFT JOIN (SELECT fieldId, ndvi, MAX(epochDay) FROM satellite_indices GROUP BY fieldId) s " +
            "  ON s.fieldId = f.id",
    )
    suspend fun mapFields(year: Int): List<MapFieldRow>

    @Query(
        "SELECT name, areaHa, soilType, polygon, " +
            "(SELECT fa.name FROM farms fa WHERE fa.id = fields.farmId) AS farm, " +
            "(SELECT r.name FROM regions r JOIN districts d ON d.regionId = r.id " +
            " JOIN farms fa ON fa.districtId = d.id WHERE fa.id = fields.farmId) AS region " +
            "FROM fields WHERE polygon <> ''",
    )
    suspend fun fieldsForGeoJson(): List<ExportFieldGeoRow>
}

@Dao
interface CropDao {
    @Insert suspend fun insertAll(rows: List<CropEntity>): List<Long>
    @Update suspend fun update(crop: CropEntity)

    @Query("SELECT * FROM crops ORDER BY name")
    suspend fun all(): List<CropEntity>

    @Query("SELECT * FROM crops WHERE id = :id LIMIT 1")
    suspend fun byId(id: Long): CropEntity?

    @Query("SELECT COUNT(*) FROM crops")
    suspend fun count(): Int
}

@Dao
interface YieldDao {
    @Insert suspend fun insertAll(rows: List<YieldRecordEntity>)

    @Query("SELECT MAX(year) FROM yield_records")
    suspend fun latestYear(): Int?

    @Query("SELECT DISTINCT year FROM yield_records ORDER BY year")
    suspend fun years(): List<Int>

    @Query(
        "SELECT (SELECT COUNT(*) FROM farms) AS farms, (SELECT COUNT(*) FROM farmers) AS farmers, " +
            "(SELECT COUNT(*) FROM fields) AS fields, (SELECT COUNT(*) FROM crops) AS crops, " +
            "(SELECT COALESCE(SUM(areaHa),0) FROM fields) AS area",
    )
    suspend fun kpiCounts(): KpiCountsRow

    @Query("SELECT COALESCE(AVG(yieldTHa),0) FROM yield_records WHERE year = :year")
    suspend fun avgYield(year: Int): Double

    @Query("SELECT COALESCE(SUM(productionT),0) FROM yield_records WHERE year = :year")
    suspend fun totalProduction(year: Int): Double

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
        "SELECT r.name AS region, y.year, ROUND(AVG(y.yieldTHa),2) AS avgYield, " +
            "ROUND(SUM(y.productionT),0) AS production, ROUND(SUM(y.areaHa),0) AS area " +
            "FROM yield_records y JOIN fields f ON f.id = y.fieldId JOIN farms fa ON fa.id = f.farmId " +
            "JOIN districts d ON d.id = fa.districtId JOIN regions r ON r.id = d.regionId " +
            "GROUP BY r.name, y.year ORDER BY y.year",
    )
    suspend fun byRegionAllYears(): List<RegionYearYieldRow>

    @Query(
        "SELECT c.name AS crop, ROUND(SUM(y.areaHa),0) AS area, ROUND(SUM(y.productionT),0) AS production, " +
            "ROUND(AVG(y.yieldTHa),2) AS avgYield FROM yield_records y JOIN crops c ON c.id = y.cropId " +
            "WHERE y.year = :year GROUP BY c.name ORDER BY area DESC",
    )
    suspend fun cropDistribution(year: Int): List<CropAreaRow>

    @Query(
        "SELECT r.name AS region, c.name AS crop, ROUND(AVG(y.yieldTHa),2) AS avgYield " +
            "FROM yield_records y JOIN crops c ON c.id = y.cropId JOIN fields f ON f.id = y.fieldId " +
            "JOIN farms fa ON fa.id = f.farmId JOIN districts d ON d.id = fa.districtId " +
            "JOIN regions r ON r.id = d.regionId WHERE y.year = :year GROUP BY r.name, c.name",
    )
    suspend fun regionCropMatrix(year: Int): List<RegionCropRow>

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
        "SELECT y.year, ROUND(AVG(y.yieldTHa),2) AS avgYield, ROUND(SUM(y.productionT),0) AS production " +
            "FROM yield_records y JOIN fields f ON f.id = y.fieldId JOIN farms fa ON fa.id = f.farmId " +
            "JOIN districts d ON d.id = fa.districtId JOIN regions r ON r.id = d.regionId " +
            "WHERE (:regionId IS NULL OR r.id = :regionId) AND (:cropId IS NULL OR y.cropId = :cropId) " +
            "GROUP BY y.year ORDER BY y.year",
    )
    suspend fun filteredTrend(regionId: Long?, cropId: Long?): List<YearYieldRow>

    // ---- ML o'qitish ----
    @Query(
        "SELECT y.yieldTHa, y.areaHa, y.year, y.cropId, c.waterNeedMm, r.id AS regionId, " +
            "r.fertility, d.id AS districtId, y.fieldId " +
            "FROM yield_records y JOIN crops c ON c.id = y.cropId JOIN fields f ON f.id = y.fieldId " +
            "JOIN farms fa ON fa.id = f.farmId JOIN districts d ON d.id = fa.districtId " +
            "JOIN regions r ON r.id = d.regionId",
    )
    suspend fun yieldTrainRows(): List<YieldTrainRow>

    @Query(
        "SELECT y.cropId, y.year, d.id AS districtId, r.id AS regionId, r.fertility, " +
            "AVG(y.yieldTHa) AS avgYield, c.basePricePerKg, c.costPerHa " +
            "FROM yield_records y JOIN crops c ON c.id = y.cropId JOIN fields f ON f.id = y.fieldId " +
            "JOIN farms fa ON fa.id = f.farmId JOIN districts d ON d.id = fa.districtId " +
            "JOIN regions r ON r.id = d.regionId GROUP BY d.id, y.year, y.cropId",
    )
    suspend fun cropProfitRows(): List<CropProfitRow>

    // ---- Ro'yxat va eksport ----
    @Query(
        "SELECT y.id, f.name AS field, c.name AS crop, y.year, y.yieldTHa, y.productionT " +
            "FROM yield_records y JOIN fields f ON f.id = y.fieldId JOIN crops c ON c.id = y.cropId " +
            "ORDER BY y.id DESC LIMIT :limit",
    )
    suspend fun recentList(limit: Int = 100): List<YieldListRow>

    @Query(
        "SELECT y.year, r.name AS region, d.name AS district, fa.name AS farm, f.name AS field, " +
            "c.name AS crop, y.areaHa, y.yieldTHa, y.productionT " +
            "FROM yield_records y JOIN crops c ON c.id = y.cropId JOIN fields f ON f.id = y.fieldId " +
            "JOIN farms fa ON fa.id = f.farmId JOIN districts d ON d.id = fa.districtId " +
            "JOIN regions r ON r.id = d.regionId ORDER BY y.year DESC LIMIT :limit",
    )
    suspend fun exportRows(limit: Int = 20000): List<ExportYieldRow>

    @Query("SELECT COUNT(*) FROM yield_records")
    suspend fun count(): Int
}

data class RegionYearYieldRow(
    val region: String, val year: Int, val avgYield: Double, val production: Double, val area: Double,
)

@Dao
interface WeatherDao {
    @Insert suspend fun insertAll(rows: List<WeatherRecordEntity>)

    @Query("DELETE FROM weather_records WHERE districtId = :districtId AND epochDay BETWEEN :start AND :end")
    suspend fun deleteRange(districtId: Long, start: Long, end: Long)

    @Query("SELECT MAX(epochDay) FROM weather_records WHERE districtId = :districtId")
    suspend fun latestEpochDay(districtId: Long): Long?

    @Query("SELECT COUNT(*) FROM weather_records WHERE districtId = :districtId")
    suspend fun countForDistrict(districtId: Long): Int

    @Query(
        "SELECT epochDay, tMin, tMax, precipitationMm, humidity FROM weather_records " +
            "WHERE districtId = :districtId AND epochDay >= :since ORDER BY epochDay",
    )
    suspend fun history(districtId: Long, since: Long): List<WeatherDailyRow>

    @Query(
        "SELECT CAST(strftime('%m', epochDay*86400,'unixepoch') AS INTEGER) AS month, " +
            "ROUND(AVG(tMax),1) AS tMax, ROUND(AVG(tMin),1) AS tMin, " +
            "ROUND(SUM(precipitationMm)/COUNT(DISTINCT strftime('%Y', epochDay*86400,'unixepoch')),1) AS precip, " +
            "ROUND(AVG(humidity),1) AS humidity FROM weather_records WHERE districtId = :districtId " +
            "GROUP BY month ORDER BY month",
    )
    suspend fun monthlyClimate(districtId: Long): List<MonthClimateRow>

    /** Vegetatsiya mavsumi (aprel–sentabr) bo'yicha tuman×yil agregati — ML va AI uchun. */
    @Query(
        "SELECT districtId, $YEAR_OF AS year, SUM(precipitationMm) AS precip, " +
            "AVG((tMin+tMax)/2) AS tAvg, AVG(humidity) AS humidity FROM weather_records " +
            "WHERE CAST(strftime('%m', epochDay*86400,'unixepoch') AS INTEGER) BETWEEN 4 AND 9 " +
            "GROUP BY districtId, year",
    )
    suspend fun seasonByDistrictYear(): List<DistrictSeasonRow>

    /** Viloyat×yil mavsumiy agregat (tumanlar o'rtachasi) — ogohlantirish va AI uchun. */
    @Query(
        "SELECT r.name AS region, $YEAR_OF AS year, " +
            "SUM(w.precipitationMm)/COUNT(DISTINCT w.districtId) AS precip, " +
            "AVG((w.tMin+w.tMax)/2) AS tAvg, AVG(w.humidity) AS humidity " +
            "FROM weather_records w JOIN districts d ON d.id = w.districtId " +
            "JOIN regions r ON r.id = d.regionId " +
            "WHERE CAST(strftime('%m', w.epochDay*86400,'unixepoch') AS INTEGER) BETWEEN 4 AND 9 " +
            "GROUP BY r.name, year ORDER BY year",
    )
    suspend fun seasonByRegionYear(): List<RegionSeasonRow>

    /** Kasallik modeli uchun oylik agregat (desktop `_disease_frame`). */
    @Query(
        "SELECT districtId, $YEAR_OF AS year, " +
            "CAST(strftime('%m', epochDay*86400,'unixepoch') AS INTEGER) AS month, " +
            "AVG(humidity) AS humidity, AVG((tMin+tMax)/2) AS tAvg, SUM(precipitationMm) AS precip " +
            "FROM weather_records GROUP BY districtId, year, month",
    )
    suspend fun monthlyAggregates(): List<MonthWeatherRow>

    @Query(
        "SELECT epochDay, d.name AS district, tMin, tMax, precipitationMm, humidity, source " +
            "FROM weather_records w JOIN districts d ON d.id = w.districtId " +
            "ORDER BY epochDay DESC LIMIT :limit",
    )
    suspend fun exportRows(limit: Int = 20000): List<ExportWeatherRow>

    @Query("SELECT COUNT(*) FROM weather_records")
    suspend fun count(): Int
}

@Dao
interface MarketDao {
    @Insert suspend fun insertAll(rows: List<MarketPriceEntity>)
    @Insert suspend fun insert(row: MarketPriceEntity)

    /**
     * Har bir ekin uchun eng so'nggi narx.
     *
     * MUHIM: bitta kunda bir nechta narx bo'lishi mumkin (demo qator + qo'lda
     * kiritilgani). `GROUP BY` bilan bare-ustunlar ishlatilsa SQLite guruhdan
     * TASODIFIY qatorni oladi va qo'lda kiritilgan narx ko'rinmay qoladi.
     * Shuning uchun aniq bitta qator id bo'yicha tanlanadi: eng kech sana,
     * teng bo'lsa — eng oxirgi kiritilgani.
     */
    @Query(
        "SELECT m.cropId, c.name AS crop, m.pricePerKg AS price, m.epochDay FROM market_prices m " +
            "JOIN crops c ON c.id = m.cropId " +
            "WHERE m.id = (SELECT id FROM market_prices WHERE cropId = m.cropId " +
            "ORDER BY epochDay DESC, id DESC LIMIT 1) " +
            "ORDER BY c.name",
    )
    suspend fun latestPrices(): List<LatestPriceRow>

    @Query("SELECT epochDay, pricePerKg AS price FROM market_prices WHERE cropId = :cropId AND epochDay >= :since ORDER BY epochDay")
    suspend fun history(cropId: Long, since: Long): List<PricePointRow>

    @Query(
        "SELECT c.name AS crop, m.epochDay, m.pricePerKg AS price FROM market_prices m " +
            "JOIN crops c ON c.id = m.cropId WHERE m.epochDay >= :since ORDER BY m.epochDay",
    )
    suspend fun since(since: Long): List<CropPriceRow>

    @Query(
        "SELECT m.epochDay, c.name AS crop, m.pricePerKg, m.marketName, m.source FROM market_prices m " +
            "JOIN crops c ON c.id = m.cropId ORDER BY m.epochDay DESC LIMIT :limit",
    )
    suspend fun exportRows(limit: Int = 20000): List<ExportPriceRow>

    @Query("SELECT COUNT(*) FROM market_prices")
    suspend fun count(): Int
}

@Dao
interface IrrigationDao {
    @Insert suspend fun insertAll(rows: List<IrrigationRecordEntity>)

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
            "FROM irrigation_records WHERE $YEAR_OF = :year GROUP BY method ORDER BY waterMlnM3 DESC",
    )
    suspend fun usageByMethod(year: Int): List<MethodWaterRow>

    @Query(
        "SELECT CAST(strftime('%m', epochDay*86400,'unixepoch') AS INTEGER) AS month, " +
            "ROUND(SUM(waterM3)/1000000.0,2) AS waterMlnM3 FROM irrigation_records " +
            "WHERE $YEAR_OF = :year GROUP BY month ORDER BY month",
    )
    suspend fun monthlyUsage(year: Int): List<MonthWaterRow>

    @Query(
        "SELECT c.name AS crop, SUM(y.productionT) AS production, SUM(iw.water) AS waterM3 " +
            "FROM yield_records y JOIN crops c ON c.id = y.cropId JOIN " +
            "(SELECT fieldId, CAST(strftime('%Y', epochDay*86400,'unixepoch') AS INTEGER) AS yr, " +
            " SUM(waterM3) AS water FROM irrigation_records GROUP BY fieldId, yr) iw " +
            "ON iw.fieldId = y.fieldId AND iw.yr = y.year WHERE y.year = :year GROUP BY c.name",
    )
    suspend fun efficiencyByCrop(year: Int): List<CropEfficiencyRow>

    @Query("SELECT COALESCE(SUM(waterM3),0) FROM irrigation_records WHERE $YEAR_OF = :year")
    suspend fun totalWater(year: Int): Double

    @Query(
        "SELECT fieldId, $YEAR_OF AS year, SUM(waterM3) AS waterM3 " +
            "FROM irrigation_records GROUP BY fieldId, year",
    )
    suspend fun totalsByFieldYear(): List<FieldYearWaterRow>

    /** AI "nega pasaydi" tahlili uchun viloyat×yil suv sarfi. */
    @Query(
        "SELECT r.id AS regionId, CAST(strftime('%Y', i.epochDay*86400,'unixepoch') AS INTEGER) AS year, " +
            "SUM(i.waterM3) AS waterM3 FROM irrigation_records i " +
            "JOIN fields f ON f.id = i.fieldId JOIN farms fa ON fa.id = f.farmId " +
            "JOIN districts d ON d.id = fa.districtId JOIN regions r ON r.id = d.regionId " +
            "GROUP BY r.id, year ORDER BY year",
    )
    suspend fun totalsByRegionYear(): List<RegionYearWaterRow>

    @Query(
        "SELECT i.id, f.name AS field, i.epochDay, i.waterM3, i.method FROM irrigation_records i " +
            "JOIN fields f ON f.id = i.fieldId ORDER BY i.id DESC LIMIT :limit",
    )
    suspend fun recentList(limit: Int = 100): List<IrrigationListRow>

    @Query(
        "SELECT i.epochDay, f.name AS field, i.waterM3, i.method FROM irrigation_records i " +
            "JOIN fields f ON f.id = i.fieldId ORDER BY i.epochDay DESC LIMIT :limit",
    )
    suspend fun exportRows(limit: Int = 20000): List<ExportIrrigationRow>

    @Query("SELECT COUNT(*) FROM irrigation_records")
    suspend fun count(): Int
}

@Dao
interface FinanceDao {
    @Insert suspend fun insertAll(rows: List<FinanceRecordEntity>)

    @Query(
        "SELECT year, SUM(CASE WHEN category='income' THEN amount ELSE 0 END) AS income, " +
            "SUM(CASE WHEN category='expense' THEN amount ELSE 0 END) AS expense, " +
            "SUM(CASE WHEN category='credit' THEN amount ELSE 0 END) AS credit, " +
            "SUM(CASE WHEN category='subsidy' THEN amount ELSE 0 END) AS subsidy " +
            "FROM finance_records GROUP BY year ORDER BY year",
    )
    suspend fun yearlySummary(): List<YearFinanceRow>

    @Query(
        "SELECT r.name AS region, SUM(CASE WHEN fr.category='income' THEN fr.amount ELSE 0 END) AS income, " +
            "SUM(CASE WHEN fr.category='expense' THEN fr.amount ELSE 0 END) AS expense " +
            "FROM finance_records fr JOIN farms fa ON fa.id = fr.farmId " +
            "JOIN districts d ON d.id = fa.districtId JOIN regions r ON r.id = d.regionId " +
            "WHERE fr.year = :year GROUP BY r.name",
    )
    suspend fun byRegion(year: Int): List<RegionFinanceRow>

    @Query(
        "SELECT fa.name AS farm, r.name AS region, " +
            "SUM(CASE WHEN fr.category='income' THEN fr.amount ELSE 0 END) AS income, " +
            "SUM(CASE WHEN fr.category='expense' THEN fr.amount ELSE 0 END) AS expense " +
            "FROM finance_records fr JOIN farms fa ON fa.id = fr.farmId " +
            "JOIN districts d ON d.id = fa.districtId JOIN regions r ON r.id = d.regionId " +
            "WHERE fr.year = :year GROUP BY fa.id",
    )
    suspend fun farmProfitability(year: Int): List<FarmFinanceRow>

    @Query(
        "SELECT fa.name AS farm, fr.category, fr.amount, fr.note FROM finance_records fr " +
            "JOIN farms fa ON fa.id = fr.farmId WHERE fr.year = :year " +
            "AND fr.category IN ('credit','subsidy') ORDER BY fr.amount DESC LIMIT :limit",
    )
    suspend fun creditsAndSubsidies(year: Int, limit: Int = 50): List<CreditRow>

    @Query(
        "SELECT fr.id, fa.name AS farm, fr.year, fr.category, fr.amount, fr.note " +
            "FROM finance_records fr JOIN farms fa ON fa.id = fr.farmId ORDER BY fr.id DESC LIMIT :limit",
    )
    suspend fun recentList(limit: Int = 100): List<FinanceListRow>

    @Query(
        "SELECT fr.year, fa.name AS farm, fr.category, fr.amount, fr.note " +
            "FROM finance_records fr JOIN farms fa ON fa.id = fr.farmId ORDER BY fr.year DESC LIMIT :limit",
    )
    suspend fun exportRows(limit: Int = 20000): List<ExportFinanceRow>

    @Query("SELECT COUNT(*) FROM finance_records")
    suspend fun count(): Int
}

@Dao
interface SatelliteDao {
    @Insert suspend fun insertAll(rows: List<SatelliteIndexEntity>)

    @Query(
        "SELECT f.id AS fieldId, f.name AS field, fa.name AS farm, r.name AS region, " +
            "s.ndvi, s.evi, s.epochDay FROM satellite_indices s " +
            "JOIN fields f ON f.id = s.fieldId JOIN farms fa ON fa.id = f.farmId " +
            "JOIN districts d ON d.id = fa.districtId JOIN regions r ON r.id = d.regionId " +
            "WHERE s.epochDay = (SELECT MAX(epochDay) FROM satellite_indices WHERE fieldId = f.id) " +
            "GROUP BY f.id ORDER BY s.ndvi DESC",
    )
    suspend fun fieldHealth(): List<FieldHealthRow>

    @Query("SELECT epochDay, ndvi, evi FROM satellite_indices WHERE fieldId = :fieldId AND epochDay >= :since ORDER BY epochDay")
    suspend fun series(fieldId: Long, since: Long): List<NdviPointRow>

    @Query("SELECT COALESCE(AVG(ndvi),0) FROM satellite_indices WHERE epochDay >= :since")
    suspend fun avgNdviSince(since: Long): Double

    @Query(
        "SELECT s.id, f.name AS field, s.epochDay, s.ndvi, s.evi FROM satellite_indices s " +
            "JOIN fields f ON f.id = s.fieldId ORDER BY s.id DESC LIMIT :limit",
    )
    suspend fun recentList(limit: Int = 100): List<NdviListRow>

    @Query(
        "SELECT s.epochDay, f.name AS field, s.ndvi, s.evi, s.source FROM satellite_indices s " +
            "JOIN fields f ON f.id = s.fieldId ORDER BY s.epochDay DESC LIMIT :limit",
    )
    suspend fun exportRows(limit: Int = 20000): List<ExportNdviRow>

    @Query("SELECT COUNT(*) FROM satellite_indices")
    suspend fun count(): Int
}

@Dao
interface ImportedFileDao {
    @Insert suspend fun insert(row: ImportedFileEntity)

    @Query("SELECT * FROM imported_files ORDER BY id DESC LIMIT :limit")
    suspend fun recent(limit: Int = 50): List<ImportedFileEntity>
}

@Dao
interface MlModelDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(model: MlModelEntity)

    @Query("SELECT * FROM ml_models WHERE name = :name LIMIT 1")
    suspend fun get(name: String): MlModelEntity?

    @Query("SELECT * FROM ml_models")
    suspend fun all(): List<MlModelEntity>

    @Query("DELETE FROM ml_models")
    suspend fun clear()
}
