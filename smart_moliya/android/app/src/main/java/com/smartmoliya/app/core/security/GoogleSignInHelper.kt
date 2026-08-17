package com.smartmoliya.app.core.security

import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.smartmoliya.app.BuildConfig

/**
 * Credential Manager orqali Google ID token olish.
 *
 * Ishlashi uchun `app/build.gradle.kts` dagi GOOGLE_SERVER_CLIENT_ID to'ldirilgan
 * bo'lishi kerak (Google Cloud Console -> Credentials -> Web application client ID).
 * Bo'sh bo'lsa [isConfigured] false qaytaradi va UI'da tugma ko'rsatilmaydi.
 */
class GoogleSignInHelper(private val context: Context) {

    fun isConfigured(): Boolean = BuildConfig.GOOGLE_SERVER_CLIENT_ID.isNotBlank()

    /** Google hisob tanlash oynasini ochib, ID tokenni qaytaradi. Bekor qilinsa exception. */
    suspend fun getIdToken(): String {
        val googleIdOption = GetGoogleIdOption.Builder()
            .setServerClientId(BuildConfig.GOOGLE_SERVER_CLIENT_ID)
            .setFilterByAuthorizedAccounts(false)
            .build()

        val request = GetCredentialRequest.Builder()
            .addCredentialOption(googleIdOption)
            .build()

        val result = CredentialManager.create(context).getCredential(context, request)
        val credential = GoogleIdTokenCredential.createFrom(result.credential.data)
        return credential.idToken
    }
}
