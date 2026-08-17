package com.agrovision.app.data.repo

import com.agrovision.app.core.round1
import com.agrovision.app.data.local.CreditRow
import com.agrovision.app.data.local.FinanceDao
import com.agrovision.app.data.local.FinanceListRow
import javax.inject.Inject
import javax.inject.Singleton

data class YearFinance(
    val year: Int,
    val income: Double,
    val expense: Double,
    val credit: Double,
    val subsidy: Double,
    val profit: Double,
    val roi: Double,
)

data class EntityFinance(val name: String, val income: Double, val expense: Double) {
    val profit: Double get() = income - expense
    val roi: Double get() = if (expense > 0) (profit / expense * 100).round1() else 0.0
}

@Singleton
class FinanceRepository @Inject constructor(private val financeDao: FinanceDao) {

    suspend fun yearlySummary(): List<YearFinance> = financeDao.yearlySummary().map {
        val profit = it.income - it.expense
        YearFinance(
            year = it.year, income = it.income, expense = it.expense,
            credit = it.credit, subsidy = it.subsidy, profit = profit,
            roi = if (it.expense > 0) (profit / it.expense * 100).round1() else 0.0,
        )
    }

    suspend fun byRegion(year: Int): List<EntityFinance> = financeDao.byRegion(year)
        .map { EntityFinance(it.region, it.income, it.expense) }
        .sortedByDescending { it.profit }

    suspend fun farmRanking(year: Int, limit: Int = 15): List<EntityFinance> =
        financeDao.farmProfitability(year)
            .map { EntityFinance(it.farm, it.income, it.expense) }
            .sortedByDescending { it.profit }
            .take(limit)

    /** Zarar bilan ishlayotgan xo'jaliklar (ogohlantirish uchun). */
    suspend fun losingFarms(year: Int, limit: Int = 2): List<EntityFinance> =
        financeDao.farmProfitability(year)
            .map { EntityFinance(it.farm, it.income, it.expense) }
            .filter { it.profit < 0 }
            .sortedBy { it.profit }
            .take(limit)

    suspend fun creditsAndSubsidies(year: Int): List<CreditRow> = financeDao.creditsAndSubsidies(year)

    suspend fun recentList(): List<FinanceListRow> = financeDao.recentList()
}
