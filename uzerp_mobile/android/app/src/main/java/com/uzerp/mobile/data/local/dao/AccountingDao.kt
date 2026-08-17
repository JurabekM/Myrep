package com.uzerp.mobile.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.uzerp.mobile.data.local.entity.AccountEntity
import com.uzerp.mobile.data.local.entity.AssetEntity
import com.uzerp.mobile.data.local.entity.JournalEntryEntity
import com.uzerp.mobile.data.local.entity.JournalLineEntity
import com.uzerp.mobile.data.local.entity.PaymentEntity
import kotlinx.coroutines.flow.Flow
import java.math.BigDecimal

@Dao
interface AccountDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(account: AccountEntity): Long

    @Query("SELECT * FROM accounts WHERE code = :code")
    suspend fun getByCode(code: String): AccountEntity?

    @Query("SELECT * FROM accounts WHERE id = :id")
    suspend fun getById(id: Long): AccountEntity?

    @Query("SELECT * FROM accounts WHERE isActive = 1 ORDER BY code")
    fun observeAll(): Flow<List<AccountEntity>>

    @Query("SELECT COUNT(*) FROM accounts")
    suspend fun count(): Int

    // MUHIM: barcha SUM() natijalari CAST(... AS TEXT) bilan o'raladi.
    // Sabab: pul TEXT ustunlarda saqlanadi, SUM() esa REAL qaytaradi va
    // Android CursorWindow REAL ni String ga %g (6 xonali aniqlik) bilan
    // aylantiradi — 7+ xonali summalarda aniqlik yo'qoladi (masalan
    // 1339285.71 -> 1339290). SQLite ning o'z REAL->TEXT cast'i esa 15
    // xonali aniq matn beradi.
    @Query(
        "SELECT CAST(COALESCE(SUM(debit), 0) AS TEXT) FROM journal_lines l " +
            "JOIN journal_entries e ON e.id = l.entryId " +
            "WHERE l.accountId = :accountId AND e.isPosted = 1 " +
            "AND (:dateTo IS NULL OR e.entryDate <= :dateTo)",
    )
    suspend fun sumDebit(accountId: Long, dateTo: String?): BigDecimal

    @Query(
        "SELECT CAST(COALESCE(SUM(credit), 0) AS TEXT) FROM journal_lines l " +
            "JOIN journal_entries e ON e.id = l.entryId " +
            "WHERE l.accountId = :accountId AND e.isPosted = 1 " +
            "AND (:dateTo IS NULL OR e.entryDate <= :dateTo)",
    )
    suspend fun sumCredit(accountId: Long, dateTo: String?): BigDecimal
}

@Dao
interface JournalDao {
    @Insert
    suspend fun insertEntry(entry: JournalEntryEntity): Long

    @Insert
    suspend fun insertLine(line: JournalLineEntity): Long

    @Query("SELECT * FROM journal_entries WHERE id = :id")
    suspend fun getEntryById(id: Long): JournalEntryEntity?

    @Query(
        "SELECT l.*, a.code AS accountCode, a.name AS accountName FROM journal_lines l " +
            "JOIN accounts a ON a.id = l.accountId WHERE l.entryId = :entryId ORDER BY l.id",
    )
    suspend fun linesForEntry(entryId: Long): List<JournalLineWithAccount>

    @Query(
        "SELECT e.*, CAST((SELECT SUM(debit) FROM journal_lines l WHERE l.entryId = e.id) " +
            "AS TEXT) AS amount FROM journal_entries e " +
            "WHERE (:dateFrom IS NULL OR e.entryDate >= :dateFrom) " +
            "AND (:dateTo IS NULL OR e.entryDate <= :dateTo) " +
            "ORDER BY e.id DESC LIMIT :limit OFFSET :offset",
    )
    suspend fun search(
        dateFrom: String?,
        dateTo: String?,
        limit: Int,
        offset: Int,
    ): List<JournalEntryWithAmount>

    @Query(
        "SELECT a.code, a.name, a.type, " +
            "CAST(COALESCE((SELECT SUM(l.debit) FROM journal_lines l " +
            "  JOIN journal_entries e ON e.id = l.entryId " +
            "  WHERE l.accountId = a.id AND e.isPosted = 1 " +
            "  AND (:dateTo IS NULL OR e.entryDate <= :dateTo)), 0) AS TEXT) AS totalDebit, " +
            "CAST(COALESCE((SELECT SUM(l.credit) FROM journal_lines l " +
            "  JOIN journal_entries e ON e.id = l.entryId " +
            "  WHERE l.accountId = a.id AND e.isPosted = 1 " +
            "  AND (:dateTo IS NULL OR e.entryDate <= :dateTo)), 0) AS TEXT) AS totalCredit " +
            "FROM accounts a WHERE a.isActive = 1 ORDER BY a.code",
    )
    suspend fun trialBalanceRaw(dateTo: String?): List<TrialBalanceRow>

    /** Foyda-zarar uchun: davr ichida daromad/xarajat hisoblari bo'yicha sof kredit. */
    @Query(
        "SELECT a.code, a.name, a.type, " +
            "CAST(COALESCE(SUM(l.credit - l.debit), 0) AS TEXT) AS netCredit " +
            "FROM accounts a JOIN journal_lines l ON l.accountId = a.id " +
            "JOIN journal_entries e ON e.id = l.entryId " +
            "WHERE a.type IN ('income', 'expense') AND e.isPosted = 1 " +
            "AND e.entryDate >= :dateFrom AND e.entryDate <= :dateTo " +
            "GROUP BY a.id, a.code, a.name, a.type ORDER BY a.code",
    )
    suspend fun profitLossRaw(dateFrom: String, dateTo: String): List<ProfitLossRow>
}

data class ProfitLossRow(
    val code: String,
    val name: String,
    val type: String,
    val netCredit: BigDecimal,
)

data class JournalLineWithAccount(
    val id: Long,
    val entryId: Long,
    val accountId: Long,
    val debit: BigDecimal,
    val credit: BigDecimal,
    val accountCode: String,
    val accountName: String,
)

data class JournalEntryWithAmount(
    val id: Long,
    val number: String,
    val entryDate: String,
    val memo: String,
    val refType: String,
    val amount: BigDecimal?,
)

data class TrialBalanceRow(
    val code: String,
    val name: String,
    val type: String,
    val totalDebit: BigDecimal,
    val totalCredit: BigDecimal,
)

@Dao
interface PaymentDao {
    @Insert
    suspend fun insert(payment: PaymentEntity): Long

    @Query(
        "SELECT * FROM payments WHERE " +
            "(:method IS NULL OR method = :method) " +
            "AND (:paymentType IS NULL OR paymentType = :paymentType) " +
            "ORDER BY id DESC LIMIT :limit OFFSET :offset",
    )
    suspend fun search(
        method: String?,
        paymentType: String?,
        limit: Int,
        offset: Int,
    ): List<PaymentEntity>

    @Query(
        "SELECT CAST(COALESCE(SUM(CASE WHEN paymentType = 'in' THEN amount ELSE -amount END), 0) AS TEXT) " +
            "FROM payments WHERE method = 'cash'",
    )
    suspend fun cashNet(): BigDecimal

    @Query(
        "SELECT CAST(COALESCE(SUM(CASE WHEN paymentType = 'in' THEN amount ELSE -amount END), 0) AS TEXT) " +
            "FROM payments WHERE method <> 'cash'",
    )
    suspend fun bankNet(): BigDecimal
}

@Dao
interface AssetDao {
    @Insert
    suspend fun insert(asset: AssetEntity): Long

    @Query("UPDATE assets SET accumulatedDepreciation = :value WHERE id = :id")
    suspend fun setAccumulatedDepreciation(id: Long, value: BigDecimal)

    @Query("SELECT * FROM assets WHERE status = 'active'")
    suspend fun activeAssets(): List<AssetEntity>

    @Query("SELECT * FROM assets ORDER BY id DESC LIMIT :limit OFFSET :offset")
    suspend fun page(limit: Int, offset: Int): List<AssetEntity>

    @Query("SELECT EXISTS(SELECT 1 FROM journal_entries WHERE refType = 'depreciation' AND memo LIKE '%' || :period || '%')")
    suspend fun depreciationExistsForPeriod(period: String): Boolean
}
