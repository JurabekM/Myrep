package uz.dehqonkomakchi.app.data.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "diagnosis_records")
data class DiagnosisRecordEntity(
    @PrimaryKey val id: String,
    val photoPath: String,
    val category: String,
    val confidence: Float,
    val causeText: String,
    val stepsText: String,
    val watchText: String,
    val consultText: String,
    val createdAtEpochMillis: Long,
    val usefulRating: Int? = null, // null = not rated, 1 = useful, 0 = not useful
)

@Entity(tableName = "expenses")
data class ExpenseEntity(
    @PrimaryKey val id: String,
    val category: String,
    val amount: Double,
    val note: String,
    val dateEpochDay: Long,
    val createdAtEpochMillis: Long,
)

@Entity(tableName = "harvests")
data class HarvestEntity(
    @PrimaryKey val id: String,
    val quantity: Double,
    val unit: String,
    val dateEpochDay: Long,
    val createdAtEpochMillis: Long,
)

@Entity(tableName = "sales")
data class SaleEntity(
    @PrimaryKey val id: String,
    val product: String,
    val quantity: Double,
    val price: Double,
    val buyerType: String,
    val dateEpochDay: Long,
    val createdAtEpochMillis: Long,
)

@Entity(tableName = "listings")
data class ListingEntity(
    @PrimaryKey val id: String,
    val variety: String,
    val quantityKg: Double,
    val priceSom: Double?,
    val negotiable: Boolean,
    val region: String,
    val availabilityEpochDay: Long,
    val photoPath: String?,
    val contactMethod: String, // "phone" | "telegram"
    val contactValue: String,
    val contactConsent: Boolean,
    val ownerName: String,
    val groupId: String? = null,
    val createdAtEpochMillis: Long,
    val reported: Boolean = false,
)

@Entity(tableName = "listing_reports")
data class ListingReportEntity(
    @PrimaryKey val id: String,
    val listingId: String,
    val reason: String,
    val note: String,
    val createdAtEpochMillis: Long,
)

@Entity(tableName = "sell_groups")
data class SellGroupEntity(
    @PrimaryKey val id: String,
    val name: String,
    val region: String,
    val adminName: String,
    val isAdmin: Boolean,
    val createdAtEpochMillis: Long,
)

@Entity(tableName = "weather_cache")
data class WeatherCacheEntity(
    @PrimaryKey val region: String,
    val payloadJson: String,
    val fetchedAtEpochMillis: Long,
)
