package com.smartmoliya.app.feature.expense.data

import com.smartmoliya.app.core.database.entity.TransactionEntity
import com.smartmoliya.app.core.network.dto.TransactionDto
import com.smartmoliya.app.feature.expense.domain.TransactionType
import org.junit.Assert.assertEquals
import org.junit.Test

class TransactionMappersTest {

    @Test
    fun `entity toDomain maps type string to enum`() {
        val entity = TransactionEntity(
            id = "t1",
            walletId = "w1",
            categoryId = "c1",
            type = "EXPENSE",
            amount = 25000.0,
            currency = "UZS",
            note = "Ovqat",
            source = "MANUAL",
            occurredAt = 1_700_000_000_000,
            syncStatus = "SYNCED",
            version = 1
        )

        val domain = entity.toDomain()

        assertEquals(TransactionType.EXPENSE, domain.type)
        assertEquals("Ovqat", domain.note)
        assertEquals(25000.0, domain.amount, 0.0)
    }

    @Test
    fun `dto toEntity uppercases type and source`() {
        val dto = TransactionDto(
            id = "t2",
            wallet_id = "w1",
            category_id = null,
            type = "income",
            amount = 100000.0,
            currency = "UZS",
            note = null,
            source = "manual",
            occurred_at = "2026-07-12T10:30:00",
            sync_status = "synced",
            version = 1
        )

        val entity = dto.toEntity()

        assertEquals("INCOME", entity.type)
        assertEquals("MANUAL", entity.source)
    }

    @Test
    fun `parseIsoToMillis and millisToIso round-trip preserves the timestamp`() {
        val originalMillis = 1_752_312_600_000L // 2025-07-12T10:30:00Z atrofida
        val iso = millisToIso(originalMillis)
        val parsedBack = parseIsoToMillis(iso)

        assertEquals(originalMillis, parsedBack)
    }

    @Test
    fun `parseIsoToMillis falls back to now for unparsable input instead of crashing`() {
        val before = System.currentTimeMillis()
        val result = parseIsoToMillis("not-a-date")
        val after = System.currentTimeMillis()

        assert(result in before..after)
    }
}
