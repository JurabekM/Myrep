package com.agrovision.app.data.repo

import com.agrovision.app.core.RateLimiter
import com.agrovision.app.core.Security
import com.agrovision.app.core.Session
import com.agrovision.app.core.SessionUser
import com.agrovision.app.data.local.AuditDao
import com.agrovision.app.data.local.AuditLogEntity
import com.agrovision.app.data.local.UserDao
import com.agrovision.app.data.local.UserEntity
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

sealed class LoginResult {
    data class Success(val user: SessionUser) : LoginResult()
    data object InvalidCredentials : LoginResult()
    data object Disabled : LoginResult()
    data class Locked(val minutes: Int) : LoginResult()
}

@Singleton
class AuthRepository @Inject constructor(
    private val userDao: UserDao,
    private val auditDao: AuditDao,
) {
    private val limiter = RateLimiter()

    suspend fun login(username: String, password: String): LoginResult {
        val key = username.trim().lowercase()
        if (limiter.isLocked(key)) return LoginResult.Locked(limiter.lockRemainingMinutes(key))

        val user = userDao.find(key)
        if (user == null || !Security.verifyPassword(password, user.passwordHash)) {
            limiter.registerFailure(key)
            audit("login_failed", key)
            return LoginResult.InvalidCredentials
        }
        if (!user.active) return LoginResult.Disabled

        limiter.registerSuccess(key)
        val session = SessionUser(user.id, user.username, user.fullName.ifBlank { user.username }, user.role)
        Session.login(session)
        audit("login", key)
        return LoginResult.Success(session)
    }

    suspend fun logout() {
        Session.current?.let { audit("logout", it.username) }
        Session.logout()
    }

    suspend fun createUser(username: String, fullName: String, password: String, role: String): String? {
        val key = username.trim().lowercase()
        if (key.isBlank() || password.isBlank()) return "Login va parol majburiy."
        if (password.length < 6) return "Parol kamida 6 belgidan bo'lishi kerak."
        if (userDao.find(key) != null) return "Bunday login allaqachon mavjud."
        userDao.insert(
            UserEntity(
                username = key,
                fullName = fullName.trim().ifBlank { key },
                passwordHash = Security.hashPassword(password),
                role = role,
            ),
        )
        audit("user_created", actor(), key)
        return null
    }

    suspend fun toggleActive(username: String): String? {
        val user = userDao.find(username.trim().lowercase()) ?: return "Foydalanuvchi topilmadi."
        if (user.username == Session.current?.username) return "O'zingizni bloklay olmaysiz."
        userDao.update(user.copy(active = !user.active))
        audit("user_toggled", actor(), "${user.username}: ${if (!user.active) "faollashtirildi" else "bloklandi"}")
        return null
    }

    suspend fun resetPassword(username: String, newPassword: String): String? {
        if (newPassword.length < 6) return "Parol kamida 6 belgidan bo'lishi kerak."
        val user = userDao.find(username.trim().lowercase()) ?: return "Foydalanuvchi topilmadi."
        userDao.update(user.copy(passwordHash = Security.hashPassword(newPassword)))
        audit("password_reset", actor(), user.username)
        return null
    }

    fun observeUsers(): Flow<List<UserEntity>> = userDao.observeAll()
    fun observeAudit(limit: Int = 200): Flow<List<AuditLogEntity>> = auditDao.observeRecent(limit)

    suspend fun audit(action: String, username: String = actor(), details: String = "") {
        runCatching {
            auditDao.insert(AuditLogEntity(username = username, action = action, details = details.take(500)))
        }
    }

    private fun actor(): String = Session.current?.username ?: "system"
}
