package com.agrovision.mobile.data.local

/** DAO agregatsiya so'rovlari uchun POJO natijalar (Room ularni avtomatik to'ldiradi). */

data class YearYieldRow(val year: Int, val avgYield: Double, val production: Double)

data class RegionYieldRow(
    val region: String,
    val avgYield: Double,
    val production: Double,
    val area: Double,
)

data class CropAreaRow(
    val crop: String,
    val area: Double,
    val production: Double,
    val avgYield: Double,
)

data class RegionCropYieldRow(val region: String, val crop: String, val avgYield: Double)

data class FarmProductionRow(
    val farm: String,
    val region: String,
    val production: Double,
    val avgYield: Double,
)

data class DistrictYearPrecipRow(val districtId: Long, val year: Int, val precip: Double, val tAvg: Double, val humidity: Double)

data class DistrictYearYieldRow(val districtId: Long, val district: String, val year: Int, val avgYield: Double)

data class WeatherDailyRow(
    val epochDay: Long,
    val tMin: Double,
    val tMax: Double,
    val precipitationMm: Double,
    val humidity: Double,
)

data class WeatherMonthlyClimateRow(
    val month: Int,
    val tMax: Double,
    val tMin: Double,
    val precip: Double,
    val humidity: Double,
)

data class LatestPriceRow(
    val cropId: Long,
    val crop: String,
    val price: Double,
    val epochDay: Long,
)

data class PricePointRow(val epochDay: Long, val price: Double)

data class RegionWaterRow(val region: String, val waterMlnM3: Double, val area: Double)

data class MethodWaterRow(val method: String, val waterMlnM3: Double, val events: Int)

data class MonthWaterRow(val month: Int, val waterMlnM3: Double)

data class CropEfficiencyRow(val crop: String, val production: Double, val waterM3: Double)

data class YearFinanceRow(
    val year: Int,
    val income: Double,
    val expense: Double,
    val credit: Double,
    val subsidy: Double,
)

data class RegionFinanceRow(
    val region: String,
    val income: Double,
    val expense: Double,
)

data class FarmFinanceRow(
    val farm: String,
    val region: String,
    val income: Double,
    val expense: Double,
)

data class FieldHealthRow(
    val fieldId: Long,
    val field: String,
    val farm: String,
    val region: String,
    val ndvi: Double,
    val evi: Double,
)

data class NdviPointRow(val epochDay: Long, val ndvi: Double, val evi: Double)

data class FieldLabelRow(val id: Long, val label: String)

data class SearchRow(val turi: String, val nomi: String, val tafsilot: String)

data class YieldTrainRow(
    val fieldId: Long,
    val districtId: Long,
    val year: Int,
    val cropId: Long,
    val regionId: Long,
    val areaHa: Double,
    val waterNeedMm: Double,
    val fertility: Double,
    val yieldTHa: Double,
)

data class KpiCountsRow(
    val farms: Int,
    val farmers: Int,
    val fields: Int,
    val crops: Int,
    val area: Double,
)

data class FarmerListRow(val id: Long, val name: String, val phone: String, val district: String)
data class FarmListRow(val id: Long, val name: String, val farmer: String, val areaHa: Double)
data class FieldListRow(val id: Long, val name: String, val farm: String, val areaHa: Double, val soilType: String)
data class YieldListRow(val id: Long, val field: String, val crop: String, val year: Int, val yieldTHa: Double, val productionT: Double)
data class IrrigationListRow(val id: Long, val field: String, val epochDay: Long, val waterM3: Double, val method: String)
data class FinanceListRow(val id: Long, val farm: String, val year: Int, val category: String, val amount: Double, val note: String)
data class SatelliteListRow(val id: Long, val field: String, val epochDay: Long, val ndvi: Double)
