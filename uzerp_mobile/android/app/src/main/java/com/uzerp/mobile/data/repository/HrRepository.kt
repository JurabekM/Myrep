package com.uzerp.mobile.data.repository

import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.NotFoundException
import com.uzerp.mobile.core.StateException
import com.uzerp.mobile.core.ValidationException
import com.uzerp.mobile.core.d
import com.uzerp.mobile.data.local.dao.AttendanceDao
import com.uzerp.mobile.data.local.dao.AttendanceSheetRow
import com.uzerp.mobile.data.local.dao.DepartmentDao
import com.uzerp.mobile.data.local.dao.DepartmentWithCount
import com.uzerp.mobile.data.local.dao.EmployeeDao
import com.uzerp.mobile.data.local.dao.LeaveDao
import com.uzerp.mobile.data.local.dao.LeaveWithEmployee
import com.uzerp.mobile.data.local.entity.AttendanceEntity
import com.uzerp.mobile.data.local.entity.DepartmentEntity
import com.uzerp.mobile.data.local.entity.EmployeeEntity
import com.uzerp.mobile.data.local.entity.LeaveEntity
import java.math.BigDecimal
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow

val LEAVE_TYPES = listOf("annual" to "Yillik", "sick" to "Kasallik", "unpaid" to "Ish haqisiz", "maternity" to "Dekret", "other" to "Boshqa")
val ATTENDANCE_STATUSES = listOf("present" to "Keldi", "late" to "Kechikdi", "absent" to "Kelmadi", "leave" to "Ta'til", "holiday" to "Bayram")

/** HR servisi — Python `HrService` bilan bir xil: xodim (avto-kod), davomat, ta'til. */
@Singleton
class HrRepository @Inject constructor(
    private val departmentDao: DepartmentDao,
    private val employeeDao: EmployeeDao,
    private val attendanceDao: AttendanceDao,
    private val leaveDao: LeaveDao,
) {
    fun departments(): Flow<List<DepartmentWithCount>> = departmentDao.observeAll()

    suspend fun createDepartment(name: String): Long {
        if (name.isBlank()) throw ValidationException("Bo'lim nomi bo'sh bo'lishi mumkin emas.")
        return departmentDao.insert(DepartmentEntity(name = name.trim()))
    }

    suspend fun listEmployees(page: Int = 1, search: String? = null, status: String? = "active"): PageResult<EmployeeEntity> {
        val offset = (page - 1) * PAGE_SIZE
        val term = search?.trim()?.ifBlank { null }
        return PageResult(employeeDao.search(status, term, PAGE_SIZE, offset), page, PAGE_SIZE, Int.MAX_VALUE)
    }

    suspend fun getEmployee(id: Long): EmployeeEntity =
        employeeDao.getById(id) ?: throw NotFoundException("Xodim topilmadi (id=$id).")

    suspend fun createEmployee(
        fullName: String,
        departmentId: Long?,
        position: String,
        salary: BigDecimal,
        phone: String = "",
        hireDate: String? = null,
    ): Long {
        val trimmed = fullName.trim()
        if (trimmed.isBlank()) throw ValidationException("Xodim F.I.Sh. bo'sh bo'lishi mumkin emas.")
        if (salary < BigDecimal.ZERO) throw ValidationException("Maosh manfiy bo'lishi mumkin emas.")
        val now = DateUtils.nowStr()
        val id = employeeDao.insert(
            EmployeeEntity(
                fullName = trimmed, departmentId = departmentId, position = position, phone = phone,
                salary = d(salary), hireDate = hireDate ?: DateUtils.todayStr(), status = "active",
                createdAt = now, updatedAt = now,
            ),
        )
        employeeDao.setCode(id, "E%05d".format(id))
        return id
    }

    suspend fun updateEmployee(employee: EmployeeEntity) {
        if (employee.fullName.isBlank()) throw ValidationException("Xodim F.I.Sh. bo'sh bo'lishi mumkin emas.")
        employeeDao.update(employee.copy(updatedAt = DateUtils.nowStr()))
    }

    suspend fun terminate(id: Long) {
        val employee = getEmployee(id)
        employeeDao.update(employee.copy(status = "terminated", updatedAt = DateUtils.nowStr()))
    }

    // ------------------------------------------------------------------ //
    //  Davomat
    // ------------------------------------------------------------------ //

    suspend fun markAttendance(
        employeeId: Long,
        workDate: String? = null,
        status: String = "present",
        checkIn: String = "",
        checkOut: String = "",
        note: String = "",
    ) {
        if (status !in ATTENDANCE_STATUSES.map { it.first }) throw ValidationException("Noma'lum davomat holati: $status")
        getEmployee(employeeId)
        val date = workDate ?: DateUtils.todayStr()
        val hours = calcHours(checkIn, checkOut)
        val existing = attendanceDao.get(employeeId, date)
        if (existing != null) {
            attendanceDao.update(existing.copy(status = status, checkIn = checkIn, checkOut = checkOut, hours = hours, note = note))
        } else {
            attendanceDao.insert(
                AttendanceEntity(employeeId = employeeId, workDate = date, status = status, checkIn = checkIn, checkOut = checkOut, hours = hours, note = note),
            )
        }
    }

    suspend fun attendanceSheet(year: Int, month: Int): List<AttendanceSheetRow> =
        attendanceDao.monthSheet("%04d-%02d-%%".format(year, month))

    // ------------------------------------------------------------------ //
    //  Ta'tillar
    // ------------------------------------------------------------------ //

    suspend fun requestLeave(employeeId: Long, leaveType: String, dateFrom: String, dateTo: String, note: String = ""): Long {
        if (leaveType !in LEAVE_TYPES.map { it.first }) throw ValidationException("Noma'lum ta'til turi: $leaveType")
        getEmployee(employeeId)
        val start = LocalDate.parse(dateFrom)
        val end = LocalDate.parse(dateTo)
        if (end.isBefore(start)) throw ValidationException("Ta'til sanalari noto'g'ri.")
        val days = (end.toEpochDay() - start.toEpochDay()).toInt() + 1
        return leaveDao.insert(
            LeaveEntity(employeeId = employeeId, leaveType = leaveType, dateFrom = dateFrom, dateTo = dateTo, days = days, status = "pending", note = note, createdAt = DateUtils.nowStr()),
        )
    }

    suspend fun decideLeave(leaveId: Long, approve: Boolean, approverId: Long?) {
        val leave = leaveDao.getById(leaveId) ?: throw NotFoundException("Ta'til so'rovi topilmadi (id=$leaveId).")
        if (leave.status != "pending") throw StateException("Bu so'rov allaqachon ko'rib chiqilgan.")
        leaveDao.decide(leaveId, if (approve) "approved" else "rejected", approverId)
    }

    suspend fun listLeaves(page: Int = 1, status: String? = null): PageResult<LeaveWithEmployee> {
        val offset = (page - 1) * PAGE_SIZE
        return PageResult(leaveDao.search(status, PAGE_SIZE, offset), page, PAGE_SIZE, Int.MAX_VALUE)
    }

    private fun calcHours(checkIn: String, checkOut: String): BigDecimal {
        return try {
            val (h1, m1) = checkIn.trim().split(":").map { it.toInt() }
            val (h2, m2) = checkOut.trim().split(":").map { it.toInt() }
            val minutes = (h2 * 60 + m2) - (h1 * 60 + m1)
            if (minutes > 0) d(BigDecimal(minutes).divide(BigDecimal(60), 4, java.math.RoundingMode.HALF_UP)) else BigDecimal.ZERO
        } catch (_: Exception) {
            BigDecimal.ZERO
        }
    }
}
