#include "aesgcm.h"

#include <string.h>

#include "mbedtls/gcm.h"

#if defined(ESP_PLATFORM)
#  if defined(__has_include) && __has_include("esp_random.h")
#    include "esp_random.h"
#  else
#    include "esp_system.h" /* eski ESP-IDF: esp_fill_random shu yerda */
#  endif

void aesgcm_random(uint8_t *buf, size_t len)
{
    esp_fill_random(buf, len);
}
#endif

int aesgcm_encrypt_with_nonce(const uint8_t key[AESGCM_KEY_LEN],
                              const uint8_t nonce[AESGCM_NONCE_LEN],
                              const uint8_t *pt, size_t pt_len,
                              const uint8_t *aad, size_t aad_len,
                              uint8_t *out, size_t out_cap, size_t *out_len)
{
    if (key == NULL || nonce == NULL || out == NULL || out_len == NULL ||
        (pt == NULL && pt_len != 0) || (aad == NULL && aad_len != 0)) {
        return AESGCM_ERR_ARG;
    }
    if (pt_len > SIZE_MAX - AESGCM_OVERHEAD || out_cap < pt_len + AESGCM_OVERHEAD) {
        return AESGCM_ERR_BUF;
    }

    uint8_t *ct = out + AESGCM_NONCE_LEN;
    uint8_t *tag = ct + pt_len;

    /* out va nonce bir joyni ko'rsatsa ham to'g'ri ishlashi uchun memmove. */
    memmove(out, nonce, AESGCM_NONCE_LEN);

    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);
    int rc = mbedtls_gcm_setkey(&ctx, MBEDTLS_CIPHER_ID_AES, key, AESGCM_KEY_LEN * 8);
    if (rc == 0) {
        rc = mbedtls_gcm_crypt_and_tag(&ctx, MBEDTLS_GCM_ENCRYPT, pt_len,
                                       out, AESGCM_NONCE_LEN,
                                       aad, aad_len,
                                       pt, ct,
                                       AESGCM_TAG_LEN, tag);
    }
    mbedtls_gcm_free(&ctx); /* kalit jadvalini xotiradan o'chiradi */

    if (rc != 0) {
        memset(out, 0, pt_len + AESGCM_OVERHEAD);
        return AESGCM_ERR_CRYPTO;
    }
    *out_len = pt_len + AESGCM_OVERHEAD;
    return AESGCM_OK;
}

int aesgcm_encrypt(const uint8_t key[AESGCM_KEY_LEN],
                   const uint8_t *pt, size_t pt_len,
                   const uint8_t *aad, size_t aad_len,
                   uint8_t *out, size_t out_cap, size_t *out_len)
{
    uint8_t nonce[AESGCM_NONCE_LEN];
    aesgcm_random(nonce, sizeof nonce);
    return aesgcm_encrypt_with_nonce(key, nonce, pt, pt_len, aad, aad_len,
                                     out, out_cap, out_len);
}

int aesgcm_decrypt(const uint8_t key[AESGCM_KEY_LEN],
                   const uint8_t *in, size_t in_len,
                   const uint8_t *aad, size_t aad_len,
                   uint8_t *out, size_t out_cap, size_t *out_len)
{
    if (key == NULL || in == NULL || out_len == NULL ||
        (aad == NULL && aad_len != 0) || in_len < AESGCM_OVERHEAD) {
        return AESGCM_ERR_ARG;
    }
    const size_t ct_len = in_len - AESGCM_OVERHEAD;
    if (out == NULL && ct_len != 0) {
        return AESGCM_ERR_ARG;
    }
    if (out_cap < ct_len) {
        return AESGCM_ERR_BUF;
    }

    const uint8_t *nonce = in;
    const uint8_t *ct = in + AESGCM_NONCE_LEN;
    const uint8_t *tag = ct + ct_len;

    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);
    int rc = mbedtls_gcm_setkey(&ctx, MBEDTLS_CIPHER_ID_AES, key, AESGCM_KEY_LEN * 8);
    if (rc == 0) {
        /* Tegni doimiy vaqtda solishtiradi; mos kelmasa out ni nollaydi. */
        rc = mbedtls_gcm_auth_decrypt(&ctx, ct_len,
                                      nonce, AESGCM_NONCE_LEN,
                                      aad, aad_len,
                                      tag, AESGCM_TAG_LEN,
                                      ct, out);
    }
    mbedtls_gcm_free(&ctx);

    if (rc != 0) {
        if (ct_len != 0) {
            memset(out, 0, ct_len);
        }
        return rc == MBEDTLS_ERR_GCM_AUTH_FAILED ? AESGCM_ERR_AUTH : AESGCM_ERR_CRYPTO;
    }
    *out_len = ct_len;
    return AESGCM_OK;
}
