package com.smartmoliya.app.feature.wallets.data

import com.smartmoliya.app.core.database.entity.WalletEntity
import com.smartmoliya.app.core.network.dto.WalletDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class WalletMappersTest {

    @Test
    fun `entity toDomain maps all fields`() {
        val entity = WalletEntity(
            id = "wallet-1",
            name = "Asosiy",
            currency = "UZS",
            balance = 150000.0,
            isShared = false,
            syncStatus = "SYNCED",
            version = 2,
            updatedAt = 1_700_000_000_000
        )

        val domain = entity.toDomain()

        assertEquals("wallet-1", domain.id)
        assertEquals("Asosiy", domain.name)
        assertEquals("UZS", domain.currency)
        assertEquals(150000.0, domain.balance, 0.0)
        assertFalse(domain.isShared)
    }

    @Test
    fun `dto toEntity defaults syncStatus to SYNCED`() {
        val dto = WalletDto(
            id = "wallet-2",
            name = "Jamg'arma",
            currency = "USD",
            balance = 500.0,
            is_shared = true,
            version = 1
        )

        val entity = dto.toEntity()

        assertEquals("wallet-2", entity.id)
        assertEquals("SYNCED", entity.syncStatus)
        assertEquals(true, entity.isShared)
        assertEquals(1, entity.version)
    }

    @Test
    fun `dto toEntity respects explicit syncStatus override`() {
        val dto = WalletDto(id = "wallet-3", name = "X", currency = "UZS", balance = 0.0, is_shared = false, version = 1)
        val entity = dto.toEntity(syncStatus = "PENDING")
        assertEquals("PENDING", entity.syncStatus)
    }
}
