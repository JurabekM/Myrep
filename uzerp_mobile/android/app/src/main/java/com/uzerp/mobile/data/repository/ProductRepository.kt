package com.uzerp.mobile.data.repository

import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.ValidationException
import com.uzerp.mobile.core.d
import com.uzerp.mobile.data.local.dao.CategoryDao
import com.uzerp.mobile.data.local.dao.ProductDao
import com.uzerp.mobile.data.local.entity.CategoryEntity
import com.uzerp.mobile.data.local.entity.ProductEntity
import java.math.BigDecimal
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.first

const val PAGE_SIZE = 25

/** Sahifalangan natija — Python `Page` bilan bir xil shakl. */
data class PageResult<T>(
    val items: List<T>,
    val page: Int,
    val perPage: Int,
    val total: Int,
) {
    val pages: Int get() = maxOf(1, (total + perPage - 1) / perPage)
}

/**
 * Mahsulotlar katalogi servisi — Python `ProductService` bilan bir xil
 * qoidalar: avto-SKU, shtrix-kod qidiruvi, min. zaxira nazorati.
 */
@Singleton
class ProductRepository @Inject constructor(
    private val productDao: ProductDao,
    private val categoryDao: CategoryDao,
) {
    suspend fun list(page: Int = 1, search: String? = null, categoryId: Long? = null): PageResult<ProductEntity> {
        val offset = (page - 1) * PAGE_SIZE
        val term = search?.trim()?.ifBlank { null }
        val items = productDao.search(term, categoryId, PAGE_SIZE, offset)
        val total = productDao.searchCount(term, categoryId)
        return PageResult(items, page, PAGE_SIZE, total)
    }

    suspend fun get(id: Long): ProductEntity =
        productDao.getById(id) ?: throw ValidationException("Mahsulot topilmadi (id=$id).")

    suspend fun create(
        name: String,
        salePrice: BigDecimal,
        costPrice: BigDecimal = BigDecimal.ZERO,
        barcode: String = "",
        unit: String = "dona",
        vatRate: BigDecimal = BigDecimal("12"),
        minStock: BigDecimal = BigDecimal.ZERO,
        categoryId: Long? = null,
        description: String = "",
    ): Long {
        val trimmedName = name.trim()
        if (trimmedName.isBlank()) throw ValidationException("Mahsulot nomi bo'sh bo'lishi mumkin emas.")
        if (salePrice < BigDecimal.ZERO || costPrice < BigDecimal.ZERO) {
            throw ValidationException("Narx manfiy bo'lishi mumkin emas.")
        }
        val now = DateUtils.nowStr()
        val id = productDao.insert(
            ProductEntity(
                name = trimmedName,
                barcode = barcode.trim(),
                salePrice = d(salePrice),
                costPrice = d(costPrice),
                unit = unit,
                vatRate = d(vatRate),
                minStock = d(minStock),
                categoryId = categoryId,
                description = description,
                createdAt = now,
                updatedAt = now,
            ),
        )
        productDao.setSku(id, "P%06d".format(id))
        return id
    }

    suspend fun update(product: ProductEntity) {
        if (product.name.isBlank()) throw ValidationException("Mahsulot nomi bo'sh bo'lishi mumkin emas.")
        productDao.update(product.copy(updatedAt = DateUtils.nowStr()))
    }

    suspend fun deactivate(id: Long) = productDao.deactivate(id)

    suspend fun findByBarcode(barcode: String): ProductEntity? =
        productDao.findByBarcode(barcode.trim())

    suspend fun updateCostPrice(id: Long, newCost: BigDecimal) = productDao.setCostPrice(id, d(newCost))

    suspend fun categories(): List<CategoryEntity> = categoryDao.observeAll().first()

    suspend fun createCategory(name: String): Long {
        val trimmed = name.trim()
        if (trimmed.isBlank()) throw ValidationException("Kategoriya nomi bo'sh bo'lishi mumkin emas.")
        return categoryDao.insert(CategoryEntity(name = trimmed))
    }
}
