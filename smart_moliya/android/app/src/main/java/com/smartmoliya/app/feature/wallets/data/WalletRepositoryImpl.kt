package com.smartmoliya.app.feature.wallets.data

import android.util.Log
import com.smartmoliya.app.BuildConfig
import com.smartmoliya.app.core.database.dao.WalletDao
import com.smartmoliya.app.core.database.entity.WalletEntity
import com.smartmoliya.app.core.network.ApiService
import com.smartmoliya.app.core.network.dto.WalletCreateDto
import com.smartmoliya.app.feature.wallets.domain.Wallet
import com.smartmoliya.app.feature.wallets.domain.WalletRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.util.UUID
import javax.inject.Inject

class WalletRepositoryImpl @Inject constructor(
    private val api: ApiService,
    private val dao: WalletDao
) : WalletRepository {

    override fun observeWallets(): Flow<List<Wallet>> =
        dao.observeAll().map { entities -> entities.map { it.toDomain() } }

    /** Serverdan so'nggi holatni tortib, offline bazani yangilaydi (Room - yagona UI manbai). */
    override suspend fun refresh() {
        if (BuildConfig.OFFLINE_MODE) return
        val remoteWallets = api.listWallets()
        remoteWallets.forEach { dao.upsert(it.toEntity()) }
    }

    /** Offline-first: avval lokal bazaga PENDING sifatida yoziladi, so'ng serverga jo'natiladi. */
    override suspend fun createWallet(name: String, currency: String) {
        val id = UUID.randomUUID().toString()
        dao.upsert(
            WalletEntity(
                id = id,
                name = name,
                currency = currency,
                balance = 0.0,
                isShared = false,
                syncStatus = if (BuildConfig.OFFLINE_MODE) "SYNCED" else "PENDING",
                version = 1,
                updatedAt = System.currentTimeMillis()
            )
        )
        if (BuildConfig.OFFLINE_MODE) return
        try {
            val created = api.createWallet(WalletCreateDto(id = id, name = name, currency = currency))
            dao.upsert(created.toEntity())
        } catch (e: Exception) {
            Log.w(TAG, "createWallet: offline yoki server xatosi, keyinroq SyncWorker qayta urinadi", e)
        }
    }

    override suspend fun deleteWallet(walletId: String) {
        val wallet = dao.getById(walletId) ?: return
        dao.delete(wallet)
        if (BuildConfig.OFFLINE_MODE) return
        try {
            api.deleteWallet(walletId)
        } catch (e: Exception) {
            Log.w(TAG, "deleteWallet: server bilan sinxronlanmadi", e)
        }
    }

    companion object {
        private const val TAG = "WalletRepository"
    }
}
