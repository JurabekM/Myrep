package uz.dehqonkomakchi.app.data.db.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow
import uz.dehqonkomakchi.app.data.db.entity.DiagnosisRecordEntity
import uz.dehqonkomakchi.app.data.db.entity.ExpenseEntity
import uz.dehqonkomakchi.app.data.db.entity.HarvestEntity
import uz.dehqonkomakchi.app.data.db.entity.ListingEntity
import uz.dehqonkomakchi.app.data.db.entity.ListingReportEntity
import uz.dehqonkomakchi.app.data.db.entity.SaleEntity
import uz.dehqonkomakchi.app.data.db.entity.SellGroupEntity
import uz.dehqonkomakchi.app.data.db.entity.WeatherCacheEntity

@Dao
interface DiagnosisDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(record: DiagnosisRecordEntity)

    @Update
    suspend fun update(record: DiagnosisRecordEntity)

    @Query("SELECT * FROM diagnosis_records ORDER BY createdAtEpochMillis DESC")
    fun observeAll(): Flow<List<DiagnosisRecordEntity>>

    @Query("SELECT * FROM diagnosis_records WHERE id = :id")
    suspend fun getById(id: String): DiagnosisRecordEntity?
}

@Dao
interface ExpenseDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(entity: ExpenseEntity)

    @Delete
    suspend fun delete(entity: ExpenseEntity)

    @Query("SELECT * FROM expenses ORDER BY dateEpochDay DESC")
    fun observeAll(): Flow<List<ExpenseEntity>>

    @Query("SELECT COALESCE(SUM(amount), 0) FROM expenses")
    fun observeTotal(): Flow<Double>
}

@Dao
interface HarvestDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(entity: HarvestEntity)

    @Delete
    suspend fun delete(entity: HarvestEntity)

    @Query("SELECT * FROM harvests ORDER BY dateEpochDay DESC")
    fun observeAll(): Flow<List<HarvestEntity>>

    @Query("SELECT COALESCE(SUM(quantity), 0) FROM harvests")
    fun observeTotalQuantity(): Flow<Double>
}

@Dao
interface SaleDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(entity: SaleEntity)

    @Delete
    suspend fun delete(entity: SaleEntity)

    @Query("SELECT * FROM sales ORDER BY dateEpochDay DESC")
    fun observeAll(): Flow<List<SaleEntity>>

    @Query("SELECT COALESCE(SUM(quantity * price), 0) FROM sales")
    fun observeTotalRevenue(): Flow<Double>
}

@Dao
interface ListingDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(entity: ListingEntity)

    @Update
    suspend fun update(entity: ListingEntity)

    @Delete
    suspend fun delete(entity: ListingEntity)

    @Query("SELECT * FROM listings WHERE reported = 0 ORDER BY createdAtEpochMillis DESC")
    fun observeActive(): Flow<List<ListingEntity>>

    @Query("SELECT * FROM listings WHERE id = :id")
    suspend fun getById(id: String): ListingEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertReport(report: ListingReportEntity)

    @Query("SELECT COUNT(*) FROM listing_reports WHERE listingId = :listingId")
    suspend fun reportCount(listingId: String): Int
}

@Dao
interface SellGroupDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(entity: SellGroupEntity)

    @Query("SELECT * FROM sell_groups ORDER BY createdAtEpochMillis DESC")
    fun observeAll(): Flow<List<SellGroupEntity>>
}

@Dao
interface WeatherCacheDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entity: WeatherCacheEntity)

    @Query("SELECT * FROM weather_cache WHERE region = :region")
    suspend fun get(region: String): WeatherCacheEntity?
}
