package com.uzerp.mobile.data.repository

import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.PasswordHasher
import com.uzerp.mobile.data.local.CHART_OF_ACCOUNTS
import com.uzerp.mobile.data.local.dao.AccountDao
import com.uzerp.mobile.data.local.dao.CategoryDao
import com.uzerp.mobile.data.local.dao.DepartmentDao
import com.uzerp.mobile.data.local.dao.SettingsDao
import com.uzerp.mobile.data.local.dao.UserDao
import com.uzerp.mobile.data.local.dao.WarehouseDao
import com.uzerp.mobile.data.local.entity.AccountEntity
import com.uzerp.mobile.data.local.entity.CategoryEntity
import com.uzerp.mobile.data.local.entity.DepartmentEntity
import com.uzerp.mobile.data.local.entity.SettingEntity
import com.uzerp.mobile.data.local.entity.UserEntity
import com.uzerp.mobile.data.local.entity.WarehouseEntity
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Birinchi ishga tushirish bootstrap'i.
 *
 * Python `src/core/bootstrap.py` + `schema.seed_defaults` + `AuthService.ensure_admin`
 * bilan bir xil tamoyil: hisoblar rejasi (NAS-21), standart ombor/bo'lim/kategoriya,
 * va admin foydalanuvchi (tasodifiy parol bilan) avtomatik yaratiladi.
 */
@Singleton
class BootstrapRepository @Inject constructor(
    private val accountDao: AccountDao,
    private val warehouseDao: WarehouseDao,
    private val departmentDao: DepartmentDao,
    private val categoryDao: CategoryDao,
    private val settingsDao: SettingsDao,
    private val userDao: UserDao,
) {
    /**
     * Kerakli boshlang'ich ma'lumotlarni yozadi (idempotent — takror
     * chaqirilsa hech narsani ikkilantirmaydi).
     *
     * @return admin uchun generatsiya qilingan parol (birinchi ishga
     *   tushirishda), yoki `null` (admin allaqachon mavjud bo'lsa).
     */
    suspend fun runIfNeeded(): String? {
        seedChartOfAccounts()
        seedDefaults()
        return ensureAdmin()
    }

    private suspend fun seedChartOfAccounts() {
        if (accountDao.count() > 0) return
        for (seed in CHART_OF_ACCOUNTS) {
            accountDao.insert(
                AccountEntity(
                    code = seed.code,
                    name = seed.name,
                    type = seed.type,
                    isCash = seed.isCash,
                    isBank = seed.isBank,
                ),
            )
        }
    }

    private suspend fun seedDefaults() {
        if (warehouseDao.defaultWarehouseId() == null) {
            warehouseDao.insert(WarehouseEntity(name = "Asosiy ombor"))
        }
        departmentDao.insert(DepartmentEntity(name = "Asosiy bo'lim"))
        categoryDao.insert(CategoryEntity(name = "Umumiy"))

        val now = DateUtils.nowStr()
        listOf(
            "company_name" to "Mening kompaniyam",
            "company_tin" to "",
            "company_address" to "",
            "company_phone" to "",
            "receipt_footer" to "Xaridingiz uchun rahmat!",
        ).forEach { (key, value) ->
            if (settingsDao.getValue(key) == null) {
                settingsDao.upsert(SettingEntity(key, value, now))
            }
        }
    }

    private suspend fun ensureAdmin(): String? {
        if (userDao.count() > 0) return null
        val password = PasswordHasher.generatePassword(12)
        val now = DateUtils.nowStr()
        userDao.insert(
            UserEntity(
                username = "admin",
                passwordHash = PasswordHasher.hash(password),
                fullName = "Tizim administratori",
                role = "administrator",
                isActive = true,
                mustChangePassword = true,
                createdAt = now,
                updatedAt = now,
            ),
        )
        return password
    }
}
