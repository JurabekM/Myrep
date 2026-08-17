package com.uzerp.mobile.data.repository

import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.NotFoundException
import com.uzerp.mobile.core.ValidationException
import com.uzerp.mobile.core.d
import com.uzerp.mobile.data.local.dao.CustomerDao
import com.uzerp.mobile.data.local.dao.SupplierDao
import com.uzerp.mobile.data.local.entity.CustomerEntity
import com.uzerp.mobile.data.local.entity.SupplierEntity
import java.math.BigDecimal
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CustomerRepository @Inject constructor(
    private val customerDao: CustomerDao,
) {
    suspend fun list(page: Int = 1, search: String? = null): PageResult<CustomerEntity> {
        val term = search?.trim()?.ifBlank { null }
        val offset = (page - 1) * PAGE_SIZE
        val items = customerDao.search(term, PAGE_SIZE, offset)
        val total = customerDao.searchCount(term)
        return PageResult(items, page, PAGE_SIZE, total)
    }

    suspend fun get(id: Long): CustomerEntity =
        customerDao.getById(id) ?: throw NotFoundException("Mijoz topilmadi (id=$id).")

    suspend fun create(
        name: String,
        phone: String = "",
        tin: String = "",
        email: String = "",
        address: String = "",
        discountPercent: BigDecimal = BigDecimal.ZERO,
    ): Long {
        val trimmed = name.trim()
        if (trimmed.isBlank()) throw ValidationException("Mijoz nomi bo'sh bo'lishi mumkin emas.")
        if (discountPercent < BigDecimal.ZERO || discountPercent > BigDecimal(100)) {
            throw ValidationException("Chegirma 0 dan 100 gacha bo'lishi kerak.")
        }
        val now = DateUtils.nowStr()
        return customerDao.insert(
            CustomerEntity(
                name = trimmed, phone = phone, tin = tin, email = email, address = address,
                discountPercent = d(discountPercent), createdAt = now, updatedAt = now,
            ),
        )
    }

    suspend fun update(customer: CustomerEntity) {
        if (customer.name.isBlank()) throw ValidationException("Mijoz nomi bo'sh bo'lishi mumkin emas.")
        customerDao.update(customer.copy(updatedAt = DateUtils.nowStr()))
    }
}

@Singleton
class SupplierRepository @Inject constructor(
    private val supplierDao: SupplierDao,
) {
    suspend fun list(page: Int = 1, search: String? = null): PageResult<SupplierEntity> {
        val term = search?.trim()?.ifBlank { null }
        val offset = (page - 1) * PAGE_SIZE
        val items = supplierDao.search(term, PAGE_SIZE, offset)
        return PageResult(items, page, PAGE_SIZE, Int.MAX_VALUE)
    }

    suspend fun get(id: Long): SupplierEntity =
        supplierDao.getById(id) ?: throw NotFoundException("Ta'minotchi topilmadi (id=$id).")

    suspend fun create(name: String, phone: String = "", tin: String = "", email: String = "", address: String = ""): Long {
        val trimmed = name.trim()
        if (trimmed.isBlank()) throw ValidationException("Ta'minotchi nomi bo'sh bo'lishi mumkin emas.")
        val now = DateUtils.nowStr()
        return supplierDao.insert(
            SupplierEntity(name = trimmed, phone = phone, tin = tin, email = email, address = address, createdAt = now, updatedAt = now),
        )
    }

    suspend fun update(supplier: SupplierEntity) {
        if (supplier.name.isBlank()) throw ValidationException("Ta'minotchi nomi bo'sh bo'lishi mumkin emas.")
        supplierDao.update(supplier.copy(updatedAt = DateUtils.nowStr()))
    }
}
