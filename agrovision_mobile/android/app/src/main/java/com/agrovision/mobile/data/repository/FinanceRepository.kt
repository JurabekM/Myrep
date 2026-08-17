package com.agrovision.mobile.data.repository

import com.agrovision.mobile.data.local.*
import javax.inject.Inject
import javax.inject.Singleton

data class YearFinance(
    val year: Int, val income: Double, val expense: Double,
    val credit: Double, val subsidy: Double, val profit: Double, val roi: Double,
)

@Singleton
class FinanceRepository @Inject constructor(private val financeDao: FinanceDao) {

    suspend fun yearlySummary(): List<YearFinance> = financeDao.yearlySummary().map {
        val profit = it.income - it.expense
        YearFinance(
            it.year, it.income, it.expense, it.credit, it.subsidy, profit,
            if (it.expense > 0) Math.round(profit / it.expense * 1000) / 10.0 else 0.0,
        )
    }

    suspend fun byRegion(year: Int): List<RegionFinanceRow> =
        financeDao.byRegion(year).sortedByDescending { it.income - it.expense }

    suspend fun farmProfitability(year: Int, limit: Int = 15): List<FarmFinanceRow> =
        financeDao.farmProfitability(year).sortedByDescending { it.income - it.expense }.take(limit)
}
