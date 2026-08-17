package com.agrovision.mobile.data.repository

import com.agrovision.mobile.core.Security
import com.agrovision.mobile.core.Session
import com.agrovision.mobile.core.SessionUser
import com.agrovision.mobile.data.local.AuditDao
import com.agrovision.mobile.data.local.AuditLogEntity
import com.agrovision.mobile.data.local.UserDao
import com.agrovision.mobile.data.local.UserEntity
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

sealed class LoginResult {
    data class Success(val user: SessionUser) : LoginResult()
    data object InvalidCredentials : LoginResult()
    data object AccountDisabled : LoginResult()
}

@Singleton
class AuthRepository @Inject constructor(
    private val userDao: UserDao,
    private val auditDao: AuditDao,
) {
    suspend fun login(username: String, password: String): LoginResult {
        val normalized = username.trim().lowercase()
        val user = userDao.findAny(normalized)
            ?: return LoginResult.InvalidCredentials.also { audit("login_failed", normalized) }
        if (!user.active) return LoginResult.AccountDisabled
        if (!Security.verifyPassword(password, user.passwordHash)) {
            audit("login_failed", normalized)
            return LoginResult.InvalidCredentials
        }
        val session = SessionUser(user.id, user.username, user.fullName, user.role)
        Session.login(session)
        audit("login", normalized)
        return LoginResult.Success(session)
    }

    suspend fun logout() {
        Session.current?.let { audit("logout", it.username) }
        Session.logout()
    }

    suspend fun createUser(username: String, fullName: String, password: String, role: String): Boolean {
        val normalized = username.trim().lowercase()
        if (userDao.findAny(normalized) != null) return false
        userDao.insert(
            UserEntity(
                username = normalized, fullName = fullName.ifBlank { normalized },
                passwordHash = Security.hashPassword(password), role = role,
            ),
        )
        audit("user_created", Session.current?.username ?: "system", normalized)
        return true
    }

    suspend fun toggleActive(username: String): Boolean {
        val user = userDao.findAny(username) ?: return false
        if (user.username == Session.current?.username) return false
        userDao.update(user.copy(active = !user.active))
        audit("user_toggled", Session.current?.username ?: "system", username)
        return true
    }

    suspend fun resetPassword(username: String, newPassword: String): Boolean {
        val user = userDao.findAny(username) ?: return false
        userDao.update(user.copy(passwordHash = Security.hashPassword(newPassword)))
        audit("password_reset", Session.current?.username ?: "system", username)
        return true
    }

    fun observeUsers(): Flow<List<UserEntity>> = userDao.observeAll()
    fun observeAudit(limit: Int = 200): Flow<List<AuditLogEntity>> = auditDao.observeRecent(limit)

    suspend fun audit(action: String, username: String, details: String = "") {
        auditDao.insert(AuditLogEntity(username = username, action = action, details = details))
    }
}
