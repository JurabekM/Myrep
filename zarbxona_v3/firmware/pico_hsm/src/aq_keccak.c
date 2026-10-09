/* Keccak-f[1600] — FIPS 202 bo'yicha to'g'ridan-to'g'ri yozilgan, jadvalsiz
 * (rotatsiya va pi joylashuvi hisoblanadi). Tezlik emas, kichiklik va tekshirib
 * bo'ladiganlik maqsad: testlar Python hashlib bilan solishtiradi. */
#include "aq_keccak.h"

#include <string.h>

static const uint64_t RC[24] = {
    0x0000000000000001ULL, 0x0000000000008082ULL, 0x800000000000808aULL,
    0x8000000080008000ULL, 0x000000000000808bULL, 0x0000000080000001ULL,
    0x8000000080008081ULL, 0x8000000000008009ULL, 0x000000000000008aULL,
    0x0000000000000088ULL, 0x0000000080008009ULL, 0x000000008000000aULL,
    0x000000008000808bULL, 0x800000000000008bULL, 0x8000000000008089ULL,
    0x8000000000008003ULL, 0x8000000000008002ULL, 0x8000000000000080ULL,
    0x000000000000800aULL, 0x800000008000000aULL, 0x8000000080008081ULL,
    0x8000000000008080ULL, 0x0000000080000001ULL, 0x8000000080008008ULL,
};

static const uint8_t ROT[24] = {1,  3,  6,  10, 15, 21, 28, 36, 45, 55, 2,  14,
                                27, 41, 56, 8,  25, 43, 62, 18, 39, 61, 20, 44};
static const uint8_t PI[24] = {10, 7,  11, 17, 18, 3, 5,  16, 8,  21, 24, 4,
                               15, 23, 19, 13, 12, 2, 20, 14, 22, 9,  6,  1};

static uint64_t rotl(uint64_t x, unsigned n) { return (x << n) | (x >> (64 - n)); }

static void keccak_f(uint64_t s[25]) {
    uint64_t c[5], t;
    for (int r = 0; r < 24; r++) {
        for (int x = 0; x < 5; x++) c[x] = s[x] ^ s[x + 5] ^ s[x + 10] ^ s[x + 15] ^ s[x + 20];
        for (int x = 0; x < 5; x++) {
            t = c[(x + 4) % 5] ^ rotl(c[(x + 1) % 5], 1);
            for (int y = 0; y < 25; y += 5) s[y + x] ^= t;
        }
        t = s[1];
        for (int i = 0; i < 24; i++) {
            uint64_t u = s[PI[i]];
            s[PI[i]] = rotl(t, ROT[i]);
            t = u;
        }
        for (int y = 0; y < 25; y += 5) {
            for (int x = 0; x < 5; x++) c[x] = s[y + x];
            for (int x = 0; x < 5; x++) s[y + x] = c[x] ^ ((~c[(x + 1) % 5]) & c[(x + 2) % 5]);
        }
        s[0] ^= RC[r];
    }
}

static void xor_bayt(uint64_t s[25], size_t i, uint8_t b) {
    s[i / 8] ^= (uint64_t)b << (8 * (i % 8));
}

static uint8_t ol_bayt(const uint64_t s[25], size_t i) {
    return (uint8_t)(s[i / 8] >> (8 * (i % 8)));
}

static void boshla(aq_keccak *k, uint8_t pad) {
    memset(k, 0, sizeof *k);
    k->rate = 136;
    k->pad = pad;
}

void aq_sha3_256_init(aq_keccak *k) { boshla(k, 0x06); }
void aq_shake256_init(aq_keccak *k) { boshla(k, 0x1F); }

void aq_keccak_update(aq_keccak *k, const uint8_t *d, size_t n) {
    for (size_t i = 0; i < n; i++) {
        xor_bayt(k->s, k->pos++, d[i]);
        if (k->pos == k->rate) {
            keccak_f(k->s);
            k->pos = 0;
        }
    }
}

void aq_keccak_final(aq_keccak *k, uint8_t *out, size_t n) {
    xor_bayt(k->s, k->pos, k->pad);
    xor_bayt(k->s, k->rate - 1, 0x80);
    keccak_f(k->s);
    size_t j = 0;
    for (size_t i = 0; i < n; i++) {
        if (j == k->rate) {
            keccak_f(k->s);
            j = 0;
        }
        out[i] = ol_bayt(k->s, j++);
    }
    memset(k->s, 0, sizeof k->s);
}

void aq_sha3_256(uint8_t out[32], const uint8_t *d, size_t n) {
    aq_keccak k;
    aq_sha3_256_init(&k);
    aq_keccak_update(&k, d, n);
    aq_keccak_final(&k, out, 32);
}
