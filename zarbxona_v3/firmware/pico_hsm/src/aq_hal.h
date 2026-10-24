/* Apparat qatlami (HAL): yadro (aq_hsm.c) faqat shu funksiyalar orqali tashqi dunyo
 * bilan gaplashadi. Ikki amalga oshirish bor:
 *   main_pico.c — RP2040 (USB CDC, flash, GPIO tugma/LED, ROSC tasodifi);
 *   main_host.c — kompyuter (stdin/stdout, fayl, muhit o'zgaruvchilari) — testlar uchun. */
#ifndef AQ_HAL_H
#define AQ_HAL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum { TUGMA_HA = 1, TUGMA_RAD = 2, TUGMA_YOQ = 3 };
enum { LED_QULF = 0, LED_OCHIQ = 1, LED_RUXSAT = 2, LED_KUTISH = 3, LED_XATO = 4 };

#define AQ_FLASH_YOZUV_UZ 256   /* bitta flash sahifa */

void hal_yubor(const uint8_t *d, size_t n);           /* USB'ga yozish (to'liq) */
void hal_tasodif(uint8_t *out, size_t n);             /* qurilma tasodifi */
uint64_t hal_ms(void);                                /* yoqilgandan beri, ms */
int hal_tugma(uint32_t kutish_ms);                    /* TUGMA_HA | TUGMA_RAD | TUGMA_YOQ */
void hal_led(int rejim);
bool hal_flash_oqi(uint8_t out[AQ_FLASH_YOZUV_UZ]);
bool hal_flash_yoz(const uint8_t d[AQ_FLASH_YOZUV_UZ]);
void hal_seriya(uint8_t out[8]);

#endif
