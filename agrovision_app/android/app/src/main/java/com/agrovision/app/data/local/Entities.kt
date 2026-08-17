package com.agrovision.app.data.local

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Room entity'lari — desktop AgroVision `database/models.py` faylining aynan
 * ko'chirmasi (16 jadval). Sana ustunlari `epochDay` (Long) sifatida
 * saqlanadi: SQLite'da `date(epochDay*86400,'unixepoch')` orqali desktopdagi
 * `strftime` so'rovlari bilan bir xil agregatsiya qilish mumkin.
 */

@Entity(tableName = "users", indices = [Index(value = ["username"], unique = true)])
data class UserEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val username: String,
    val fullName: String = "",
    val passwordHash: String,
    val role: String = "viewer",
    val active: Boolean = true,
    val createdAt: Long = System.currentTimeMillis(),
)

@Entity(tableName = "audit_log", indices = [Index("timestamp")])
data class AuditLogEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val timestamp: Long = System.currentTimeMillis(),
    val username: String = "system",
    val action: String,
    val details: String = "",
)

@Entity(tableName = "settings")
data class SettingEntity(
    @PrimaryKey val key: String,
    val value: String = "",
)

@Entity(tableName = "regions", indices = [Index(value = ["name"], unique = true)])
data class RegionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val lat: Double,
    val lon: Double,
    /** Nisbiy tuproq unumdorligi koeffitsienti. */
    val fertility: Double = 1.0,
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
    indices = [Index("name"), Index("districtId")],
)
data class FarmerEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val phone: String = "",
    val districtId: Long,
)

@Entity(
    tableName = "farms",
    foreignKeys = [
        ForeignKey(FarmerEntity::class, ["id"], ["farmerId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(DistrictEntity::class, ["id"], ["districtId"], onDelete = ForeignKey.CASCADE),
    ],
    indices = [Index("name"), Index("farmerId"), Index("districtId")],
)
data class FarmEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val farmerId: Long,
    val districtId: Long,
    val areaHa: Double = 0.0,
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
    val soilType: String = "bo'z tuproq",
    val lat: Double,
    val lon: Double,
    /** Poligon burchaklari "lon,lat;lon,lat;..." formatida (desktop GeoJSON ekvivalenti). */
    val polygon: String = "",
)

@Entity(tableName = "crops", indices = [Index(value = ["name"], unique = true)])
data class CropEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val category: String = "don",
    val season: String = "yozgi",
    val waterNeedMm: Double = 500.0,
    val baseYieldTHa: Double = 3.0,
    val basePricePerKg: Double = 3000.0,
    val costPerHa: Double = 6_000_000.0,
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
    val epochDay: Long,
    val tMin: Double,
    val tMax: Double,
    val precipitationMm: Double = 0.0,
    val humidity: Double = 50.0,
    val source: String = "demo",
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
    val method: String = "egat",
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
    /** income | expense | credit | subsidy */
    val category: String,
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
    val source: String = "demo",
)

@Entity(tableName = "imported_files")
data class ImportedFileEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val filename: String,
    val fileType: String,
    val uploadedAt: Long = System.currentTimeMillis(),
    val uploadedBy: String = "",
    val summary: String = "",
)

/** O'qitilgan ML modellarini saqlash (desktop'dagi .pkl fayllar analogi). */
@Entity(tableName = "ml_models")
data class MlModelEntity(
    @PrimaryKey val name: String,
    /** Model JSON serializatsiyasi (daraxtlar/ansambl). */
    val payload: String,
    val algorithm: String,
    val metric: Double,
    val metricName: String,
    val rows: Int,
    val trainedAt: Long,
)
