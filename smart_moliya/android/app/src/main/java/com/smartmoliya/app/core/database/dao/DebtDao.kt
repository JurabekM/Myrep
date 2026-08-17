package com.smartmoliya.app.core.database.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import com.smartmoliya.app.core.database.entity.DebtEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface DebtDao {
    @Query("SELECT * FROM debts ORDER BY dueDate")
    fun observeAll(): Flow<List<DebtEntity>>

    @Upsert
    suspend fun upsert(debt: DebtEntity)
}
