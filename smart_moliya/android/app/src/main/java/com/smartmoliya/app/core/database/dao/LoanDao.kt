package com.smartmoliya.app.core.database.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import com.smartmoliya.app.core.database.entity.LoanEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface LoanDao {
    @Query("SELECT * FROM loans ORDER BY dueDate")
    fun observeAll(): Flow<List<LoanEntity>>

    @Upsert
    suspend fun upsert(loan: LoanEntity)
}
