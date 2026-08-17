package com.agrovision.mobile.di

import android.content.Context
import com.agrovision.mobile.data.local.*
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        AppDatabase.getInstance(context)

    @Provides fun provideUserDao(db: AppDatabase): UserDao = db.userDao()
    @Provides fun provideAuditDao(db: AppDatabase): AuditDao = db.auditDao()
    @Provides fun provideSettingDao(db: AppDatabase): SettingDao = db.settingDao()
    @Provides fun provideGeoDao(db: AppDatabase): GeoDao = db.geoDao()
    @Provides fun provideCropDao(db: AppDatabase): CropDao = db.cropDao()
    @Provides fun provideYieldDao(db: AppDatabase): YieldDao = db.yieldDao()
    @Provides fun provideWeatherDao(db: AppDatabase): WeatherDao = db.weatherDao()
    @Provides fun provideMarketDao(db: AppDatabase): MarketDao = db.marketDao()
    @Provides fun provideIrrigationDao(db: AppDatabase): IrrigationDao = db.irrigationDao()
    @Provides fun provideFinanceDao(db: AppDatabase): FinanceDao = db.financeDao()
    @Provides fun provideSatelliteDao(db: AppDatabase): SatelliteDao = db.satelliteDao()
    @Provides fun provideMlModelDao(db: AppDatabase): MlModelDao = db.mlModelDao()
}
