package com.smartmoliya.app.feature.expense.data

import com.smartmoliya.app.BuildConfig
import com.smartmoliya.app.core.database.dao.CategoryDao
import com.smartmoliya.app.core.database.entity.CategoryEntity
import com.smartmoliya.app.core.network.ApiService
import com.smartmoliya.app.feature.expense.domain.Category
import com.smartmoliya.app.feature.expense.domain.CategoryRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject

/** Offline flavor'da bazaga yoziladigan standart kategoriyalar (id'lar barqaror). */
private val SEED_CATEGORIES = listOf(
    CategoryEntity("seed-inc-salary", null, "Maosh", "INCOME", "salary"),
    CategoryEntity("seed-inc-bonus", null, "Bonus", "INCOME", "bonus"),
    CategoryEntity("seed-inc-gift", null, "Sovg'a", "INCOME", "gift"),
    CategoryEntity("seed-inc-other", null, "Boshqa daromad", "INCOME", "other"),
    CategoryEntity("seed-exp-food", null, "Oziq-ovqat", "EXPENSE", "food"),
    CategoryEntity("seed-exp-transport", null, "Transport", "EXPENSE", "transport"),
    CategoryEntity("seed-exp-shopping", null, "Xarid", "EXPENSE", "shopping"),
    CategoryEntity("seed-exp-restaurant", null, "Restoran", "EXPENSE", "restaurant"),
    CategoryEntity("seed-exp-entertainment", null, "Ko'ngilochar", "EXPENSE", "entertainment"),
    CategoryEntity("seed-exp-medical", null, "Tibbiyot", "EXPENSE", "medical"),
    CategoryEntity("seed-exp-education", null, "Ta'lim", "EXPENSE", "education"),
    CategoryEntity("seed-exp-utilities", null, "Kommunal", "EXPENSE", "utilities"),
    CategoryEntity("seed-exp-internet", null, "Internet", "EXPENSE", "internet"),
    CategoryEntity("seed-exp-fuel", null, "Yoqilg'i", "EXPENSE", "fuel"),
    CategoryEntity("seed-exp-other", null, "Boshqa", "EXPENSE", "other"),
)

class CategoryRepositoryImpl @Inject constructor(
    private val api: ApiService,
    private val dao: CategoryDao
) : CategoryRepository {

    override fun observeCategories(): Flow<List<Category>> =
        dao.observeAll().map { entities ->
            entities.map { Category(id = it.id, name = it.name, type = it.type, icon = it.icon) }
        }

    override suspend fun refresh() {
        if (BuildConfig.OFFLINE_MODE) return
        val remote = api.listCategories()
        dao.upsertAll(
            remote.map {
                CategoryEntity(
                    id = it.id,
                    userId = it.user_id,
                    name = it.name,
                    type = it.type.uppercase(),
                    icon = it.icon
                )
            }
        )
    }

    override suspend fun ensureSeedData() {
        // Faqat offline rejimda: server kategoriyalari bilan ID to'qnashuvi bo'lmasligi uchun
        if (!BuildConfig.OFFLINE_MODE) return
        val existing = dao.observeAll().first()
        if (existing.isEmpty()) {
            dao.upsertAll(SEED_CATEGORIES)
        }
    }
}
