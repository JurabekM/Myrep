package com.smartmoliya.app.core.database

import androidx.room.Database
import androidx.room.RoomDatabase
import com.smartmoliya.app.core.database.dao.BudgetDao
import com.smartmoliya.app.core.database.dao.CategoryDao
import com.smartmoliya.app.core.database.dao.DebtDao
import com.smartmoliya.app.core.database.dao.GoalDao
import com.smartmoliya.app.core.database.dao.InvestmentDao
import com.smartmoliya.app.core.database.dao.LoanDao
import com.smartmoliya.app.core.database.dao.LocalTaskDao
import com.smartmoliya.app.core.database.dao.TransactionDao
import com.smartmoliya.app.core.database.dao.WalletDao
import com.smartmoliya.app.core.database.entity.BudgetEntity
import com.smartmoliya.app.core.database.entity.CategoryEntity
import com.smartmoliya.app.core.database.entity.DebtEntity
import com.smartmoliya.app.core.database.entity.GoalEntity
import com.smartmoliya.app.core.database.entity.InvestmentEntity
import com.smartmoliya.app.core.database.entity.LoanEntity
import com.smartmoliya.app.core.database.entity.LocalTaskEntity
import com.smartmoliya.app.core.database.entity.TransactionEntity
import com.smartmoliya.app.core.database.entity.WalletEntity

/**
 * Offline-first mahalliy baza - SQLCipher bilan AES-256 shifrlangan
 * (`DatabaseModule`da `SupportOpenHelperFactory` orqali ulanadi, kalit
 * `DatabaseKeyProvider`dan - Android Keystore himoyasida).
 *
 * Eslatma: ilova ilgari shifrlanmagan baza bilan o'rnatilgan bo'lsa, eski fayl
 * ochilmaydi - dev bosqichida ilovani o'chirib qayta o'rnatish kifoya.
 */
@Database(
    entities = [
        WalletEntity::class,
        CategoryEntity::class,
        TransactionEntity::class,
        BudgetEntity::class,
        GoalEntity::class,
        LoanEntity::class,
        DebtEntity::class,
        InvestmentEntity::class,
        LocalTaskEntity::class
    ],
    version = 2,
    exportSchema = true
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun walletDao(): WalletDao
    abstract fun categoryDao(): CategoryDao
    abstract fun transactionDao(): TransactionDao
    abstract fun budgetDao(): BudgetDao
    abstract fun goalDao(): GoalDao
    abstract fun loanDao(): LoanDao
    abstract fun debtDao(): DebtDao
    abstract fun investmentDao(): InvestmentDao
    abstract fun localTaskDao(): LocalTaskDao

    companion object {
        const val DATABASE_NAME = "smart_moliya.db"
    }
}
