package com.smartmoliya.app.feature.expense.data

import com.smartmoliya.app.core.database.entity.TransactionEntity
import com.smartmoliya.app.core.network.dto.TransactionDto
import com.smartmoliya.app.feature.expense.domain.Transaction
import com.smartmoliya.app.feature.expense.domain.TransactionType
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

private val isoFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).apply {
    timeZone = TimeZone.getTimeZone("UTC")
}

fun TransactionEntity.toDomain() = Transaction(
    id = id,
    walletId = walletId,
    categoryId = categoryId,
    type = TransactionType.valueOf(type),
    amount = amount,
    currency = currency,
    note = note,
    occurredAt = occurredAt
)

fun TransactionDto.toEntity(syncStatus: String = "SYNCED") = TransactionEntity(
    id = id,
    walletId = wallet_id,
    categoryId = category_id,
    type = type.uppercase(),
    amount = amount,
    currency = currency,
    note = note,
    source = source.uppercase(),
    occurredAt = parseIsoToMillis(occurred_at),
    syncStatus = syncStatus,
    version = version
)

fun parseIsoToMillis(iso: String): Long =
    runCatching { isoFormat.parse(iso.substringBefore("+").substringBefore("Z"))?.time }
        .getOrNull() ?: System.currentTimeMillis()

fun millisToIso(millis: Long): String = isoFormat.format(Date(millis))
