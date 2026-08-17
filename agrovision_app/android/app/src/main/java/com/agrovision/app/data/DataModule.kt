package com.agrovision.app.data

import android.content.Context
import com.agrovision.app.data.local.*
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DataModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        AppDatabase.getInstance(context)

    @Provides fun userDao(db: AppDatabase): UserDao = db.userDao()
    @Provides fun auditDao(db: AppDatabase): AuditDao = db.auditDao()
    @Provides fun settingDao(db: AppDatabase): SettingDao = db.settingDao()
    @Provides fun geoDao(db: AppDatabase): GeoDao = db.geoDao()
    @Provides fun cropDao(db: AppDatabase): CropDao = db.cropDao()
    @Provides fun yieldDao(db: AppDatabase): YieldDao = db.yieldDao()
    @Provides fun weatherDao(db: AppDatabase): WeatherDao = db.weatherDao()
    @Provides fun marketDao(db: AppDatabase): MarketDao = db.marketDao()
    @Provides fun irrigationDao(db: AppDatabase): IrrigationDao = db.irrigationDao()
    @Provides fun financeDao(db: AppDatabase): FinanceDao = db.financeDao()
    @Provides fun satelliteDao(db: AppDatabase): SatelliteDao = db.satelliteDao()
    @Provides fun importedFileDao(db: AppDatabase): ImportedFileDao = db.importedFileDao()
    @Provides fun mlModelDao(db: AppDatabase): MlModelDao = db.mlModelDao()
}
