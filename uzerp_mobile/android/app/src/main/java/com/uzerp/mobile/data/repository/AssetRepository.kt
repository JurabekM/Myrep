package com.uzerp.mobile.data.repository

import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.NotFoundException
import com.uzerp.mobile.core.StateException
import com.uzerp.mobile.core.ValidationException
import com.uzerp.mobile.core.d
import com.uzerp.mobile.data.local.dao.AssetDao
import com.uzerp.mobile.data.local.entity.AssetEntity
import java.math.BigDecimal
import java.math.RoundingMode
import javax.inject.Inject
import javax.inject.Singleton

data class DepreciationResult(val total: BigDecimal, val count: Int)

/**
 * Asosiy vositalar servisi — Python `AssetService` bilan bir xil:
 * to'g'ri chiziqli amortizatsiya, davr takrorlanishidan himoya.
 */
@Singleton
class AssetRepository @Inject constructor(
    private val assetDao: AssetDao,
    private val accountingRepository: AccountingRepository,
) {
    suspend fun createAsset(
        name: String,
        cost: BigDecimal,
        salvageValue: BigDecimal = BigDecimal.ZERO,
        usefulLifeMonths: Int = 60,
        purchaseDate: String? = null,
    ): Long {
        if (name.isBlank()) throw ValidationException("Aktiv nomi bo'sh bo'lishi mumkin emas.")
        val c = d(cost)
        val salvage = d(salvageValue)
        if (c <= BigDecimal.ZERO) throw ValidationException("Aktiv qiymati musbat bo'lishi kerak.")
        if (salvage < BigDecimal.ZERO || salvage >= c) throw ValidationException("Qoldiq qiymat 0 dan katta-teng va qiymatdan kichik bo'lsin.")
        if (usefulLifeMonths <= 0) throw ValidationException("Foydali muddat musbat bo'lishi kerak.")

        val id = assetDao.insert(
            AssetEntity(
                name = name.trim(), cost = c, salvageValue = salvage, usefulLifeMonths = usefulLifeMonths,
                purchaseDate = purchaseDate ?: DateUtils.todayStr(), status = "active", createdAt = DateUtils.nowStr(),
            ),
        )
        return id
    }

    suspend fun listAssets(page: Int = 1): PageResult<AssetEntity> {
        val offset = (page - 1) * PAGE_SIZE
        return PageResult(assetDao.page(PAGE_SIZE, offset), page, PAGE_SIZE, Int.MAX_VALUE)
    }

    fun bookValue(asset: AssetEntity): BigDecimal = d(asset.cost.subtract(asset.accumulatedDepreciation))

    fun monthlyDepreciation(asset: AssetEntity): BigDecimal {
        if (asset.usefulLifeMonths <= 0) return BigDecimal.ZERO
        return d(asset.cost.subtract(asset.salvageValue).divide(BigDecimal(asset.usefulLifeMonths), 10, RoundingMode.HALF_UP))
    }

    suspend fun runDepreciation(period: String, userId: Long?): DepreciationResult {
        if (period.length != 7 || period[4] != '-') throw ValidationException("Davr formati YYYY-MM bo'lishi kerak.")
        if (assetDao.depreciationExistsForPeriod(period)) {
            throw StateException("$period davri uchun amortizatsiya allaqachon hisoblangan.")
        }
        val assets = assetDao.activeAssets()
        var total = BigDecimal.ZERO
        var count = 0
        for (asset in assets) {
            val monthly = monthlyDepreciation(asset)
            val remaining = d(asset.cost.subtract(asset.salvageValue).subtract(asset.accumulatedDepreciation))
            val amount = if (monthly < remaining.max(BigDecimal.ZERO)) monthly else remaining.max(BigDecimal.ZERO)
            if (amount <= BigDecimal.ZERO) continue
            assetDao.setAccumulatedDepreciation(asset.id, d(asset.accumulatedDepreciation.add(amount)))
            total = d(total.add(amount))
            count++
        }
        if (total > BigDecimal.ZERO) {
            accountingRepository.createEntry(
                "Amortizatsiya $period",
                listOf(JournalLineInput("9410", debit = total), JournalLineInput("0200", credit = total)),
                "$period-28", "depreciation", null, userId,
            )
        }
        return DepreciationResult(total, count)
    }
}
