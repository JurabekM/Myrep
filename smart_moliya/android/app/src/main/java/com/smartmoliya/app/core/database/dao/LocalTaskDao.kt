package com.smartmoliya.app.core.database.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import com.smartmoliya.app.core.database.entity.LocalTaskEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface LocalTaskDao {
    @Query("SELECT * FROM local_tasks ORDER BY createdAt DESC")
    fun observeAll(): Flow<List<LocalTaskEntity>>

    @Query("SELECT * FROM local_tasks WHERE id = :id")
    suspend fun getById(id: String): LocalTaskEntity?

    @Upsert
    suspend fun upsert(task: LocalTaskEntity)

    @Query("DELETE FROM local_tasks WHERE id = :id")
    suspend fun deleteById(id: String)
}
