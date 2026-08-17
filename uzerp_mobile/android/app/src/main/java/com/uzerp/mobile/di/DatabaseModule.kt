package com.uzerp.mobile.di

import android.content.Context
import androidx.room.Room
import com.uzerp.mobile.data.local.AppDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Room bazasi va barcha DAO'larni ta'minlovchi Hilt moduli.
 *
 * Baza qurilmaning ichki xotirasida (`/data/data/<paket>/databases/`)
 * saqlanadi — tashqi xotira yoki tarmoq ishlatilmaydi.
 */
@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, AppDatabase.DB_NAME)
            .fallbackToDestructiveMigration()
            .build()

    @Provides fun provideUserDao(db: AppDatabase) = db.userDao()
    @Provides fun provideAuditDao(db: AppDatabase) = db.auditDao()
    @Provides fun provideSettingsDao(db: AppDatabase) = db.settingsDao()
    @Provides fun provideSequenceDao(db: AppDatabase) = db.sequenceDao()

    @Provides fun provideCategoryDao(db: AppDatabase) = db.categoryDao()
    @Provides fun provideProductDao(db: AppDatabase) = db.productDao()
    @Provides fun provideWarehouseDao(db: AppDatabase) = db.warehouseDao()
    @Provides fun provideStockDao(db: AppDatabase) = db.stockDao()
    @Provides fun provideStockMoveDao(db: AppDatabase) = db.stockMoveDao()

    @Provides fun provideCustomerDao(db: AppDatabase) = db.customerDao()
    @Provides fun provideSupplierDao(db: AppDatabase) = db.supplierDao()
    @Provides fun provideLeadDao(db: AppDatabase) = db.leadDao()

    @Provides fun provideSalesDocDao(db: AppDatabase) = db.salesDocDao()
    @Provides fun provideSalesItemDao(db: AppDatabase) = db.salesItemDao()
    @Provides fun providePurchaseDao(db: AppDatabase) = db.purchaseDao()
    @Provides fun providePurchaseItemDao(db: AppDatabase) = db.purchaseItemDao()

    @Provides fun provideAccountDao(db: AppDatabase) = db.accountDao()
    @Provides fun provideJournalDao(db: AppDatabase) = db.journalDao()
    @Provides fun providePaymentDao(db: AppDatabase) = db.paymentDao()
    @Provides fun provideAssetDao(db: AppDatabase) = db.assetDao()

    @Provides fun provideDepartmentDao(db: AppDatabase) = db.departmentDao()
    @Provides fun provideEmployeeDao(db: AppDatabase) = db.employeeDao()
    @Provides fun provideAttendanceDao(db: AppDatabase) = db.attendanceDao()
    @Provides fun provideLeaveDao(db: AppDatabase) = db.leaveDao()
    @Provides fun providePayrollDao(db: AppDatabase) = db.payrollDao()

    @Provides fun provideCrmActivityDao(db: AppDatabase) = db.crmActivityDao()
    @Provides fun provideInventoryCountDao(db: AppDatabase) = db.inventoryCountDao()
}
