package com.smartmoliya.app.core.di

import com.smartmoliya.app.BuildConfig
import com.smartmoliya.app.feature.auth.data.AuthRepositoryImpl
import com.smartmoliya.app.feature.auth.data.OfflineAuthRepository
import com.smartmoliya.app.feature.auth.domain.AuthRepository
import com.smartmoliya.app.feature.expense.data.CategoryRepositoryImpl
import com.smartmoliya.app.feature.expense.data.TransactionRepositoryImpl
import com.smartmoliya.app.feature.expense.domain.CategoryRepository
import com.smartmoliya.app.feature.expense.domain.TransactionRepository
import com.smartmoliya.app.feature.wallets.data.WalletRepositoryImpl
import com.smartmoliya.app.feature.wallets.domain.WalletRepository
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindWalletRepository(impl: WalletRepositoryImpl): WalletRepository

    @Binds
    @Singleton
    abstract fun bindTransactionRepository(impl: TransactionRepositoryImpl): TransactionRepository

    @Binds
    @Singleton
    abstract fun bindCategoryRepository(impl: CategoryRepositoryImpl): CategoryRepository

    companion object {
        /** Flavor'ga qarab auth almashtiriladi: offline'da server/login umuman yo'q. */
        @Provides
        @Singleton
        fun provideAuthRepository(
            online: AuthRepositoryImpl,
            offline: OfflineAuthRepository
        ): AuthRepository = if (BuildConfig.OFFLINE_MODE) offline else online
    }
}
