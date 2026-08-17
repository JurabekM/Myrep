package com.smartmoliya.app.feature.expense.domain

import kotlinx.coroutines.flow.Flow

data class Category(
    val id: String,
    val name: String,
    val type: String, // INCOME | EXPENSE
    val icon: String
)

interface CategoryRepository {
    fun observeCategories(): Flow<List<Category>>

    /** Online rejimda serverdan tortadi; offline rejimda hech narsa qilmaydi. */
    suspend fun refresh()

    /** Offline rejimda baza bo'sh bo'lsa standart kategoriyalarni yozadi (idempotent). */
    suspend fun ensureSeedData()
}
