package com.agrovision.mobile.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [
        UserEntity::class, AuditLogEntity::class, SettingEntity::class,
        RegionEntity::class, DistrictEntity::class, FarmerEntity::class,
        FarmEntity::class, FieldEntity::class, CropEntity::class,
        YieldRecordEntity::class, WeatherRecordEntity::class, MarketPriceEntity::class,
        IrrigationRecordEntity::class, FinanceRecordEntity::class, SatelliteIndexEntity::class,
        MlModelEntity::class,
    ],
    version = 1,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao
    abstract fun auditDao(): AuditDao
    abstract fun settingDao(): SettingDao
    abstract fun geoDao(): GeoDao
    abstract fun cropDao(): CropDao
    abstract fun yieldDao(): YieldDao
    abstract fun weatherDao(): WeatherDao
    abstract fun marketDao(): MarketDao
    abstract fun irrigationDao(): IrrigationDao
    abstract fun financeDao(): FinanceDao
    abstract fun satelliteDao(): SatelliteDao
    abstract fun mlModelDao(): MlModelDao

    companion object {
        const val DB_NAME = "agrovision.db"

        @Volatile private var instance: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase =
            instance ?: synchronized(this) {
                instance ?: Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    DB_NAME,
                ).fallbackToDestructiveMigration()
                    .build().also { instance = it }
            }

        /** Backup/restore uchun: bazani yopib, jarayonni qayta ochish uchun bo'shatadi. */
        fun closeInstance() {
            synchronized(this) {
                instance?.close()
                instance = null
            }
        }
    }
}
