package uz.dehqonkomakchi.app.data.db

import androidx.room.Database
import androidx.room.RoomDatabase
import uz.dehqonkomakchi.app.data.db.dao.DiagnosisDao
import uz.dehqonkomakchi.app.data.db.dao.ExpenseDao
import uz.dehqonkomakchi.app.data.db.dao.HarvestDao
import uz.dehqonkomakchi.app.data.db.dao.ListingDao
import uz.dehqonkomakchi.app.data.db.dao.SaleDao
import uz.dehqonkomakchi.app.data.db.dao.SellGroupDao
import uz.dehqonkomakchi.app.data.db.dao.WeatherCacheDao
import uz.dehqonkomakchi.app.data.db.entity.DiagnosisRecordEntity
import uz.dehqonkomakchi.app.data.db.entity.ExpenseEntity
import uz.dehqonkomakchi.app.data.db.entity.HarvestEntity
import uz.dehqonkomakchi.app.data.db.entity.ListingEntity
import uz.dehqonkomakchi.app.data.db.entity.ListingReportEntity
import uz.dehqonkomakchi.app.data.db.entity.SaleEntity
import uz.dehqonkomakchi.app.data.db.entity.SellGroupEntity
import uz.dehqonkomakchi.app.data.db.entity.WeatherCacheEntity

@Database(
    entities = [
        DiagnosisRecordEntity::class,
        ExpenseEntity::class,
        HarvestEntity::class,
        SaleEntity::class,
        ListingEntity::class,
        ListingReportEntity::class,
        SellGroupEntity::class,
        WeatherCacheEntity::class,
    ],
    version = 1,
    exportSchema = true,
)
abstract class DehqonDatabase : RoomDatabase() {
    abstract fun diagnosisDao(): DiagnosisDao
    abstract fun expenseDao(): ExpenseDao
    abstract fun harvestDao(): HarvestDao
    abstract fun saleDao(): SaleDao
    abstract fun listingDao(): ListingDao
    abstract fun sellGroupDao(): SellGroupDao
    abstract fun weatherCacheDao(): WeatherCacheDao
}
