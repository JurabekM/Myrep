/* SHA3-256 va SHAKE256 (FIPS 202) — ixcham, jadvalsiz Keccak-f[1600].
 * Qurilma ichki ishlari uchun: PIN KDF, flash yozuvi, tagged_hash. ML-DSA o'z
 * Keccak'idan foydalanadi (mldsa-native). */
#ifndef AQ_KECCAK_H
#define AQ_KECCAK_H

#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint64_t s[25];
    size_t pos;      /* joriy blokdagi bayt o'rni */
    size_t rate;     /* 136 (SHA3-256, SHAKE256) */
    uint8_t pad;     /* 0x06 (SHA3) yoki 0x1F (SHAKE) */
} aq_keccak;

void aq_sha3_256_init(aq_keccak *k);
void aq_shake256_init(aq_keccak *k);
void aq_keccak_update(aq_keccak *k, const uint8_t *d, size_t n);
/* SHA3-256: out 32 bayt. SHAKE256: istalgan uzunlik (bir marta chaqiriladi). */
void aq_keccak_final(aq_keccak *k, uint8_t *out, size_t n);

void aq_sha3_256(uint8_t out[32], const uint8_t *d, size_t n);

#endif
