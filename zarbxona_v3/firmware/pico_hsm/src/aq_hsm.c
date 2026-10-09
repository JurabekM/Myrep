/* Zarbxona Pico HSM yadrosi — AQP1 protokoli va qurilma qoidalari.
 *
 * ETALON: core/pico/soxta.py (SoxtaPico). Har bir buyruqning tekshiruv TARTIBI va
 * xato kodlari o'sha bilan bir xil bo'lishi shart — tests/test_pico_ichki.py ikkalasini
 * bir xil testlar va tasodifiy kirishlar bilan solishtiradi.
 *
 * Bu faylda SDK yo'q: faqat aq_hal.h orqali. Shu sabab u kompyuterda ham yig'iladi. */
#include "aq_hsm.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "aq_hal.h"
#include "aq_keccak.h"
#include "mldsa_native.h"

/* --- protokol konstantalari (core/pico/protokol.py) -------------------------------- */
#define SARLAVHA_UZ 8
#define CRC_UZ 4
#define MAX_YUK 8192

enum {
    SALOM = 0x01, KALIT_YARAT = 0x02, KALIT_IMPORT = 0x03, PIN_OCH = 0x04, QULFLA = 0x05,
    RUXSAT = 0x06, HOLAT = 0x07, KALIT_OCHIR = 0x08, IMZO_PARTIYA = 0x10, IMZO_BOSH = 0x11,
    IMZO_MINT_AUTH = 0x12, KUTMOQDA = 0x7F, JAVOB_BIT = 0x80, XATO_RAMKA = 0xFF
};

enum {
    OK = 0, X_NOMALUM = 1, X_FORMAT = 2, X_KALIT_YOQ = 3, X_QULFLANGAN = 4, X_PIN = 5,
    X_TUGMA_YOQ = 6, X_RUXSAT_YOQ = 7, X_BYUDJET = 8, X_TARTIB = 9, X_KALIT_BOR = 10,
    X_OCHIRILDI = 11, X_ICHKI = 12, X_RAD = 13
};

#define PIN_MIN 6
#define PIN_MAX 64
#define MAX_URINISH 5
#define TUGMA_KUTISH_MS 30000u
#define MAX_RUXSAT_S 86400u
#define MAX_QULF_UZ 256
#define MAX_BUYURTMA_ID_UZ 64
#define MAX_CHAQIRIQ_UZ 128
#define ENTROPIYA_UZ 32
#define IMKONIYATLAR 0x01u

#define H_KALIT_BOR 0x01
#define H_OCHIQ 0x02
#define H_IMPORT 0x04
#define H_RUXSAT 0x08

#define PK_UZ MLDSA_PUBLICKEYBYTES(65)
#define SK_UZ MLDSA_SECRETKEYBYTES(65)
#define IMZO_UZ MLDSA_BYTES(65)
#define ML_DSA_PK_UZ 1952
#define PARTIYA_ID_UZ 16
#define SERT_ID_UZ 16

/* --- saqlash (core/pico/saqlash.py) ------------------------------------------------- */
#ifndef AQ_PIN_ITER
#define AQ_PIN_ITER 4096
#endif
#define SALT_UZ 16
#define TAG_UZ 16
#define URUG_UZ 32

static const char L_PIN[] = "AQ-PICO/PIN/v1";
static const char L_ENC[] = "AQ-PICO/ENC/v1";
static const char L_MAC[] = "AQ-PICO/MAC/v1";
static const char L_KEYGEN[] = "AQ-PICO/KEYGEN/v1";
static const char L_ROOT[] = "AETHER-Q-CBDC/BATCH-ROOT/v1";
static const char L_MINT_AUTH[] = "AETHER-Q-BANK/MINT-AUTH/v1";
static const char L_ZANJIR_BOSH[] = "AETHER-Q-ZARBXONA/JURNAL-BOSH/v1";

/* Xato matnlari — XATO_MATNI bilan aynan bir xil (xost ularni foydalanuvchiga ko'rsatadi). */
static const char *xato_matni_ol(int kod) {
    switch (kod) {
    case X_NOMALUM: return "noma'lum buyruq";
    case X_FORMAT: return "ramka yoki maydon formati xato";
    case X_KALIT_YOQ: return "Pico'da kalit yo'q";
    case X_QULFLANGAN: return "Pico qulflangan \xe2\x80\x94 PIN kerak";
    case X_PIN: return "PIN noto'g'ri";
    case X_TUGMA_YOQ: return "Pico tugmasi vaqtida bosilmadi";
    case X_RUXSAT_YOQ: return "Pico'da faol ruxsat yo'q (muddati tugagan bo'lishi mumkin)";
    case X_BYUDJET: return "partiya summasi Pico ruxsatidan oshadi";
    case X_TARTIB: return "jurnal boshi tartibi orqaga ketdi";
    case X_KALIT_BOR: return "Pico'da kalit allaqachon bor";
    case X_OCHIRILDI: return "PIN ko'p marta xato kiritildi \xe2\x80\x94 kalit O'CHIRILDI";
    case X_RAD: return "operator Pico tugmasi bilan RAD ETDI";
    default: return "Pico ichki xatosi";
    }
}

/* --- yordamchilar ------------------------------------------------------------------- */

static uint32_t crc32(const uint8_t *d, size_t n) {
    uint32_t c = 0xFFFFFFFFu;
    for (size_t i = 0; i < n; i++) {
        c ^= d[i];
        for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u)));
    }
    return c ^ 0xFFFFFFFFu;
}

static void le_yoz(uint8_t *p, uint64_t x, int n) {
    for (int i = 0; i < n; i++) p[i] = (uint8_t)(x >> (8 * i));
}

static uint64_t le_oqi(const uint8_t *p, int n) {
    uint64_t x = 0;
    for (int i = n - 1; i >= 0; i--) x = (x << 8) | p[i];
    return x;
}

static void tozala(void *p, size_t n) {
    volatile uint8_t *v = (volatile uint8_t *)p;
    while (n--) *v++ = 0;
}

static bool teng_vaqtda(const uint8_t *a, const uint8_t *b, size_t n) {
    uint8_t d = 0;
    for (size_t i = 0; i < n; i++) d |= (uint8_t)(a[i] ^ b[i]);
    return d == 0;
}

/* 128 bitli summa (32 bitli Cortex-M0+ da __int128 yo'q) */
typedef struct { uint64_t lo, hi; } u128;

static u128 u128_oqi(const uint8_t p[16]) {
    u128 r = {le_oqi(p, 8), le_oqi(p + 8, 8)};
    return r;
}
static void u128_yoz(uint8_t p[16], u128 x) {
    le_yoz(p, x.lo, 8);
    le_yoz(p + 8, x.hi, 8);
}
static bool u128_nol(u128 x) { return x.lo == 0 && x.hi == 0; }
static bool u128_katta(u128 a, u128 b) { /* a > b */
    return a.hi > b.hi || (a.hi == b.hi && a.lo > b.lo);
}
static u128 u128_ayir(u128 a, u128 b) {
    u128 r = {a.lo - b.lo, a.hi - b.hi - (a.lo < b.lo ? 1u : 0u)};
    return r;
}
static size_t u128_matn(char *out, u128 x) { /* o'nlik, out ≥ 40 bayt */
    char t[40];
    size_t n = 0;
    do { /* x /= 10, qoldiq — 32 bitli bo'laklar bilan */
        uint32_t q[4] = {(uint32_t)(x.hi >> 32), (uint32_t)x.hi, (uint32_t)(x.lo >> 32),
                         (uint32_t)x.lo};
        uint64_t qol = 0;
        for (int i = 0; i < 4; i++) {
            uint64_t cur = (qol << 32) | q[i];
            q[i] = (uint32_t)(cur / 10);
            qol = cur % 10;
        }
        t[n++] = (char)('0' + qol);
        x.hi = ((uint64_t)q[0] << 32) | q[1];
        x.lo = ((uint64_t)q[2] << 32) | q[3];
    } while (!u128_nol(x));
    for (size_t i = 0; i < n; i++) out[i] = t[n - 1 - i];
    out[n] = 0;
    return n;
}

static bool utf8_togri(const uint8_t *s, size_t n) {
    size_t i = 0;
    while (i < n) {
        uint8_t c = s[i];
        size_t k;
        uint32_t cp;
        if (c < 0x80) { i++; continue; }
        if (c >= 0xC2 && c <= 0xDF) { k = 1; cp = c & 0x1F; }
        else if (c >= 0xE0 && c <= 0xEF) { k = 2; cp = c & 0x0F; }
        else if (c >= 0xF0 && c <= 0xF4) { k = 3; cp = c & 0x07; }
        else return false;
        if (i + k >= n) return false; /* davom baytlari yetmaydi */
        for (size_t j = 1; j <= k; j++) {
            if ((s[i + j] & 0xC0) != 0x80) return false;
            cp = (cp << 6) | (s[i + j] & 0x3F);
        }
        if ((k == 2 && cp < 0x800) || (k == 3 && (cp < 0x10000 || cp > 0x10FFFF)) ||
            (cp >= 0xD800 && cp <= 0xDFFF))
            return false;
        i += k + 1;
    }
    return true;
}

static bool ascii_bosh_joy(uint8_t c) {
    return c == ' ' || (c >= 0x09 && c <= 0x0D) || (c >= 0x1C && c <= 0x1F);
}

/* --- holat -------------------------------------------------------------------------- */

typedef struct {
    bool bor, import_;
    uint8_t urinish;
    uint8_t salt[SALT_UZ], ct[URUG_UZ], tag[TAG_UZ];
} kalit_yozuvi;

static kalit_yozuvi yozuv;
static bool ochiq;
static uint8_t urug[URUG_UZ];
static uint8_t pk[PK_UZ];
static uint8_t sk[SK_UZ];
static bool ruxsat_bor;
static u128 byudjet;
static uint64_t ruxsat_tugash_ms;
static bool tartib_bor;
static uint64_t oxirgi_tartib;
static uint32_t imzolar;
static uint8_t seriya[8];

static uint16_t joriy_seq;
static uint8_t imzo[IMZO_UZ];

/* --- flash yozuvi --------------------------------------------------------------------
 * 0 'AQK1' · 4 versiya=1 · 5 bayroqlar (bit0 bor, bit1 import) · 6 urinish · 7 zaxira ·
 * 8 salt[16] · 24 ct[32] · 56 tag[16] · 72 crc32 (LE, [0,72) ustidan) · qolgani 0xFF */

static void flash_saqla(void) {
    uint8_t p[AQ_FLASH_YOZUV_UZ];
    memset(p, 0xFF, sizeof p);
    if (yozuv.bor) {
        memcpy(p, "AQK1", 4);
        p[4] = 1;
        p[5] = (uint8_t)(1u | (yozuv.import_ ? 2u : 0u));
        p[6] = yozuv.urinish;
        p[7] = 0;
        memcpy(p + 8, yozuv.salt, SALT_UZ);
        memcpy(p + 24, yozuv.ct, URUG_UZ);
        memcpy(p + 56, yozuv.tag, TAG_UZ);
        le_yoz(p + 72, crc32(p, 72), 4);
    }
    hal_flash_yoz(p);
    tozala(p, sizeof p);
}

static void flash_yukla(void) {
    uint8_t p[AQ_FLASH_YOZUV_UZ];
    memset(&yozuv, 0, sizeof yozuv);
    if (hal_flash_oqi(p) && memcmp(p, "AQK1", 4) == 0 && p[4] == 1 && (p[5] & 1u) &&
        le_oqi(p + 72, 4) == crc32(p, 72)) {
        yozuv.bor = true;
        yozuv.import_ = (p[5] & 2u) != 0;
        yozuv.urinish = p[6];
        memcpy(yozuv.salt, p + 8, SALT_UZ);
        memcpy(yozuv.ct, p + 24, URUG_UZ);
        memcpy(yozuv.tag, p + 56, TAG_UZ);
    }
    tozala(p, sizeof p);
}

/* --- PIN bilan himoya ------------------------------------------------------------------ */

static void sha3_qismlar(uint8_t out[32], const uint8_t *a, size_t an, const uint8_t *b,
                         size_t bn, const uint8_t *c, size_t cn) {
    aq_keccak k;
    aq_sha3_256_init(&k);
    aq_keccak_update(&k, a, an);
    aq_keccak_update(&k, b, bn);
    aq_keccak_update(&k, c, cn);
    aq_keccak_final(&k, out, 32);
}

static void himoya_kalitlari(const uint8_t *pin, size_t pn, const uint8_t salt[SALT_UZ],
                             uint8_t ek[32], uint8_t mk[32]) {
    uint8_t k[32];
    sha3_qismlar(k, (const uint8_t *)L_PIN, strlen(L_PIN), salt, SALT_UZ, pin, pn);
    for (int i = 1; i < AQ_PIN_ITER; i++) sha3_qismlar(k, k, 32, pin, pn, NULL, 0);
    sha3_qismlar(ek, (const uint8_t *)L_ENC, strlen(L_ENC), k, 32, NULL, 0);
    sha3_qismlar(mk, (const uint8_t *)L_MAC, strlen(L_MAC), k, 32, NULL, 0);
    tozala(k, sizeof k);
}

static void oqim(const uint8_t ek[32], const uint8_t salt[SALT_UZ], uint8_t out[URUG_UZ]) {
    aq_keccak k;
    aq_shake256_init(&k);
    aq_keccak_update(&k, ek, 32);
    aq_keccak_update(&k, salt, SALT_UZ);
    aq_keccak_final(&k, out, URUG_UZ);
}

static void shifrla(const uint8_t u[URUG_UZ], const uint8_t *pin, size_t pn) {
    uint8_t ek[32], mk[32], s[URUG_UZ], t[32];
    hal_tasodif(yozuv.salt, SALT_UZ);
    himoya_kalitlari(pin, pn, yozuv.salt, ek, mk);
    oqim(ek, yozuv.salt, s);
    for (int i = 0; i < URUG_UZ; i++) yozuv.ct[i] = (uint8_t)(u[i] ^ s[i]);
    sha3_qismlar(t, mk, 32, yozuv.salt, SALT_UZ, yozuv.ct, URUG_UZ);
    memcpy(yozuv.tag, t, TAG_UZ);
    tozala(ek, 32); tozala(mk, 32); tozala(s, sizeof s);
}

static bool och(const uint8_t *pin, size_t pn, uint8_t out[URUG_UZ]) {
    uint8_t ek[32], mk[32], s[URUG_UZ], t[32];
    himoya_kalitlari(pin, pn, yozuv.salt, ek, mk);
    sha3_qismlar(t, mk, 32, yozuv.salt, SALT_UZ, yozuv.ct, URUG_UZ);
    bool togri = teng_vaqtda(t, yozuv.tag, TAG_UZ);
    if (togri) {
        oqim(ek, yozuv.salt, s);
        for (int i = 0; i < URUG_UZ; i++) out[i] = (uint8_t)(yozuv.ct[i] ^ s[i]);
    }
    tozala(ek, 32); tozala(mk, 32); tozala(s, sizeof s);
    return togri;
}

/* --- holat o'tishlari ----------------------------------------------------------------- */

static void qulfla(void) {
    tozala(urug, sizeof urug);
    tozala(sk, sizeof sk);
    ochiq = false;
    ruxsat_bor = false;
    tartib_bor = false;
}

static int ochil(const uint8_t u[URUG_UZ]) {
    qulfla();
    memcpy(urug, u, URUG_UZ);
    if (mldsa_keypair_internal(pk, sk, urug) != 0) {
        qulfla();
        return X_ICHKI;
    }
    ochiq = true;
    return OK;
}

static bool ruxsat_faol(void) { return ruxsat_bor && hal_ms() < ruxsat_tugash_ms; }

static uint8_t holat_bitlari(void) {
    uint8_t h = 0;
    if (yozuv.bor) h |= (uint8_t)(H_KALIT_BOR | (yozuv.import_ ? H_IMPORT : 0));
    if (ochiq) h |= H_OCHIQ;
    if (ruxsat_faol()) h |= H_RUXSAT;
    return h;
}

/* --- ramka chiqarish ------------------------------------------------------------------ */

static uint8_t tx[SARLAVHA_UZ + 4096 + CRC_UZ];
static size_t jw; /* javob yuki uzunligi (tx + 8 dan) */

static void ramka_yubor(uint8_t *buf, uint8_t kod, uint16_t seq, size_t n) {
    buf[0] = 'A'; buf[1] = 'Q'; buf[2] = 1; buf[3] = kod;
    le_yoz(buf + 4, seq, 2);
    le_yoz(buf + 6, n, 2);
    le_yoz(buf + SARLAVHA_UZ + n, crc32(buf, SARLAVHA_UZ + n), 4);
    hal_yubor(buf, SARLAVHA_UZ + n + CRC_UZ);
}

static void j_boshla(uint8_t holat) {
    jw = 0;
    tx[SARLAVHA_UZ + jw++] = holat;
}

static void j_maydon(const void *d, size_t n) {
    le_yoz(tx + SARLAVHA_UZ + jw, n, 2);
    memcpy(tx + SARLAVHA_UZ + jw + 2, d, n);
    jw += 2 + n;
}

static void j_u8(uint8_t x) { j_maydon(&x, 1); }
static void j_u32(uint32_t x) { uint8_t b[4]; le_yoz(b, x, 4); j_maydon(b, 4); }

/* Tugmani so'rash: avval KUTMOQDA (xost operatorga ko'rsatadi), keyin kutish. */
static int tasdiq_ol(const char *matn) {
    static uint8_t k[SARLAVHA_UZ + 2 + 200 + CRC_UZ];
    size_t n = strlen(matn);
    if (n > 200) n = 200;
    le_yoz(k + SARLAVHA_UZ, n, 2);
    memcpy(k + SARLAVHA_UZ + 2, matn, n);
    ramka_yubor(k, KUTMOQDA, joriy_seq, n + 2);
    hal_led(LED_KUTISH);
    int t = hal_tugma(TUGMA_KUTISH_MS);
    hal_led(LED_OCHIQ);
    if (t == TUGMA_RAD) return X_RAD;
    if (t != TUGMA_HA) return X_TUGMA_YOQ;
    return OK;
}

/* --- buyruqlar ---------------------------------------------------------------------- */

typedef struct { const uint8_t *p; size_t n; } maydon;

static const char *xato_matn;      /* NULL — standart matn */
static uint8_t xato_qosh[16];      /* qo'shimcha maydon (X_PIN, X_BYUDJET) */
static size_t xato_qosh_n;

#define TEKSHIR(shart) do { if (!(shart)) return X_FORMAT; } while (0)

static int pin_togri(const maydon *m) {
    if (m->n < PIN_MIN || m->n > PIN_MAX) {
        xato_matn = "PIN 6..64 bayt bo'lsin";
        return X_FORMAT;
    }
    return OK;
}

static int kalit_kerak(bool sk_kerak) {
    if (!yozuv.bor) return X_KALIT_YOQ;
    if (sk_kerak && !ochiq) return X_QULFLANGAN;
    return OK;
}

/* Urinish hisobi tekshiruvdan OLDIN flash'ga yoziladi. */
static int pin_tekshir(const maydon *pin, uint8_t out[URUG_UZ]) {
    yozuv.urinish++;
    flash_saqla();
    if (!och(pin->p, pin->n, out)) {
        if (yozuv.urinish >= MAX_URINISH) {
            memset(&yozuv, 0, sizeof yozuv);
            qulfla();
            flash_saqla();
            return X_OCHIRILDI;
        }
        xato_qosh[0] = (uint8_t)(MAX_URINISH - yozuv.urinish);
        xato_qosh_n = 1;
        return X_PIN;
    }
    yozuv.urinish = 0;
    flash_saqla();
    return OK;
}

static int b_salom(const maydon *f, int nf) {
    TEKSHIR(nf == 0);
    (void)f;
    j_maydon(AQ_QURILMA_VERSIYASI, strlen(AQ_QURILMA_VERSIYASI));
    j_u32(IMKONIYATLAR);
    j_u8(holat_bitlari());
    j_maydon(pk, ochiq ? PK_UZ : 0);
    j_maydon(seriya, 8);
    j_u8((uint8_t)(yozuv.bor ? MAX_URINISH - yozuv.urinish : MAX_URINISH));
    return OK;
}

static int kalit_ornat(const maydon *pin, const uint8_t u[URUG_UZ], bool import_) {
    memset(&yozuv, 0, sizeof yozuv);
    shifrla(u, pin->p, pin->n);
    yozuv.bor = true;
    yozuv.import_ = import_;
    flash_saqla();
    int r = ochil(u);
    if (r) return r;
    j_maydon(pk, PK_UZ);
    return OK;
}

static int b_kalit_yarat(const maydon *f, int nf) {
    TEKSHIR(nf == 2);
    int r = pin_togri(&f[0]);
    if (r) return r;
    TEKSHIR(f[1].n == ENTROPIYA_UZ);
    if (yozuv.bor) return X_KALIT_BOR;
    if ((r = tasdiq_ol("YANGI KALIT yaratish"))) return r;
    uint8_t q[32], u[URUG_UZ];
    hal_tasodif(q, sizeof q);
    aq_keccak k;
    aq_sha3_256_init(&k);
    aq_keccak_update(&k, (const uint8_t *)L_KEYGEN, strlen(L_KEYGEN));
    aq_keccak_update(&k, q, sizeof q);
    aq_keccak_update(&k, f[1].p, f[1].n);
    aq_keccak_final(&k, u, URUG_UZ);
    r = kalit_ornat(&f[0], u, false);
    tozala(q, sizeof q);
    tozala(u, sizeof u);
    return r;
}

static int b_kalit_import(const maydon *f, int nf) {
    TEKSHIR(nf == 2);
    int r = pin_togri(&f[0]);
    if (r) return r;
    TEKSHIR(f[1].n == URUG_UZ);
    if (yozuv.bor) return X_KALIT_BOR;
    if ((r = tasdiq_ol("Mavjud kalitni IMPORT qilish"))) return r;
    return kalit_ornat(&f[0], f[1].p, true);
}

static int b_pin_och(const maydon *f, int nf) {
    TEKSHIR(nf == 1);
    int r = pin_togri(&f[0]);
    if (r) return r;
    if ((r = kalit_kerak(false))) return r;
    uint8_t u[URUG_UZ];
    if ((r = pin_tekshir(&f[0], u))) return r;
    r = ochil(u);
    tozala(u, sizeof u);
    return r;
}

static int b_qulfla(const maydon *f, int nf) {
    TEKSHIR(nf == 0);
    (void)f;
    qulfla();
    return OK;
}

static int b_kalit_ochir(const maydon *f, int nf) {
    TEKSHIR(nf == 1);
    int r = pin_togri(&f[0]);
    if (r) return r;
    if ((r = kalit_kerak(false))) return r;
    uint8_t u[URUG_UZ];
    r = pin_tekshir(&f[0], u);
    tozala(u, sizeof u);
    if (r) return r;
    if ((r = tasdiq_ol("Kalitni O'CHIRISH"))) return r;
    memset(&yozuv, 0, sizeof yozuv);
    qulfla();
    flash_saqla();
    return OK;
}

static int b_ruxsat(const maydon *f, int nf) {
    TEKSHIR(nf == 3);
    int r = kalit_kerak(true);
    if (r) return r;
    TEKSHIR(f[1].n == 16 && f[2].n == 4);
    u128 summa = u128_oqi(f[1].p);
    uint32_t muddat = (uint32_t)le_oqi(f[2].p, 4);
    TEKSHIR(f[0].n >= 1 && f[0].n <= MAX_BUYURTMA_ID_UZ && !u128_nol(summa) && muddat >= 1 &&
            muddat <= MAX_RUXSAT_S);
    char m[200], s[40];
    u128_matn(s, summa);
    snprintf(m, sizeof m, "RUXSAT: buyurtma %.*s \xc2\xb7 %s so'm", (int)f[0].n,
             (const char *)f[0].p, s);
    if ((r = tasdiq_ol(m))) return r;
    byudjet = summa;
    ruxsat_tugash_ms = hal_ms() + (uint64_t)muddat * 1000u;
    ruxsat_bor = true;
    return OK;
}

static int b_holat(const maydon *f, int nf) {
    TEKSHIR(nf == 0);
    (void)f;
    bool faol = ruxsat_faol();
    uint8_t b[16];
    u128 nol = {0, 0};
    j_u8(holat_bitlari());
    u128_yoz(b, faol ? byudjet : nol);
    j_maydon(b, 16);
    j_u32(faol ? (uint32_t)((ruxsat_tugash_ms - hal_ms()) / 1000u) : 0u);
    j_u32(imzolar);
    return OK;
}

static int imzola_va_qaytar(const uint8_t *m, size_t n) {
    if (mldsa_signature(imzo, m, n, NULL, 0, sk) != 0) return X_ICHKI;
    imzolar++;
    j_maydon(imzo, IMZO_UZ);
    return OK;
}

static void lp(uint8_t *b, size_t *w, const void *d, size_t n) { /* LE u64 prefiks */
    le_yoz(b + *w, n, 8);
    memcpy(b + *w + 8, d, n);
    *w += 8 + n;
}

static void tagged(aq_keccak *k, const void *d, size_t n) { /* BE u32 prefiks */
    uint8_t l[4] = {(uint8_t)(n >> 24), (uint8_t)(n >> 16), (uint8_t)(n >> 8), (uint8_t)n};
    aq_keccak_update(k, l, 4);
    aq_keccak_update(k, d, n);
}

static int b_imzo_partiya(const maydon *f, int nf) {
    TEKSHIR(nf == 6);
    int r = kalit_kerak(true);
    if (r) return r;
    TEKSHIR(f[2].n == 8 && f[3].n == 16 && f[5].n == 8);
    uint64_t soni = le_oqi(f[2].p, 8);
    u128 jami = u128_oqi(f[3].p);
    const maydon *q = &f[4];
    TEKSHIR(f[0].n == 32 && f[1].n == PARTIYA_ID_UZ && soni >= 1 && !u128_nol(jami) &&
            q->n >= 1 && q->n <= MAX_QULF_UZ && utf8_togri(q->p, q->n) &&
            !ascii_bosh_joy(q->p[0]) && !ascii_bosh_joy(q->p[q->n - 1]));
    if (!ruxsat_faol()) return X_RUXSAT_YOQ;
    if (u128_katta(jami, byudjet)) {
        u128_yoz(xato_qosh, byudjet);
        xato_qosh_n = 16;
        return X_BYUDJET;
    }
    /* §6.2 BATCH-ROOT/v1 xabari — core/partiya.py: imzo_xabari */
    static uint8_t m[8 * 7 + sizeof L_ROOT + 32 + PARTIYA_ID_UZ + 8 + 16 + MAX_QULF_UZ + 8];
    size_t w = 0;
    lp(m, &w, L_ROOT, strlen(L_ROOT));
    lp(m, &w, f[0].p, 32);
    lp(m, &w, f[1].p, PARTIYA_ID_UZ);
    lp(m, &w, f[2].p, 8);
    lp(m, &w, f[3].p, 16);
    lp(m, &w, q->p, q->n);
    lp(m, &w, f[5].p, 8);
    if ((r = imzola_va_qaytar(m, w))) return r;
    byudjet = u128_ayir(byudjet, jami);
    return OK;
}

static int b_imzo_bosh(const maydon *f, int nf) {
    TEKSHIR(nf == 2);
    int r = kalit_kerak(true);
    if (r) return r;
    TEKSHIR(f[0].n == 8);
    uint64_t tartib = le_oqi(f[0].p, 8);
    TEKSHIR(f[1].n == 32);
    if (tartib_bor && tartib < oxirgi_tartib) return X_TARTIB;
    if (!ruxsat_faol()) {
        char m[80];
        snprintf(m, sizeof m, "Jurnal boshi #%llu (ruxsatsiz)", (unsigned long long)tartib);
        if ((r = tasdiq_ol(m))) return r;
    }
    oxirgi_tartib = tartib;
    tartib_bor = true;
    uint8_t be[8], x[32];
    for (int i = 0; i < 8; i++) be[i] = (uint8_t)(tartib >> (56 - 8 * i));
    aq_keccak k;
    aq_sha3_256_init(&k);
    tagged(&k, L_ZANJIR_BOSH, strlen(L_ZANJIR_BOSH));
    tagged(&k, be, 8);
    tagged(&k, f[1].p, 32);
    aq_keccak_final(&k, x, 32);
    return imzola_va_qaytar(x, 32);
}

static int b_imzo_mint_auth(const maydon *f, int nf) {
    TEKSHIR(nf == 3);
    int r = kalit_kerak(true);
    if (r) return r;
    TEKSHIR(f[0].n == ML_DSA_PK_UZ && f[1].n >= 1 && f[1].n <= MAX_CHAQIRIQ_UZ &&
            f[2].n == SERT_ID_UZ);
    uint8_t x[32];
    aq_keccak k;
    aq_sha3_256_init(&k);
    tagged(&k, L_MINT_AUTH, strlen(L_MINT_AUTH));
    tagged(&k, f[0].p, f[0].n);
    tagged(&k, f[1].p, f[1].n);
    tagged(&k, f[2].p, f[2].n);
    aq_keccak_final(&k, x, 32);
    return imzola_va_qaytar(x, 32);
}

typedef int (*ishlov)(const maydon *, int);

static ishlov ishlov_top(uint8_t kod) {
    switch (kod) {
    case SALOM: return b_salom;
    case KALIT_YARAT: return b_kalit_yarat;
    case KALIT_IMPORT: return b_kalit_import;
    case PIN_OCH: return b_pin_och;
    case QULFLA: return b_qulfla;
    case RUXSAT: return b_ruxsat;
    case HOLAT: return b_holat;
    case KALIT_OCHIR: return b_kalit_ochir;
    case IMZO_PARTIYA: return b_imzo_partiya;
    case IMZO_BOSH: return b_imzo_bosh;
    case IMZO_MINT_AUTH: return b_imzo_mint_auth;
    default: return NULL;
    }
}

#define MAX_MAYDON 8

static void bajar(uint8_t kod, uint16_t seq, const uint8_t *yuk, size_t n) {
    maydon f[MAX_MAYDON];
    int nf = 0, r;
    size_t i = 0;
    joriy_seq = seq;
    xato_matn = NULL;
    xato_qosh_n = 0;
    ishlov h = ishlov_top(kod);
    j_boshla(OK);
    /* Etalondagidek: avval maydonlar tuzilishi (xato — FORMAT), keyin buyruq kodi. */
    r = OK;
    while (i < n) {
        if (i + 2 > n) { r = X_FORMAT; break; }
        size_t m = (size_t)le_oqi(yuk + i, 2);
        i += 2;
        if (i + m > n) { r = X_FORMAT; break; }
        if (nf < MAX_MAYDON) {
            f[nf].p = yuk + i;
            f[nf].n = m;
        }
        nf++; /* MAX_MAYDON dan ko'p bo'lsa ham sanaymiz: ishlovchi soni bilan rad etadi */
        i += m;
    }
    if (r == OK) r = h == NULL ? X_NOMALUM : h(f, nf);
    if (r != OK) {
        const char *m = xato_matn ? xato_matn : xato_matni_ol(r);
        j_boshla((uint8_t)r);
        j_maydon(m, strlen(m));
        if (xato_qosh_n) j_maydon(xato_qosh, xato_qosh_n);
    }
    ramka_yubor(tx, (uint8_t)(kod | JAVOB_BIT), seq, jw);
}

/* --- kirish oqimi ------------------------------------------------------------------- */

static uint8_t rx[SARLAVHA_UZ + MAX_YUK + CRC_UZ];
static size_t rn;

static void tashla(size_t k) {
    memmove(rx, rx + k, rn - k);
    rn -= k;
}

static void buzilgan_ramka(void) {
    j_boshla(X_FORMAT);
    const char *m = xato_matni_ol(X_FORMAT);
    j_maydon(m, strlen(m));
    ramka_yubor(tx, XATO_RAMKA, 0, jw);
}

static void ishlov_ber(void) {
    for (;;) {
        size_t i = 0;
        while (i + 1 < rn && !(rx[i] == 'A' && rx[i + 1] == 'Q')) i++;
        if (i + 1 >= rn) { /* sehr yo'q — oxirgi baytni saqlaymiz ('A' bo'lishi mumkin) */
            if (rn > 1) tashla(rn - 1);
            return;
        }
        if (i) tashla(i);
        if (rn < SARLAVHA_UZ) return;
        size_t n = (size_t)le_oqi(rx + 6, 2);
        if (rx[2] != 1 || n > MAX_YUK) {
            tashla(2);
            buzilgan_ramka();
            continue;
        }
        if (rn < SARLAVHA_UZ + n + CRC_UZ) return;
        if (le_oqi(rx + SARLAVHA_UZ + n, 4) != crc32(rx, SARLAVHA_UZ + n)) {
            tashla(2);
            buzilgan_ramka();
            continue;
        }
        bajar(rx[3], (uint16_t)le_oqi(rx + 4, 2), rx + SARLAVHA_UZ, n);
        tashla(SARLAVHA_UZ + n + CRC_UZ);
    }
}

void aq_hsm_qabul(const uint8_t *d, size_t n) {
    while (n) {
        size_t joy = sizeof rx - rn, k = n < joy ? n : joy;
        memcpy(rx + rn, d, k);
        rn += k;
        d += k;
        n -= k;
        ishlov_ber();
        if (rn == sizeof rx) tashla(2); /* bo'lishi mumkin emas — himoya uchun */
    }
}

void aq_hsm_boshla(void) {
    hal_seriya(seriya);
    flash_yukla();
    qulfla();
    rn = 0;
    imzolar = 0;
}

int aq_hsm_led_holati(void) {
    if (!ochiq) return LED_QULF;
    return ruxsat_faol() ? LED_RUXSAT : LED_OCHIQ;
}
