package com.uzerp.mobile.data.repository

import com.uzerp.mobile.core.AuthException
import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.PasswordHasher
import com.uzerp.mobile.data.local.dao.AuditDao
import com.uzerp.mobile.data.local.dao.UserDao
import com.uzerp.mobile.data.local.entity.AuditLogEntity
import com.uzerp.mobile.data.local.entity.UserEntity
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

private const val MAX_LOGIN_ATTEMPTS = 5
private const val LOCKOUT_MINUTES = 15L
private val TS_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")

/**
 * Autentifikatsiya servisi — Python `AuthService` bilan bir xil tamoyil:
 * hisob blokirovkasi (5 xato urinishdan keyin 15 daqiqa), PBKDF2 xesh
 * tekshiruvi. Mobil qurilma bitta foydalanuvchi sessiyasini xotirada
 * saqlaydi (server sessiyalar jadvali kerak emas).
 */
@Singleton
class AuthRepository @Inject constructor(
    private val userDao: UserDao,
    private val auditDao: AuditDao,
) {
    private val _currentUser = MutableStateFlow<UserEntity?>(null)
    val currentUser: StateFlow<UserEntity?> = _currentUser.asStateFlow()

    suspend fun login(username: String, password: String): UserEntity {
        val user = userDao.getByUsername(username.trim())
        if (user == null || !user.isActive) {
            audit("login.failed", null, "username=$username")
            throw AuthException("Login yoki parol noto'g'ri.")
        }

        user.lockedUntil?.let { locked ->
            runCatching { LocalDateTime.parse(locked, TS_FMT) }.getOrNull()?.let {
                if (it.isAfter(LocalDateTime.now())) {
                    audit("login.locked", user)
                    throw AuthException(
                        "Hisob vaqtincha bloklangan. Birozdan so'ng urinib ko'ring.",
                    )
                }
            }
        }

        if (!PasswordHasher.verify(password, user.passwordHash)) {
            registerFailedAttempt(user)
            throw AuthException("Login yoki parol noto'g'ri.")
        }

        userDao.update(
            user.copy(failedAttempts = 0, lockedUntil = null, lastLogin = DateUtils.nowStr()),
        )
        audit("login.success", user)
        val fresh = userDao.getById(user.id)!!
        _currentUser.value = fresh
        return fresh
    }

    suspend fun logout() {
        val user = _currentUser.value
        _currentUser.value = null
        if (user != null) audit("logout", user)
    }

    suspend fun changePassword(userId: Long, oldPassword: String, newPassword: String) {
        val user = userDao.getById(userId) ?: throw AuthException("Foydalanuvchi topilmadi.")
        if (!PasswordHasher.verify(oldPassword, user.passwordHash)) {
            throw AuthException("Joriy parol noto'g'ri.")
        }
        PasswordHasher.checkPolicy(newPassword)?.let { throw AuthException(it) }
        userDao.update(
            user.copy(
                passwordHash = PasswordHasher.hash(newPassword),
                mustChangePassword = false,
                updatedAt = DateUtils.nowStr(),
            ),
        )
        if (_currentUser.value?.id == userId) {
            _currentUser.value = userDao.getById(userId)
        }
        audit("user.password_changed", user, category = "security")
    }

    suspend fun createUser(
        actor: UserEntity?,
        username: String,
        password: String,
        fullName: String,
        role: String,
    ): Long {
        val name = username.trim()
        if (name.length < 3) throw AuthException("Login kamida 3 ta belgidan iborat bo'lishi kerak.")
        PasswordHasher.checkPolicy(password)?.let { throw AuthException(it) }
        if (userDao.getByUsername(name) != null) {
            throw AuthException("Bunday login allaqachon mavjud.")
        }
        val now = DateUtils.nowStr()
        val id = userDao.insert(
            UserEntity(
                username = name,
                passwordHash = PasswordHasher.hash(password),
                fullName = fullName,
                role = role,
                isActive = true,
                createdAt = now,
                updatedAt = now,
            ),
        )
        audit("user.create", actor, entityId = id.toString(), details = "$name ($role)")
        return id
    }

    private suspend fun registerFailedAttempt(user: UserEntity) {
        val attempts = user.failedAttempts + 1
        val lockedUntil = if (attempts >= MAX_LOGIN_ATTEMPTS) {
            LocalDateTime.now().plusMinutes(LOCKOUT_MINUTES).format(TS_FMT)
        } else {
            null
        }
        userDao.update(user.copy(failedAttempts = attempts, lockedUntil = lockedUntil))
        audit(
            if (lockedUntil != null) "account.locked" else "login.failed",
            user,
            details = "urinish #$attempts",
        )
    }

    private suspend fun audit(
        action: String,
        user: UserEntity?,
        details: String = "",
        entityId: String = "",
        category: String = "security",
    ) {
        auditDao.insert(
            AuditLogEntity(
                userId = user?.id,
                username = user?.username ?: "system",
                action = action,
                entity = "user",
                entityId = entityId.ifBlank { user?.id?.toString() ?: "" },
                details = details,
                category = category,
                createdAt = DateUtils.nowStr(),
            ),
        )
    }
}
