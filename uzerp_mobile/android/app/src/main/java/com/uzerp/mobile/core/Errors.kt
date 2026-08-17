package com.uzerp.mobile.core

/** Barcha biznes xatolarning asosi (xabari foydalanuvchiga ko'rsatiladi). */
sealed class UzErpException(message: String) : Exception(message)

class ValidationException(message: String) : UzErpException(message)
class NotFoundException(message: String) : UzErpException(message)
class InsufficientStockException(message: String) : UzErpException(message)
class StateException(message: String) : UzErpException(message)
class AuthException(message: String) : UzErpException(message)
class PermissionDeniedException(message: String) : UzErpException(message)

/** Servis natijasi: muvaffaqiyat yoki xato matni (UI'da ko'rsatish uchun). */
sealed class AppResult<out T> {
    data class Success<T>(val data: T) : AppResult<T>()
    data class Error(val message: String) : AppResult<Nothing>()
}

/** [block] ni bajaradi va [UzErpException] larni [AppResult.Error] ga aylantiradi. */
inline fun <T> runCatchingApp(block: () -> T): AppResult<T> = try {
    AppResult.Success(block())
} catch (e: UzErpException) {
    AppResult.Error(e.message ?: "Noma'lum xato")
} catch (e: Exception) {
    AppResult.Error("Kutilmagan xato: ${e.message}")
}
