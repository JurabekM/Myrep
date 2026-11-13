/* Raspberry Pi Pico (RP2040) HAL'i va asosiy sikl.
 *
 * Ulanish (docs/PICO_PROTOKOL.md, firmware/pico_hsm/README.md):
 *   GP14 — tugma, ikkinchi oyog'i GND ga (ichki pull-up yoqiladi);
 *   GP15 — LED (+ 330 Ω rezistor) GND ga; platadagi LED (GP25) ham xuddi shunday yonadi.
 *   (Pico W da platadagi LED Wi-Fi chipiga ulangan — faqat tashqi LED ishlaydi.)
 *
 * LED: o'chiq — qulflangan; yonib turadi — PIN bilan ochilgan; sekin miltillaydi —
 * buyurtma ruxsati faol; tez miltillaydi — TUGMANI BOSING. */
#include <stdio.h>
#include <string.h>

#include "aq_hal.h"
#include "aq_hsm.h"
#include "aq_keccak.h"
#include "hardware/flash.h"
#include "hardware/gpio.h"
#include "hardware/structs/rosc.h"
#include "pico/flash.h"
#include "pico/rand.h"
#include "pico/stdio_usb.h"
#include "pico/stdlib.h"
#include "pico/unique_id.h"

#define TUGMA_PIN 14
#define LED_PIN 15
#define TASHQI_LED_BOR 1
#define UZUN_BOSISH_MS 2000u
#define FLASH_OFS (PICO_FLASH_SIZE_BYTES - FLASH_SECTOR_SIZE)

static int led_rejim = LED_QULF;

/* --- USB ------------------------------------------------------------------------------ */

void hal_yubor(const uint8_t *d, size_t n) {
    fwrite(d, 1, n, stdout);
    fflush(stdout);
}

/* --- tasodif: ROSC shovqini + pico_rand + vaqt → SHA3 havzasi --------------------------
 * RP2040'da sertifikatlangan TRNG yo'q. Havza ROSC'ning tasodifiy bitlari bilan
 * to'ldiriladi va har chaqiriqda yangi manbalar qo'shiladi. Kalit yaratishda xost
 * entropiyasi ham aralashadi (aq_hsm.c), shuning uchun bitta manba zaif bo'lsa ham
 * kalit oldindan aytib bo'lmaydigan bo'lib qoladi. */

static uint8_t havza[32];
static uint64_t sanoq;
static bool havza_tayyor;

static uint8_t rosc_bayt(void) {
    uint8_t b = 0;
    for (int i = 0; i < 8; i++) {
        b = (uint8_t)((b << 1) | (rosc_hw->randombit & 1u));
        busy_wait_us_32(2);
    }
    return b;
}

static void havza_aralash(void) {
    aq_keccak k;
    aq_sha3_256_init(&k);
    aq_keccak_update(&k, havza, sizeof havza);
    for (int i = 0; i < (havza_tayyor ? 32 : 256); i++) {
        uint8_t b = rosc_bayt();
        aq_keccak_update(&k, &b, 1);
    }
    rng_128_t r;
    get_rand_128(&r);
    aq_keccak_update(&k, (const uint8_t *)&r, sizeof r);
    uint64_t t = time_us_64();
    aq_keccak_update(&k, (const uint8_t *)&t, sizeof t);
    aq_keccak_final(&k, havza, sizeof havza);
    havza_tayyor = true;
}

void hal_tasodif(uint8_t *out, size_t n) {
    havza_aralash();
    aq_keccak k;
    aq_shake256_init(&k);
    aq_keccak_update(&k, havza, sizeof havza);
    sanoq++;
    aq_keccak_update(&k, (const uint8_t *)&sanoq, sizeof sanoq);
    aq_keccak_final(&k, out, n);
    aq_sha3_256(havza, havza, sizeof havza); /* oldingi chiqishlarni qayta tiklab bo'lmasin */
}

uint64_t hal_ms(void) { return time_us_64() / 1000u; }

/* --- tugma va LED ------------------------------------------------------------------- */

static bool bosilgan(void) { return !gpio_get(TUGMA_PIN); }

static void led_yoz(bool yon) {
#ifdef PICO_DEFAULT_LED_PIN
    gpio_put(PICO_DEFAULT_LED_PIN, yon);
#endif
#if TASHQI_LED_BOR
    gpio_put(LED_PIN, yon);
#endif
}

static void led_yangila(void) {
    uint64_t t = hal_ms();
    switch (led_rejim) {
    case LED_OCHIQ: led_yoz(true); break;
    case LED_RUXSAT: led_yoz((t / 500u) % 2u == 0); break;
    case LED_KUTISH: led_yoz((t / 100u) % 2u == 0); break;
    case LED_XATO: led_yoz((t / 50u) % 2u == 0); break;
    default: led_yoz(false); break;
    }
}

void hal_led(int rejim) { led_rejim = rejim; }

int hal_tugma(uint32_t kutish_ms) {
    uint64_t oxiri = hal_ms() + kutish_ms;
    /* So'rov paytida bosib turilgan (yoki tiqilib qolgan) tugma tasdiq emas: avval qo'yib
     * yuborilishi kerak. */
    while (bosilgan()) {
        led_yangila();
        if (hal_ms() >= oxiri) return TUGMA_YOQ;
    }
    while (hal_ms() < oxiri) {
        led_yangila();
        if (!bosilgan()) continue;
        sleep_ms(30); /* tebranish */
        if (!bosilgan()) continue;
        uint64_t boshi = hal_ms();
        while (bosilgan()) {
            if (hal_ms() - boshi >= UZUN_BOSISH_MS) return TUGMA_RAD; /* qo'yishni kutmaymiz */
        }
        return TUGMA_HA;
    }
    return TUGMA_YOQ;
}

/* --- flash: oxirgi 4 KB sektor ---------------------------------------------------------- */

bool hal_flash_oqi(uint8_t out[AQ_FLASH_YOZUV_UZ]) {
    memcpy(out, (const uint8_t *)(XIP_BASE + FLASH_OFS), AQ_FLASH_YOZUV_UZ);
    return true;
}

static void flash_ish(void *p) {
    flash_range_erase(FLASH_OFS, FLASH_SECTOR_SIZE);
    flash_range_program(FLASH_OFS, (const uint8_t *)p, FLASH_PAGE_SIZE);
}

bool hal_flash_yoz(const uint8_t d[AQ_FLASH_YOZUV_UZ]) {
    static uint8_t sahifa[FLASH_PAGE_SIZE];
    memcpy(sahifa, d, FLASH_PAGE_SIZE);
    bool ok = flash_safe_execute(flash_ish, sahifa, UINT32_MAX) == PICO_OK &&
              memcmp((const uint8_t *)(XIP_BASE + FLASH_OFS), sahifa, FLASH_PAGE_SIZE) == 0;
    memset(sahifa, 0, sizeof sahifa);
    return ok;
}

void hal_seriya(uint8_t out[8]) {
    pico_unique_board_id_t id;
    pico_get_unique_board_id(&id);
    memcpy(out, id.id, 8);
}

/* --- asosiy sikl ----------------------------------------------------------------------
 * ML-DSA-65 ga ~10-12 KB stek kerak (katta buferlar arenada bo'lsa ham), RP2040'ning
 * standart asosiy steki esa 4 KB (SCRATCH_Y). Shuning uchun sikl RAM'dagi alohida 32 KB
 * stekda ishlaydi: `stekda_ishga_tushir` SP ni almashtirib, qaytmaydigan funksiyani
 * chaqiradi. Uzilishlar ham shu stekdan foydalanadi. */

#define ASOSIY_STEK_UZ (32 * 1024)
static uint32_t asosiy_stek[ASOSIY_STEK_UZ / 4] __attribute__((aligned(8)));

static void __attribute__((naked, noinline, noreturn))
stekda_ishga_tushir(void (*f)(void), uint32_t *tepa) {
    (void)f;
    (void)tepa;
    __asm volatile("mov sp, r1\n"
                   "blx r0\n"
                   "1: b 1b\n");
}

static void __attribute__((noreturn)) asosiy_sikl(void) {
    aq_hsm_boshla();
    static uint8_t b[512];
    for (;;) {
        size_t n = 0;
        int c;
        while (n < sizeof b && (c = stdio_getchar_timeout_us(n ? 0 : 1000)) != PICO_ERROR_TIMEOUT)
            b[n++] = (uint8_t)c;
        if (n) aq_hsm_qabul(b, n);
        hal_led(aq_hsm_led_holati());
        led_yangila();
    }
}

int main(void) {
    stdio_usb_init();
    stdio_set_translate_crlf(&stdio_usb, false);
    gpio_init(TUGMA_PIN);
    gpio_set_dir(TUGMA_PIN, GPIO_IN);
    gpio_pull_up(TUGMA_PIN);
#ifdef PICO_DEFAULT_LED_PIN
    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);
#endif
#if TASHQI_LED_BOR
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
#endif
    stekda_ishga_tushir(asosiy_sikl, asosiy_stek + ASOSIY_STEK_UZ / 4);
}
