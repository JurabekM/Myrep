package com.agrovision.mobile.data.local

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Room entities — desktop AgroVision (SQLAlchemy, database/models.py) sxemasining
 * mobil ko'chirmasi. Ma'lumot mustaqil ravishda qurilma ichida yaratiladi va
 * saqlanadi; hech qanday tarmoq sinxronizatsiyasi yo'q (to'liq avtonom).
 */

@Entity(tableName = "users")
data class UserEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val username: String,
    val fullName: String,
    val passwordHash: String,
    val role: String, // admin | manager | viewer
    val active: Boolean = true,
    val createdAt: Long = System.currentTimeMillis(),
)

@Entity(tableName = "audit_log")
data class AuditLogEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val timestamp: Long = System.currentTimeMillis(),
    val username: String,
    val action: String,
    val details: String = "",
)

@Entity(tableName = "settings")
data class SettingEntity(
    @PrimaryKey val key: String,
    val value: String,
)

@Entity(tableName = "regions")
data class RegionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val lat: Double,
    val lon: Double,
    val fertility: Double,
)

@Entity(
    tableName = "districts",
    foreignKeys = [ForeignKey(RegionEntity::class, ["id"], ["regionId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("regionId")],
)
data class DistrictEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val regionId: Long,
    val name: String,
    val lat: Double,
    val lon: Double,
)

@Entity(
    tableName = "farmers",
    foreignKeys = [ForeignKey(DistrictEntity::class, ["id"], ["districtId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("districtId")],
)
data class FarmerEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val phone: String,
    val districtId: Long,
)

@Entity(
    tableName = "farms",
    foreignKeys = [
        ForeignKey(FarmerEntity::class, ["id"], ["farmerId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(DistrictEntity::class, ["id"], ["districtId"], onDelete = ForeignKey.CASCADE),
    ],
    indices = [Index("farmerId"), Index("districtId")],
)
data class FarmEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val farmerId: Long,
    val districtId: Long,
    val areaHa: Double,
)

@Entity(
    tableName = "fields",
    foreignKeys = [ForeignKey(FarmEntity::class, ["id"], ["farmId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("farmId")],
)
data class FieldEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val farmId: Long,
    val name: String,
    val areaHa: Double,
    val soilType: String,
    val lat: Double,
    val lon: Double,
    /** Vergul bilan ajratilgan "lon:lat" nuqtalar — GeoJSON o'rniga yengil format. */
    val polygonPoints: String,
)

@Entity(tableName = "crops")
data class CropEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val category: String,
    val season: String,
    val waterNeedMm: Double,
    val baseYieldTHa: Double,
    val basePricePerKg: Double,
    val costPerHa: Double,
)

@Entity(
    tableName = "yield_records",
    foreignKeys = [
        ForeignKey(FieldEntity::class, ["id"], ["fieldId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(CropEntity::class, ["id"], ["cropId"], onDelete = ForeignKey.CASCADE),
    ],
    indices = [Index("fieldId"), Index("cropId"), Index("year")],
)
data class YieldRecordEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val fieldId: Long,
    val cropId: Long,
    val year: Int,
    val areaHa: Double,
    val yieldTHa: Double,
    val productionT: Double,
)

@Entity(
    tableName = "weather_records",
    foreignKeys = [ForeignKey(DistrictEntity::class, ["id"], ["districtId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("districtId"), Index("epochDay")],
)
data class WeatherRecordEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val districtId: Long,
    /** java.time.LocalDate.toEpochDay() */
    val epochDay: Long,
    val tMin: Double,
    val tMax: Double,
    val precipitationMm: Double,
    val humidity: Double,
)

@Entity(
    tableName = "market_prices",
    foreignKeys = [ForeignKey(CropEntity::class, ["id"], ["cropId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("cropId"), Index("epochDay")],
)
data class MarketPriceEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val cropId: Long,
    val epochDay: Long,
    val pricePerKg: Double,
    val marketName: String = "Milliy bozor",
    val source: String = "demo",
)

@Entity(
    tableName = "irrigation_records",
    foreignKeys = [ForeignKey(FieldEntity::class, ["id"], ["fieldId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("fieldId"), Index("epochDay")],
)
data class IrrigationRecordEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val fieldId: Long,
    val epochDay: Long,
    val waterM3: Double,
    val method: String,
)

@Entity(
    tableName = "finance_records",
    foreignKeys = [ForeignKey(FarmEntity::class, ["id"], ["farmId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("farmId"), Index("year")],
)
data class FinanceRecordEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val farmId: Long,
    val year: Int,
    val category: String, // income | expense | credit | subsidy
    val amount: Double,
    val note: String = "",
)

@Entity(
    tableName = "satellite_indices",
    foreignKeys = [ForeignKey(FieldEntity::class, ["id"], ["fieldId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("fieldId"), Index("epochDay")],
)
data class SatelliteIndexEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val fieldId: Long,
    val epochDay: Long,
    val ndvi: Double,
    val evi: Double,
)

/** ML regressiya koeffitsientlarini saqlash uchun (mahalliy o'qitilgan chiziqli model). */
@Entity(tableName = "ml_models")
data class MlModelEntity(
    @PrimaryKey val name: String, // "yield"
    /** Vergul bilan ajratilgan koeffitsientlar: intercept,b1,b2,... */
    val coefficients: String,
    val rSquared: Double,
    val trainedAt: Long,
)
