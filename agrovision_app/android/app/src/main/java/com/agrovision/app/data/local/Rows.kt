package com.agrovision.app.data.local

/**
 * DAO agregatsiya so'rovlari qaytaradigan POJO natijalar — desktop
 * `read_df(...)` DataFrame'larining tipli ekvivalenti.
 */

// ---- KPI / hosildorlik ----
data class KpiCountsRow(val farms: Int, val farmers: Int, val fields: Int, val crops: Int, val area: Double)
data class YearYieldRow(val year: Int, val avgYield: Double, val production: Double)
data class RegionYieldRow(val region: String, val avgYield: Double, val production: Double, val area: Double)
data class CropAreaRow(val crop: String, val area: Double, val production: Double, val avgYield: Double)
data class RegionCropRow(val region: String, val crop: String, val avgYield: Double)
data class FarmProductionRow(val farm: String, val region: String, val production: Double, val avgYield: Double)
data class DistrictYearYieldRow(val districtId: Long, val district: String, val year: Int, val avgYield: Double)

// ---- Ob-havo ----
data class WeatherDailyRow(
    val epochDay: Long, val tMin: Double, val tMax: Double,
    val precipitationMm: Double, val humidity: Double,
)
data class MonthClimateRow(val month: Int, val tMax: Double, val tMin: Double, val precip: Double, val humidity: Double)
data class DistrictSeasonRow(val districtId: Long, val year: Int, val precip: Double, val tAvg: Double, val humidity: Double)
data class RegionSeasonRow(val region: String, val year: Int, val precip: Double, val tAvg: Double, val humidity: Double)
data class SeasonAggRow(val precip: Double?, val tAvg: Double?, val humidity: Double?)

// ---- Bozor ----
data class LatestPriceRow(val cropId: Long, val crop: String, val price: Double, val epochDay: Long)
data class PricePointRow(val epochDay: Long, val price: Double)
data class CropPriceRow(val crop: String, val epochDay: Long, val price: Double)

// ---- Sug'orish ----
data class RegionWaterRow(val region: String, val waterMlnM3: Double, val area: Double)
data class MethodWaterRow(val method: String, val waterMlnM3: Double, val events: Int)
data class MonthWaterRow(val month: Int, val waterMlnM3: Double)
data class CropEfficiencyRow(val crop: String, val production: Double, val waterM3: Double)
data class FieldYearWaterRow(val fieldId: Long, val year: Int, val waterM3: Double)
data class RegionYearWaterRow(val regionId: Long, val year: Int, val waterM3: Double)

// ---- Moliya ----
data class YearFinanceRow(val year: Int, val income: Double, val expense: Double, val credit: Double, val subsidy: Double)
data class RegionFinanceRow(val region: String, val income: Double, val expense: Double)
data class FarmFinanceRow(val farm: String, val region: String, val income: Double, val expense: Double)
data class CreditRow(val farm: String, val category: String, val amount: Double, val note: String)

// ---- Sun'iy yo'ldosh ----
data class FieldHealthRow(
    val fieldId: Long, val field: String, val farm: String, val region: String,
    val ndvi: Double, val evi: Double, val epochDay: Long,
)
data class NdviPointRow(val epochDay: Long, val ndvi: Double, val evi: Double)

// ---- Xarita ----
data class MapFieldRow(
    val id: Long, val name: String, val areaHa: Double, val soilType: String,
    val lat: Double, val lon: Double, val polygon: String,
    val farm: String, val farmer: String, val region: String, val regionId: Long,
    val district: String, val yieldTHa: Double, val crop: String, val ndvi: Double,
)

// ---- ML o'qitish ----
data class YieldTrainRow(
    val yieldTHa: Double, val areaHa: Double, val year: Int, val cropId: Long,
    val waterNeedMm: Double, val regionId: Long, val fertility: Double,
    val districtId: Long, val fieldId: Long,
)
data class CropProfitRow(
    val cropId: Long, val year: Int, val districtId: Long, val regionId: Long,
    val fertility: Double, val avgYield: Double, val basePricePerKg: Double, val costPerHa: Double,
)
data class MonthWeatherRow(
    val districtId: Long, val year: Int, val month: Int,
    val humidity: Double, val tAvg: Double, val precip: Double,
)

// ---- Ro'yxatlar (CRUD ekranlari) ----
data class FarmerListRow(val id: Long, val name: String, val phone: String, val district: String)
data class FarmListRow(val id: Long, val name: String, val farmer: String, val district: String, val areaHa: Double)
data class FieldListRow(val id: Long, val name: String, val farm: String, val areaHa: Double, val soilType: String)
data class YieldListRow(val id: Long, val field: String, val crop: String, val year: Int, val yieldTHa: Double, val productionT: Double)
data class IrrigationListRow(val id: Long, val field: String, val epochDay: Long, val waterM3: Double, val method: String)
data class FinanceListRow(val id: Long, val farm: String, val year: Int, val category: String, val amount: Double, val note: String)
data class NdviListRow(val id: Long, val field: String, val epochDay: Long, val ndvi: Double, val evi: Double)
data class FieldLabelRow(
    val id: Long,
    val label: String,
    /** Onlayn xaritani shu dalaga markazlash uchun. */
    val lat: Double = 0.0,
    val lon: Double = 0.0,
    val polygon: String = "",
)

// ---- Global qidiruv ----
data class SearchRow(val turi: String, val nomi: String, val tafsilot: String)

// ---- Tuproq tahlili (plagin analogi) ----
data class SoilStatRow(val soilType: String, val fields: Int, val areaHa: Double, val avgYield: Double)

// ---- Eksport datasetlari ----
data class ExportYieldRow(
    val year: Int, val region: String, val district: String, val farm: String,
    val field: String, val crop: String, val areaHa: Double, val yieldTHa: Double, val productionT: Double,
)
data class ExportWeatherRow(
    val epochDay: Long, val district: String, val tMin: Double, val tMax: Double,
    val precipitationMm: Double, val humidity: Double, val source: String,
)
data class ExportPriceRow(val epochDay: Long, val crop: String, val pricePerKg: Double, val marketName: String, val source: String)
data class ExportFinanceRow(val year: Int, val farm: String, val category: String, val amount: Double, val note: String)
data class ExportIrrigationRow(val epochDay: Long, val field: String, val waterM3: Double, val method: String)
data class ExportNdviRow(val epochDay: Long, val field: String, val ndvi: Double, val evi: Double, val source: String)
data class ExportFieldGeoRow(val name: String, val areaHa: Double, val soilType: String, val polygon: String, val farm: String, val region: String)

// ---- Baza statistikasi ----
data class TableCountRow(val table: String, val rows: Int)
