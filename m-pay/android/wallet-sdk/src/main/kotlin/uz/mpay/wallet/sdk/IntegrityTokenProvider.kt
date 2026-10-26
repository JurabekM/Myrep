package uz.mpay.wallet.sdk

/**
 * Ilova yaxlitligi tokeni manbai (2-faza P2.6, ADR-0021). Fon oqimida chaqiriladi.
 *
 * `requestHash` — joriy PQ Link sessiyasiga bog'langan ([uz.mpay.core.Integrity]); token shu
 * qiymat bilan olinishi shart, aks holda server `INTEGRITY_INVALID` qaytaradi.
 *
 * * Sandbox / emulyator: [MpayWallet.sandboxIntegrityToken] (server mock'i, operator kaliti bilan).
 * * Production: Google Play Integrity API standart so'rovi —
 *   `StandardIntegrityManager.prepareIntegrityToken(cloudProjectNumber)` (ilova ishga tushganda bir
 *   marta), so'ng `provider.request(StandardIntegrityTokenRequest.builder().setRequestHash(requestHash))`.
 *   `TODO(spec):` `com.google.android.play:integrity` bog'liqligi va Google Cloud loyiha raqami bank
 *   bilan kelishilgach (Play Console'da ilova ro'yxatdan o'tgan bo'lishi kerak).
 *
 * `null` — token yo'q (server `[integrity] required = true` bo'lsa `INTEGRITY_REQUIRED`).
 */
fun interface IntegrityTokenProvider {
    fun token(requestHash: String): String?
}
