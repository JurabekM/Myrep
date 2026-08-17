package uz.buildcontrol.mobile.data.repo

import androidx.room.withTransaction
import at.favre.lib.crypto.bcrypt.BCrypt
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import uz.buildcontrol.mobile.data.db.AuditLogRow
import uz.buildcontrol.mobile.data.db.BcDatabase
import uz.buildcontrol.mobile.data.db.RoleRow
import uz.buildcontrol.mobile.data.db.UserRow
import uz.buildcontrol.mobile.data.db.now
import uz.buildcontrol.mobile.data.sync.SyncRecorder
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.RoleCode

class AuthException(val key: String) : Exception(key)

/** Sign-in, role bootstrap and the audit trail. */
class AuthRepository(
    private val db: BcDatabase,
    private val recorder: SyncRecorder,
) {
    private val dao = db.dao()

    /** Built-in roles, created when the phone starts with an empty database. */
    private val defaultRoles = listOf(
        Triple(RoleCode.ADMIN, "Administrator", "Administrator"),
        Triple(RoleCode.MANAGER, "Loyiha rahbari", "Project manager"),
        Triple(RoleCode.ESTIMATOR, "Smetachi", "Estimator"),
        Triple(RoleCode.STOREKEEPER, "Omborchi", "Storekeeper"),
        Triple(RoleCode.VIEWER, "Kuzatuvchi", "Viewer"),
    )

    suspend fun ensureRoles() = withContext(Dispatchers.IO) {
        db.withTransaction {
            for ((code, uz, en) in defaultRoles) {
                if (dao.roleByCode(code) == null) {
                    val row = RoleRow(code = code, nameUz = uz, nameEn = en)
                    val id = dao.upsert(row)
                    recorder.upsert("Role", dao.role(id)?.uid ?: row.uid)
                }
            }
        }
    }

    suspend fun hasUsers(): Boolean = withContext(Dispatchers.IO) { dao.userCount() > 0 }

    suspend fun login(username: String, password: String): CurrentUser =
        withContext(Dispatchers.IO) {
            val user = dao.userByUsername(username.trim().lowercase())
                ?: throw AuthException("login_failed")
            if (!verify(password, user.passwordHash)) throw AuthException("login_failed")
            if (!user.isActive || user.isArchived) throw AuthException("user_inactive")
            val role = user.roleId?.let { dao.role(it) }
            db.withTransaction {
                dao.upsert(user.copy(lastLogin = now(), syncTs = now(), updatedAt = now()))
                recorder.upsert("User", user.uid)
            }
            CurrentUser(
                id = user.id,
                uid = user.uid,
                username = user.username,
                fullName = user.fullName,
                roleCode = role?.code ?: RoleCode.VIEWER,
            )
        }

    suspend fun createUser(
        username: String,
        password: String,
        fullName: String,
        roleCode: String,
    ): CurrentUser = withContext(Dispatchers.IO) {
        val clean = username.trim().lowercase()
        if (clean.isEmpty()) throw AuthException("required_field")
        if (password.length < 6) throw AuthException("password_too_short")
        ensureRoles()
        if (dao.userByUsername(clean) != null) throw AuthException("username_taken")
        val role = dao.roleByCode(roleCode) ?: dao.roleByCode(RoleCode.VIEWER)
        val row = UserRow(
            username = clean,
            fullName = fullName.trim(),
            passwordHash = hash(password),
            roleId = role?.id,
        )
        val id = db.withTransaction {
            val newId = dao.upsert(row)
            recorder.upsert("User", row.uid)
            newId
        }
        CurrentUser(id, row.uid, clean, row.fullName, role?.code ?: RoleCode.VIEWER)
    }

    suspend fun audit(
        user: CurrentUser?,
        action: String,
        entityType: String,
        entityId: Long?,
        projectId: Long?,
        description: String,
        oldValue: String = "",
        newValue: String = "",
    ) = withContext(Dispatchers.IO) {
        val row = AuditLogRow(
            ts = now(),
            userId = user?.id,
            username = user?.username ?: "mobile",
            action = action,
            entityType = entityType,
            entityId = entityId,
            projectId = projectId,
            description = description,
            oldValue = oldValue,
            newValue = newValue,
        )
        db.withTransaction {
            dao.insert(row)
            recorder.upsert("AuditLog", row.uid)
        }
    }

    companion object {
        fun hash(password: String): String =
            BCrypt.withDefaults().hashToString(10, password.toCharArray())

        /** Verifies a hash produced by the desktop application (`bcrypt`). */
        fun verify(password: String, hash: String): Boolean {
            if (password.isEmpty() || hash.isEmpty()) return false
            return runCatching {
                BCrypt.verifyer().verify(password.toCharArray(), hash).verified
            }.getOrDefault(false)
        }
    }
}
