package uz.dehqonkomakchi.app.di

import android.content.Context
import androidx.room.Room
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import uz.dehqonkomakchi.app.data.db.DehqonDatabase
import uz.dehqonkomakchi.app.data.db.dao.DiagnosisDao
import uz.dehqonkomakchi.app.data.db.dao.ExpenseDao
import uz.dehqonkomakchi.app.data.db.dao.HarvestDao
import uz.dehqonkomakchi.app.data.db.dao.ListingDao
import uz.dehqonkomakchi.app.data.db.dao.SaleDao
import uz.dehqonkomakchi.app.data.db.dao.SellGroupDao
import uz.dehqonkomakchi.app.data.db.dao.WeatherCacheDao
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): DehqonDatabase =
        Room.databaseBuilder(context, DehqonDatabase::class.java, "dehqon.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides fun provideDiagnosisDao(db: DehqonDatabase): DiagnosisDao = db.diagnosisDao()
    @Provides fun provideExpenseDao(db: DehqonDatabase): ExpenseDao = db.expenseDao()
    @Provides fun provideHarvestDao(db: DehqonDatabase): HarvestDao = db.harvestDao()
    @Provides fun provideSaleDao(db: DehqonDatabase): SaleDao = db.saleDao()
    @Provides fun provideListingDao(db: DehqonDatabase): ListingDao = db.listingDao()
    @Provides fun provideSellGroupDao(db: DehqonDatabase): SellGroupDao = db.sellGroupDao()
    @Provides fun provideWeatherCacheDao(db: DehqonDatabase): WeatherCacheDao = db.weatherCacheDao()
}
