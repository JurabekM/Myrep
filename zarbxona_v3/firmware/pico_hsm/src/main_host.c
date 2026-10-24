/* Kompyuter HAL'i — ichki dastur yadrosini testlash uchun (Linux/macOS).
 *
 *   stdin/stdout  — USB CDC o'rnida (ikkilik oqim);
 *   AQ_FLASH      — flash sahifasi fayli (yo'q bo'lsa — bo'sh flash);
 *   AQ_TUGMA      — tugma javoblari navbati: "ha,rad,yoq,..." (tugagach — "ha");
 *   AQ_SERIYA     — 16 ta hex belgi (default 0102030405060708);
 *   AQ_STEK       — o'rnatilsa, chiqishda stderr'ga stek va arena cho'qqisi.
 *
 * Yadro bo'yalgan (ma'lum naqsh bilan to'ldirilgan) stekda ishlaydi: chiqishda qancha
 * stek ishlatilgani o'lchanadi — RP2040'ning 4 KB li stekiga sig'ishini tekshirish uchun. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "aq_hal.h"
#include "aq_hsm.h"

size_t aq_arena_eng_kop(void);

static struct timespec t0;
static char tugma_navbat[256];
static char *tugma_joy;

void hal_yubor(const uint8_t *d, size_t n) {
    while (n) {
        ssize_t k = write(1, d, n);
        if (k < 0) {
            if (errno == EINTR) continue;
            exit(3);
        }
        d += k;
        n -= (size_t)k;
    }
}

void hal_tasodif(uint8_t *out, size_t n) {
    int f = open("/dev/urandom", O_RDONLY);
    size_t o = 0;
    while (f >= 0 && o < n) {
        ssize_t k = read(f, out + o, n - o);
        if (k <= 0) break;
        o += (size_t)k;
    }
    if (f >= 0) close(f);
    if (o != n) abort(); /* tasodifsiz davom etmaymiz */
}

uint64_t hal_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)(t.tv_sec - t0.tv_sec) * 1000u + (uint64_t)((t.tv_nsec - t0.tv_nsec) / 1000000);
}

int hal_tugma(uint32_t kutish_ms) {
    (void)kutish_ms;
    if (tugma_joy == NULL || *tugma_joy == 0) return TUGMA_HA;
    char *v = strchr(tugma_joy, ',');
    size_t n = v ? (size_t)(v - tugma_joy) : strlen(tugma_joy);
    int r = TUGMA_HA;
    if (n == 3 && strncmp(tugma_joy, "rad", 3) == 0) r = TUGMA_RAD;
    else if (n == 3 && strncmp(tugma_joy, "yoq", 3) == 0) r = TUGMA_YOQ;
    tugma_joy = v ? v + 1 : tugma_joy + n;
    return r;
}

void hal_led(int rejim) { (void)rejim; }

bool hal_flash_oqi(uint8_t out[AQ_FLASH_YOZUV_UZ]) {
    const char *yol = getenv("AQ_FLASH");
    memset(out, 0xFF, AQ_FLASH_YOZUV_UZ);
    if (!yol) return false;
    FILE *f = fopen(yol, "rb");
    if (!f) return false;
    size_t k = fread(out, 1, AQ_FLASH_YOZUV_UZ, f);
    fclose(f);
    return k == AQ_FLASH_YOZUV_UZ;
}

bool hal_flash_yoz(const uint8_t d[AQ_FLASH_YOZUV_UZ]) {
    const char *yol = getenv("AQ_FLASH");
    if (!yol) return true;
    char tmp[4096];
    snprintf(tmp, sizeof tmp, "%s.tmp", yol);
    FILE *f = fopen(tmp, "wb");
    if (!f) return false;
    bool ok = fwrite(d, 1, AQ_FLASH_YOZUV_UZ, f) == AQ_FLASH_YOZUV_UZ;
    ok = fclose(f) == 0 && ok;
    return ok && rename(tmp, yol) == 0;
}

void hal_seriya(uint8_t out[8]) {
    const char *s = getenv("AQ_SERIYA");
    for (int i = 0; i < 8; i++) {
        unsigned b = (unsigned)(i + 1);
        if (s && strlen(s) == 16) sscanf(s + 2 * i, "%2x", &b);
        out[i] = (uint8_t)b;
    }
}

/* --- bo'yalgan stekda ishlash ---------------------------------------------------------- */

#define STEK_UZ (1024 * 1024)
#define NAQSH 0xA5

static void *ishla(void *arg) {
    (void)arg;
    static uint8_t b[4096];       /* stekda emas — o'lchovni buzmasin */
    aq_hsm_boshla();
    for (;;) {
        ssize_t k = read(0, b, sizeof b);
        if (k < 0 && errno == EINTR) continue;
        if (k <= 0) break;
        aq_hsm_qabul(b, (size_t)k);
    }
    return NULL;
}

int main(void) {
    clock_gettime(CLOCK_MONOTONIC, &t0);
    const char *t = getenv("AQ_TUGMA");
    if (t) {
        snprintf(tugma_navbat, sizeof tugma_navbat, "%s", t);
        tugma_joy = tugma_navbat;
    }
    uint8_t *stek = malloc(STEK_UZ);
    if (!stek) return 2;
    memset(stek, NAQSH, STEK_UZ);
    pthread_attr_t a;
    pthread_t th;
    pthread_attr_init(&a);
    pthread_attr_setstack(&a, stek, STEK_UZ);
    if (pthread_create(&th, &a, ishla, NULL) != 0) return 2;
    pthread_join(th, NULL);
    if (getenv("AQ_STEK")) {
        size_t i = 0;
        while (i < STEK_UZ && stek[i] == NAQSH) i++;  /* stek pastga o'sadi */
        fprintf(stderr, "stek %zu bayt, arena %zu bayt\n", (size_t)STEK_UZ - i,
                aq_arena_eng_kop());
    }
    free(stek);
    return 0;
}
