package com.agrovision.mobile.data.repository

import com.agrovision.mobile.data.local.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SatelliteRepository @Inject constructor(private val satelliteDao: SatelliteDao) {
    suspend fun fieldHealth(): List<FieldHealthRow> = satelliteDao.fieldHealth()
    suspend fun series(fieldId: Long): List<NdviPointRow> = satelliteDao.series(fieldId)

    fun classify(ndvi: Double): String = when {
        ndvi >= 0.55 -> "A'lo"
        ndvi >= 0.40 -> "Yaxshi"
        ndvi >= 0.25 -> "O'rtacha"
        else -> "Zaif"
    }
}
