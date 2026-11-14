/*
 * aesgcm — ESP32 uchun AES-256-GCM (autentifikatsiyali shifrlash).
 *
 * mbedTLS ustiga yupqa qatlam. mbedTLS ESP32 da apparat AES tezlatgichini
 * o'zi ishlatadi. Arduino-ESP32 va ESP-IDF da bir xil ishlaydi.
 *
 * Paket formati (bitta uzluksiz bufer):
 *
 *     nonce (12 bayt) | shifrmatn (ochiq matn bilan teng uzunlik) | teg (16 bayt)
 *
 * Paket ikkilik ma'lumot: ichida 0x00 bo'lishi mumkin. Uni C-satr deb
 * ishlatmang (strlen, %s) — uzunlikni doim alohida olib yuring.
 */
#ifndef AESGCM_H
#define AESGCM_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define AESGCM_KEY_LEN   32u
#define AESGCM_NONCE_LEN 12u
#define AESGCM_TAG_LEN   16u
/* Paket ochiq matndan shuncha bayt uzun bo'ladi. */
#define AESGCM_OVERHEAD  (AESGCM_NONCE_LEN + AESGCM_TAG_LEN)

#define AESGCM_OK          0
#define AESGCM_ERR_ARG    -1 /* noto'g'ri argument (NULL, juda qisqa paket) */
#define AESGCM_ERR_BUF    -2 /* chiqish buferi kichik */
#define AESGCM_ERR_AUTH   -3 /* teg mos kelmadi: kalit/AAD xato yoki paket o'zgartirilgan */
#define AESGCM_ERR_CRYPTO -4 /* mbedTLS ichki xatosi */

/*
 * Shifrlash. Har chaqiruvda yangi tasodifiy nonce olinadi.
 *
 *   key      — 32 baytli kalit
 *   pt       — ochiq matn (pt_len == 0 bo'lsa NULL bo'lishi mumkin)
 *   aad      — shifrlanmaydigan, lekin teg bilan himoyalanadigan sarlavha
 *              (masalan, qurilma ID si); kerak bo'lmasa NULL, 0
 *   out      — paket yoziladigan bufer, kamida pt_len + AESGCM_OVERHEAD bayt
 *   out_len  — yozilgan paket uzunligi
 *
 * Bitta kalit bilan 2^32 dan ortiq xabar shifrlamang — undan oldin kalitni
 * almashtiring (tasodifiy nonce takrorlanish ehtimoli o'sadi).
 */
int aesgcm_encrypt(const uint8_t key[AESGCM_KEY_LEN],
                   const uint8_t *pt, size_t pt_len,
                   const uint8_t *aad, size_t aad_len,
                   uint8_t *out, size_t out_cap, size_t *out_len);

/*
 * Shifrlash, nonce'ni chaqiruvchi beradi (hisoblagich asosidagi nonce yoki
 * test vektorlari uchun). DIQQAT: bitta kalit bilan bir xil nonce ikki marta
 * ishlatilsa GCM himoyasi butunlay yo'qoladi.
 */
int aesgcm_encrypt_with_nonce(const uint8_t key[AESGCM_KEY_LEN],
                              const uint8_t nonce[AESGCM_NONCE_LEN],
                              const uint8_t *pt, size_t pt_len,
                              const uint8_t *aad, size_t aad_len,
                              uint8_t *out, size_t out_cap, size_t *out_len);

/*
 * Deshifrlash va tekshirish.
 *
 *   in       — aesgcm_encrypt hosil qilgan paket
 *   aad      — shifrlashda berilgan AAD ning aynan o'zi
 *   out      — ochiq matn yoziladigan bufer, kamida in_len - AESGCM_OVERHEAD bayt
 *
 * AESGCM_ERR_AUTH qaytsa, out nollanadi — undagi ma'lumotni ishlatmang.
 */
int aesgcm_decrypt(const uint8_t key[AESGCM_KEY_LEN],
                   const uint8_t *in, size_t in_len,
                   const uint8_t *aad, size_t aad_len,
                   uint8_t *out, size_t out_cap, size_t *out_len);

/*
 * Tasodifiy baytlar manbai. ESP32 da modul ichida esp_fill_random orqali
 * amalga oshirilgan; boshqa platformada (masalan, PC dagi test) buni
 * o'zingiz ta'riflaysiz.
 */
void aesgcm_random(uint8_t *buf, size_t len);

#ifdef __cplusplus
}
#endif

#endif /* AESGCM_H */
