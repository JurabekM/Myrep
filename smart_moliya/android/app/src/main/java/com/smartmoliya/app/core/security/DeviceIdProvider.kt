package com.smartmoliya.app.core.security

import android.content.Context
import android.provider.Settings
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Qurilmaga xos, o'chirilmaydigan identifikator - refresh token'ni bitta qurilmaga
 * bog'lash (device binding) uchun ishlatiladi.
 */
@Singleton
class DeviceIdProvider @Inject constructor(@ApplicationContext context: Context) {

    val deviceId: String =
        Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID) ?: "unknown-device"
}
