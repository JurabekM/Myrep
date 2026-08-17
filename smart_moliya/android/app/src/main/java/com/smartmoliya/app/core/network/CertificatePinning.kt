package com.smartmoliya.app.core.network

import okhttp3.CertificatePinner

/**
 * Certificate pinning konfiguratsiyasi.
 *
 * Pin faqat ko'rsatilgan hostga qo'llanadi - dev'dagi 10.0.2.2/localhost
 * ulanishlariga ta'sir qilmaydi (OkHttp hostga mos kelmagan pin'larni e'tiborsiz
 * qoldiradi). Host yoki pin bo'sh bo'lsa pinning butunlay o'chiq.
 *
 * Production pin olish (server sertifikatining SPKI SHA-256 xeshi):
 *   openssl s_client -connect api.smartmoliya.uz:443 -servername api.smartmoliya.uz \
 *     | openssl x509 -pubkey -noout | openssl pkey -pubin -outform der \
 *     | openssl dgst -sha256 -binary | openssl enc -base64
 * Natija `sha256/...` ko'rinishida CERT_PIN_SHA256 ga yoziladi.
 */
fun buildCertificatePinner(host: String, sha256Pin: String): CertificatePinner? {
    if (host.isBlank() || sha256Pin.isBlank()) {
        return null
    }
    val normalizedPin = if (sha256Pin.startsWith("sha256/")) sha256Pin else "sha256/$sha256Pin"
    return CertificatePinner.Builder()
        .add(host, normalizedPin)
        .build()
}
