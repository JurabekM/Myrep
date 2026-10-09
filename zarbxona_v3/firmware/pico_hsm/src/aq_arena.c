/* mldsa-native ehtiyojlari: tasodif (randombytes) va katta buferlar uchun arena.
 *
 * RP2040'da asosiy stek 4 KB — ML-DSA-65 buferlari (~17 KB) stekka sig'maydi. Arena:
 * bloklar ustma-ust ajratiladi; bo'shatilgan blok faqat o'zidan YUQORIDAGI hamma blok
 * ham bo'shaganda qaytariladi. Shu sabab bo'shatish tartibi qanday bo'lmasin, tirik
 * blok hech qachon ustiga yozilmaydi. Bo'shatilgan joy nol bilan tozalanadi. */
#include <stdint.h>
#include <string.h>

#include "aq_hal.h"
#include "mldsa_native.h"

#define ARENA_UZ (MLD_TOTAL_ALLOC_65 + 2048)
#define MAX_BLOK 48

static uint8_t arena[ARENA_UZ] __attribute__((aligned(16)));
static struct { size_t boshi, uz; int band; } blok[MAX_BLOK];
static int nblok;
static size_t tepa, eng_kop;

void *aq_arena_ol(size_t n);
void aq_arena_ber(void *p);
size_t aq_arena_eng_kop(void);
int randombytes(uint8_t *out, size_t n);

void *aq_arena_ol(size_t n) {
    size_t k = (n + 15u) & ~(size_t)15u;
    if (nblok == MAX_BLOK || k > ARENA_UZ - tepa) return NULL;
    blok[nblok].boshi = tepa;
    blok[nblok].uz = k;
    blok[nblok].band = 1;
    nblok++;
    void *p = arena + tepa;
    tepa += k;
    if (tepa > eng_kop) eng_kop = tepa;
    return p;
}

void aq_arena_ber(void *p) {
    if (p == NULL) return;
    size_t i = (size_t)((uint8_t *)p - arena);
    for (int b = nblok - 1; b >= 0; b--) {
        if (blok[b].band && blok[b].boshi == i) {
            blok[b].band = 0;
            memset(arena + i, 0, blok[b].uz);
            break;
        }
    }
    while (nblok > 0 && !blok[nblok - 1].band) {
        nblok--;
        tepa = blok[nblok].boshi;
    }
}

size_t aq_arena_eng_kop(void) { return eng_kop; }

int randombytes(uint8_t *out, size_t n) {
    hal_tasodif(out, n);
    return 0;
}
