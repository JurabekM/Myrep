package com.smartmoliya.app.core.di

import android.content.Context
import androidx.room.Room
import com.smartmoliya.app.core.database.AppDatabase
import com.smartmoliya.app.core.security.DatabaseKeyProvider
import net.zetetic.database.sqlcipher.SupportOpenHelperFactory
import com.smartmoliya.app.core.database.dao.BudgetDao
import com.smartmoliya.app.core.database.dao.CategoryDao
import com.smartmoliya.app.core.database.dao.DebtDao
import com.smartmoliya.app.core.database.dao.GoalDao
import com.smartmoliya.app.core.database.dao.InvestmentDao
import com.smartmoliya.app.core.database.dao.LoanDao
import com.smartmoliya.app.core.database.dao.LocalTaskDao
import com.smartmoliya.app.core.database.dao.TransactionDao
import com.smartmoliya.app.core.database.dao.WalletDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideAppDatabase(
        @ApplicationContext context: Context,
        databaseKeyProvider: DatabaseKeyProvider
    ): AppDatabase {
        // SQLCipher native kutubxonasini yuklash (factory'dan oldin majburiy)
        System.loadLibrary("sqlcipher")
        val factory = SupportOpenHelperFactory(databaseKeyProvider.getOrCreatePassphrase())

        return Room.databaseBuilder(context, AppDatabase::class.java, AppDatabase.DATABASE_NAME)
            .openHelperFactory(factory)
            .fallbackToDestructiveMigration()
            .build()
    }

    @Provides
    fun provideWalletDao(db: AppDatabase): WalletDao = db.walletDao()

    @Provides
    fun provideCategoryDao(db: AppDatabase): CategoryDao = db.categoryDao()

    @Provides
    fun provideTransactionDao(db: AppDatabase): TransactionDao = db.transactionDao()

    @Provides
    fun provideBudgetDao(db: AppDatabase): BudgetDao = db.budgetDao()

    @Provides
    fun provideGoalDao(db: AppDatabase): GoalDao = db.goalDao()

    @Provides
    fun provideLoanDao(db: AppDatabase): LoanDao = db.loanDao()

    @Provides
    fun provideDebtDao(db: AppDatabase): DebtDao = db.debtDao()

    @Provides
    fun provideInvestmentDao(db: AppDatabase): InvestmentDao = db.investmentDao()

    @Provides
    fun provideLocalTaskDao(db: AppDatabase): LocalTaskDao = db.localTaskDao()
}
