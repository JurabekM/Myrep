package com.smartmoliya.app.feature.wallets.data

import com.smartmoliya.app.core.database.entity.WalletEntity
import com.smartmoliya.app.core.network.dto.WalletDto
import com.smartmoliya.app.feature.wallets.domain.Wallet

fun WalletEntity.toDomain() = Wallet(
    id = id,
    name = name,
    currency = currency,
    balance = balance,
    isShared = isShared
)

fun WalletDto.toEntity(syncStatus: String = "SYNCED") = WalletEntity(
    id = id,
    name = name,
    currency = currency,
    balance = balance,
    isShared = is_shared,
    syncStatus = syncStatus,
    version = version,
    updatedAt = System.currentTimeMillis()
)
