/* Zarbxona Pico HSM yadrosi: AQP1 protokoli va qurilma qoidalari.
 * Xost tomonidagi etalon — core/pico/soxta.py; spetsifikatsiya — docs/PICO_PROTOKOL.md. */
#ifndef AQ_HSM_H
#define AQ_HSM_H

#include <stddef.h>
#include <stdint.h>

#define AQ_QURILMA_VERSIYASI "zarbxona-pico 1.0"

void aq_hsm_boshla(void);                          /* flash'ni o'qiydi */
void aq_hsm_qabul(const uint8_t *d, size_t n);     /* USB'dan kelgan baytlar */
int aq_hsm_led_holati(void);                       /* asosiy sikl LED uchun */

#endif
