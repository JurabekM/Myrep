package com.smartmoliya.app.core.network.dto

data class CategoryBreakdownItemDto(
    val category_id: String,
    val category_name: String,
    val amount: Double,
    val percent: Double
)

data class DailyCashFlowItemDto(
    val date: String,
    val income: Double,
    val expense: Double,
    val net: Double
)

data class ReportSummaryDto(
    val start_date: String,
    val end_date: String,
    val total_income: Double,
    val total_expense: Double,
    val net: Double,
    val by_category: List<CategoryBreakdownItemDto>,
    val daily_cash_flow: List<DailyCashFlowItemDto>
)
