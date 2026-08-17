package com.smartmoliya.app.feature.wallets.domain

import kotlinx.coroutines.flow.Flow

interface WalletRepository {
    fun observeWallets(): Flow<List<Wallet>>
    suspend fun refresh()
    suspend fun createWallet(name: String, currency: String)
    suspend fun deleteWallet(walletId: String)
}
