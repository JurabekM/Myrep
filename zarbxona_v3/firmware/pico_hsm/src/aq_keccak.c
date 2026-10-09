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

static inline uint64_t rotl(uint64_t x, unsigned n) { return (x << n) | (x >> (64 - n)); }

/* `%` va ichki sikllarsiz (Cortex-M0+ da bo'lish va 64 bitli amallar qimmat). */
static void keccak_f(uint64_t s[25]) {
    uint64_t c0, c1, c2, c3, c4, d0, d1, d2, d3, d4, t, u;
    for (int r = 0; r < 24; r++) {
        c0 = s[0] ^ s[5] ^ s[10] ^ s[15] ^ s[20];
        c1 = s[1] ^ s[6] ^ s[11] ^ s[16] ^ s[21];
        c2 = s[2] ^ s[7] ^ s[12] ^ s[17] ^ s[22];
        c3 = s[3] ^ s[8] ^ s[13] ^ s[18] ^ s[23];
        c4 = s[4] ^ s[9] ^ s[14] ^ s[19] ^ s[24];
        d0 = c4 ^ rotl(c1, 1);
        d1 = c0 ^ rotl(c2, 1);
        d2 = c1 ^ rotl(c3, 1);
        d3 = c2 ^ rotl(c4, 1);
        d4 = c3 ^ rotl(c0, 1);
        for (int y = 0; y < 25; y += 5) {
            s[y] ^= d0;
            s[y + 1] ^= d1;
            s[y + 2] ^= d2;
            s[y + 3] ^= d3;
            s[y + 4] ^= d4;
        }
        t = s[1];
        for (int i = 0; i < 24; i++) {
            u = s[PI[i]];
            s[PI[i]] = rotl(t, ROT[i]);
            t = u;
        }
        for (int y = 0; y < 25; y += 5) {
            c0 = s[y];
            c1 = s[y + 1];
            c2 = s[y + 2];
            c3 = s[y + 3];
            c4 = s[y + 4];
            s[y] = c0 ^ (~c1 & c2);
            s[y + 1] = c1 ^ (~c2 & c3);
            s[y + 2] = c2 ^ (~c3 & c4);
            s[y + 3] = c3 ^ (~c4 & c0);
            s[y + 4] = c4 ^ (~c0 & c1);
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
    while (k->pos == 0 && n >= k->rate) { /* to'liq bloklar — 8 baytdan */
        for (size_t w = 0; w < k->rate / 8; w++) {
            uint64_t x = 0;
            for (int j = 7; j >= 0; j--) x = (x << 8) | d[8 * w + (size_t)j];
            k->s[w] ^= x;
        }
        keccak_f(k->s);
        d += k->rate;
        n -= k->rate;
    }
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
