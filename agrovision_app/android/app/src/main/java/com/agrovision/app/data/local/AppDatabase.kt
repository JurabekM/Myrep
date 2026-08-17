package com.agrovision.app.data.local

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
        IrrigationRecordEntity::class, FinanceRecordEntity::class,
        SatelliteIndexEntity::class, ImportedFileEntity::class, MlModelEntity::class,
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
    abstract fun importedFileDao(): ImportedFileDao
    abstract fun mlModelDao(): MlModelDao

    /** Jadval bo'yicha yozuvlar soni — Administrator sahifasidagi baza holati. */
    suspend fun tableCounts(): List<TableCountRow> = listOf(
        TableCountRow("users", userDao().count()),
        TableCountRow("regions", geoDao().regionCount()),
        TableCountRow("crops", cropDao().count()),
        TableCountRow("yield_records", yieldDao().count()),
        TableCountRow("weather_records", weatherDao().count()),
        TableCountRow("market_prices", marketDao().count()),
        TableCountRow("irrigation_records", irrigationDao().count()),
        TableCountRow("finance_records", financeDao().count()),
        TableCountRow("satellite_indices", satelliteDao().count()),
    )

    companion object {
        const val DB_NAME = "agrovision.db"

        @Volatile private var instance: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase =
            instance ?: synchronized(this) {
                instance ?: Room.databaseBuilder(
                    context.applicationContext, AppDatabase::class.java, DB_NAME,
                ).fallbackToDestructiveMigration().build().also { instance = it }
            }

        /** Zaxiradan tiklashdan oldin bazani bo'shatish. */
        fun closeInstance() {
            synchronized(this) {
                instance?.close()
                instance = null
            }
        }
    }
}
