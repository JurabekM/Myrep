package com.uzerp.mobile.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update
import com.uzerp.mobile.data.local.entity.AttendanceEntity
import com.uzerp.mobile.data.local.entity.DepartmentEntity
import com.uzerp.mobile.data.local.entity.EmployeeEntity
import com.uzerp.mobile.data.local.entity.LeaveEntity
import com.uzerp.mobile.data.local.entity.PayrollItemEntity
import com.uzerp.mobile.data.local.entity.PayrollRunEntity
import kotlinx.coroutines.flow.Flow
import java.math.BigDecimal

@Dao
interface DepartmentDao {
    @Insert
    suspend fun insert(department: DepartmentEntity): Long

    @Query(
        "SELECT d.*, (SELECT COUNT(*) FROM employees e WHERE e.departmentId = d.id " +
            "AND e.status = 'active') AS employeeCount FROM departments d " +
            "WHERE d.isActive = 1 ORDER BY d.name",
    )
    fun observeAll(): Flow<List<DepartmentWithCount>>
}

data class DepartmentWithCount(
    val id: Long,
    val name: String,
    val employeeCount: Int,
)

@Dao
interface EmployeeDao {
    @Insert
    suspend fun insert(employee: EmployeeEntity): Long

    @Update
    suspend fun update(employee: EmployeeEntity)

    @Query("UPDATE employees SET code = :code WHERE id = :id")
    suspend fun setCode(id: Long, code: String)

    @Query("SELECT * FROM employees WHERE id = :id")
    suspend fun getById(id: Long): EmployeeEntity?

    @Query(
        "SELECT * FROM employees WHERE (:status IS NULL OR status = :status) " +
            "AND (:search IS NULL OR fullName LIKE '%' || :search || '%') " +
            "ORDER BY fullName LIMIT :limit OFFSET :offset",
    )
    suspend fun search(status: String?, search: String?, limit: Int, offset: Int): List<EmployeeEntity>

    @Query("SELECT * FROM employees WHERE status = 'active' AND salary > 0")
    suspend fun activeWithSalary(): List<EmployeeEntity>

    @Query("SELECT COUNT(*) FROM employees WHERE status = 'active'")
    suspend fun activeCount(): Int
}

@Dao
interface AttendanceDao {
    @Insert
    suspend fun insert(attendance: AttendanceEntity): Long

    @Update
    suspend fun update(attendance: AttendanceEntity)

    @Query("SELECT * FROM attendance WHERE employeeId = :employeeId AND workDate = :workDate")
    suspend fun get(employeeId: Long, workDate: String): AttendanceEntity?

    @Query(
        "SELECT e.id, e.code, e.fullName, " +
            "SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) AS daysPresent, " +
            "SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) AS daysLate, " +
            "SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) AS daysAbsent, " +
            "SUM(CASE WHEN a.status = 'leave' THEN 1 ELSE 0 END) AS daysLeave, " +
            "CAST(COALESCE(SUM(a.hours), 0) AS TEXT) AS totalHours FROM employees e " +
            "LEFT JOIN attendance a ON a.employeeId = e.id AND a.workDate LIKE :monthPrefix " +
            "WHERE e.status = 'active' GROUP BY e.id, e.code, e.fullName ORDER BY e.fullName",
    )
    suspend fun monthSheet(monthPrefix: String): List<AttendanceSheetRow>
}

data class AttendanceSheetRow(
    val id: Long,
    val code: String,
    val fullName: String,
    val daysPresent: Int,
    val daysLate: Int,
    val daysAbsent: Int,
    val daysLeave: Int,
    val totalHours: BigDecimal,
)

@Dao
interface LeaveDao {
    @Insert
    suspend fun insert(leave: LeaveEntity): Long

    @Query("UPDATE leaves SET status = :status, approvedBy = :approvedBy WHERE id = :id")
    suspend fun decide(id: Long, status: String, approvedBy: Long?)

    @Query("SELECT * FROM leaves WHERE id = :id")
    suspend fun getById(id: Long): LeaveEntity?

    @Query(
        "SELECT l.*, e.fullName, e.code FROM leaves l JOIN employees e ON e.id = l.employeeId " +
            "WHERE (:status IS NULL OR l.status = :status) " +
            "ORDER BY l.id DESC LIMIT :limit OFFSET :offset",
    )
    suspend fun search(status: String?, limit: Int, offset: Int): List<LeaveWithEmployee>
}

data class LeaveWithEmployee(
    val id: Long,
    val employeeId: Long,
    val leaveType: String,
    val dateFrom: String,
    val dateTo: String,
    val days: Int,
    val status: String,
    val fullName: String,
    val code: String,
)

@Dao
interface PayrollDao {
    @Insert
    suspend fun insertRun(run: PayrollRunEntity): Long

    @Insert
    suspend fun insertItem(item: PayrollItemEntity): Long

    @Query("UPDATE payroll_runs SET status = :status WHERE id = :id")
    suspend fun setStatus(id: Long, status: String)

    @Query(
        "UPDATE payroll_runs SET totalGross = :gross, totalTax = :tax, totalNet = :net " +
            "WHERE id = :id",
    )
    suspend fun setTotals(id: Long, gross: BigDecimal, tax: BigDecimal, net: BigDecimal)

    @Query("SELECT * FROM payroll_runs WHERE id = :id")
    suspend fun getRunById(id: Long): PayrollRunEntity?

    @Query("SELECT * FROM payroll_runs WHERE period = :period")
    suspend fun getRunByPeriod(period: String): PayrollRunEntity?

    @Query("SELECT * FROM payroll_runs ORDER BY period DESC LIMIT :limit OFFSET :offset")
    suspend fun page(limit: Int, offset: Int): List<PayrollRunEntity>

    @Query(
        "SELECT i.*, e.fullName, e.code, e.position FROM payroll_items i " +
            "JOIN employees e ON e.id = i.employeeId WHERE i.runId = :runId ORDER BY e.fullName",
    )
    suspend fun itemsForRun(runId: Long): List<PayrollItemWithEmployee>
}

data class PayrollItemWithEmployee(
    val id: Long,
    val runId: Long,
    val employeeId: Long,
    val gross: BigDecimal,
    val incomeTax: BigDecimal,
    val pension: BigDecimal,
    val otherDeductions: BigDecimal,
    val net: BigDecimal,
    val fullName: String,
    val code: String,
    val position: String,
)
