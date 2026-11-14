/*
 * aesgcm modulining PC dagi testi (ESP32 siz). PC da mbedTLS kerak:
 *
 *   cc -I lib/aesgcm tools/host_test.c lib/aesgcm/aesgcm.c -lmbedcrypto \
 *      -o tools/host_test
 *   tools/host_test                                   # ichki testlar
 *   tools/host_test enc <kalit_hex> <aad> <matn>      # paket hex chiqaradi
 *   tools/host_test dec <kalit_hex> <aad> <paket_hex> # ochiq matn chiqaradi
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "aesgcm.h"

void aesgcm_random(uint8_t *buf, size_t len)
{
    FILE *f = fopen("/dev/urandom", "rb");
    if (f == NULL || fread(buf, 1, len, f) != len) {
        abort();
    }
    fclose(f);
}

static int failures;
#define CHECK(cond) \
    do { if (!(cond)) { printf("FAIL %d: %s\n", __LINE__, #cond); failures++; } } while (0)

static size_t unhex(const char *s, uint8_t *out, size_t cap)
{
    size_t n = strlen(s) / 2;
    if (strlen(s) % 2 != 0 || n > cap) {
        return (size_t)-1;
    }
    for (size_t i = 0; i < n; i++) {
        unsigned v;
        if (sscanf(s + 2 * i, "%2x", &v) != 1) {
            return (size_t)-1;
        }
        out[i] = (uint8_t)v;
    }
    return n;
}

static void self_tests(void)
{
    /* NIST GCM test vektori, AES-256, 14-holat. */
    static const uint8_t kat[12 + 16 + 16] = {
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0xce, 0xa7, 0x40, 0x3d, 0x4d, 0x60, 0x6b, 0x6e,
        0x07, 0x4e, 0xc5, 0xd3, 0xba, 0xf3, 0x9d, 0x18,
        0xd0, 0xd1, 0xc8, 0xa7, 0x99, 0x99, 0x6b, 0xf0,
        0x26, 0x5b, 0x98, 0xb5, 0xd4, 0x8a, 0xb9, 0x19,
    };
    static const uint8_t zeros[64] = {0};
    const uint8_t zkey[32] = {0}, znonce[12] = {0}, zpt[16] = {0};
    uint8_t pkt[512], out[512];
    size_t n = 0, m = 0;

    CHECK(aesgcm_encrypt_with_nonce(zkey, znonce, zpt, 16, NULL, 0, pkt, sizeof pkt, &n) == AESGCM_OK);
    CHECK(n == sizeof kat && memcmp(pkt, kat, n) == 0);

    uint8_t key[32];
    aesgcm_random(key, sizeof key);
    const uint8_t aad[] = "esp32-01";
    const char *msg = "SALOM, DUNYO! 123";
    const size_t len = strlen(msg);

    /* Aylanma: shifrlash -> deshifrlash. */
    CHECK(aesgcm_encrypt(key, (const uint8_t *)msg, len, aad, 8, pkt, sizeof pkt, &n) == AESGCM_OK);
    CHECK(n == len + AESGCM_OVERHEAD);
    CHECK(aesgcm_decrypt(key, pkt, n, aad, 8, out, sizeof out, &m) == AESGCM_OK);
    CHECK(m == len && memcmp(out, msg, len) == 0);

    /* Bir xil matn ikki marta shifrlansa, paketlar har xil bo'lishi kerak. */
    uint8_t pkt2[512];
    size_t n2 = 0;
    CHECK(aesgcm_encrypt(key, (const uint8_t *)msg, len, aad, 8, pkt2, sizeof pkt2, &n2) == AESGCM_OK);
    CHECK(n2 == n && memcmp(pkt, pkt2, n) != 0);

    /* Paketning har bir baytida bitta bit buzilsa, rad etilishi kerak. */
    for (size_t i = 0; i < n; i++) {
        pkt[i] ^= 0x01;
        memset(out, 0xAA, len);
        CHECK(aesgcm_decrypt(key, pkt, n, aad, 8, out, sizeof out, &m) == AESGCM_ERR_AUTH);
        CHECK(memcmp(out, zeros, len) == 0); /* ochiq matn sizib chiqmasin */
        pkt[i] ^= 0x01;
    }

    /* Noto'g'ri AAD, noto'g'ri kalit, kesilgan paket. */
    CHECK(aesgcm_decrypt(key, pkt, n, (const uint8_t *)"esp32-02", 8, out, sizeof out, &m) == AESGCM_ERR_AUTH);
    CHECK(aesgcm_decrypt(key, pkt, n, NULL, 0, out, sizeof out, &m) == AESGCM_ERR_AUTH);
    CHECK(aesgcm_decrypt(zkey, pkt, n, aad, 8, out, sizeof out, &m) == AESGCM_ERR_AUTH);
    CHECK(aesgcm_decrypt(key, pkt, n - 1, aad, 8, out, sizeof out, &m) == AESGCM_ERR_AUTH);
    CHECK(aesgcm_decrypt(key, pkt, AESGCM_OVERHEAD - 1, aad, 8, out, sizeof out, &m) == AESGCM_ERR_ARG);

    /* Bufer chegaralari. */
    CHECK(aesgcm_encrypt(key, (const uint8_t *)msg, len, aad, 8, pkt2, len + AESGCM_OVERHEAD - 1, &n2) == AESGCM_ERR_BUF);
    CHECK(aesgcm_decrypt(key, pkt, n, aad, 8, out, len - 1, &m) == AESGCM_ERR_BUF);
    CHECK(aesgcm_encrypt(key, (const uint8_t *)msg, len, aad, 8, pkt2, len + AESGCM_OVERHEAD, &n2) == AESGCM_OK);
    CHECK(aesgcm_decrypt(key, pkt2, n2, aad, 8, out, len, &m) == AESGCM_OK && m == len);

    /* Bo'sh ochiq matn (faqat autentifikatsiya). */
    CHECK(aesgcm_encrypt(key, NULL, 0, aad, 8, pkt, sizeof pkt, &n) == AESGCM_OK && n == AESGCM_OVERHEAD);
    CHECK(aesgcm_decrypt(key, pkt, n, aad, 8, NULL, 0, &m) == AESGCM_OK && m == 0);

    /* NULL argumentlar. */
    CHECK(aesgcm_encrypt(NULL, (const uint8_t *)msg, len, NULL, 0, pkt, sizeof pkt, &n) == AESGCM_ERR_ARG);
    CHECK(aesgcm_encrypt(key, NULL, 5, NULL, 0, pkt, sizeof pkt, &n) == AESGCM_ERR_ARG);
    CHECK(aesgcm_encrypt(key, (const uint8_t *)msg, len, NULL, 3, pkt, sizeof pkt, &n) == AESGCM_ERR_ARG);
}

int main(int argc, char **argv)
{
    if (argc == 1) {
        self_tests();
        if (failures) {
            printf("XATO: %d ta test o'tmadi\n", failures);
            return 1;
        }
        printf("Hamma testlar o'tdi\n");
        return 0;
    }
    if (argc != 5) {
        fprintf(stderr, "foydalanish: %s [enc|dec <kalit_hex> <aad> <ma'lumot>]\n", argv[0]);
        return 2;
    }
    uint8_t key[32], in[4096], out[4096 + AESGCM_OVERHEAD];
    size_t n = 0;
    if (unhex(argv[2], key, sizeof key) != sizeof key) {
        fprintf(stderr, "kalit 64 ta hex belgi bo'lishi kerak\n");
        return 2;
    }
    const uint8_t *aad = (const uint8_t *)argv[3];
    const size_t aad_len = strlen(argv[3]);
    int rc;
    if (strcmp(argv[1], "enc") == 0) {
        const size_t pt_len = strlen(argv[4]);
        if (pt_len > 4096) {
            fprintf(stderr, "matn juda uzun\n");
            return 2;
        }
        rc = aesgcm_encrypt(key, (const uint8_t *)argv[4], pt_len, aad, aad_len, out, sizeof out, &n);
        for (size_t i = 0; rc == AESGCM_OK && i < n; i++) {
            printf("%02x", out[i]);
        }
        printf("\n");
    } else {
        const size_t in_len = unhex(argv[4], in, sizeof in);
        if (in_len == (size_t)-1) {
            fprintf(stderr, "paket hex noto'g'ri\n");
            return 2;
        }
        rc = aesgcm_decrypt(key, in, in_len, aad, aad_len, out, sizeof out, &n);
        if (rc == AESGCM_OK) {
            printf("%.*s\n", (int)n, (const char *)out);
        }
    }
    if (rc != AESGCM_OK) {
        fprintf(stderr, "xato: %d\n", rc);
        return 1;
    }
    return 0;
}
