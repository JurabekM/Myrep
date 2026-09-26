/* ML-KEM-768 / ML-DSA-65 on Cortex-M33 (QEMU mps2-an505): known-answer output,
 * instruction-count proxy and stack peak (stack painting) per operation.
 *
 * Uses the deterministic APIs of mlkem-native / mldsa-native (portable C
 * backend) so every output can be compared byte for byte against kyber-py /
 * dilithium-py (see tests/test_pq_m33.py). Instruction counts come from
 * SysTick under `qemu -icount shift=0`, calibrated with a 2e6-instruction
 * loop; they are NOT cycle counts (QEMU models neither pipeline nor DWT). */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "mldsa_native.h"
#include "mlkem_native.h"

#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)

#define PAINT_BYTES (128u * 1024u)
#define PAINT 0xA5A5A5A5u

static uint32_t instr_per_tick_x1000;

static void tick_start(void)
{
    SYST_CSR = 0;
    SYST_RVR = 0x00FFFFFFu;
    SYST_CVR = 0;
    SYST_CSR = 5u;
}

static uint32_t tick_read(void) { return SYST_CVR; }

static uint32_t tick_elapsed(uint32_t t0, uint32_t t1) { return (t0 - t1) & 0x00FFFFFFu; }

static void calibrate(void)
{
    uint32_t n = 1000000u; /* subs + bne = 2 instructions per iteration */
    tick_start();
    uint32_t t0 = tick_read();
    __asm volatile("1: subs %0, %0, #1\n bne 1b" : "+r"(n));
    uint32_t t = tick_elapsed(t0, tick_read());
    instr_per_tick_x1000 = (uint32_t)(2000000000ull / t);
}

/* Fill the unused stack below the current frame with a pattern. */
static __attribute__((noinline)) uint32_t *paint_stack(void)
{
    uint32_t *sp;
    __asm volatile("mov %0, sp" : "=r"(sp));
    uint32_t *lo = sp - PAINT_BYTES / 4u;
    for (uint32_t *p = lo; p < sp - 64; p++) *p = PAINT;
    return lo;
}

static uint32_t stack_used(const uint32_t *lo, const uint32_t *top)
{
    const uint32_t *p = lo;
    while (p < top && *p == PAINT) p++;
    return (uint32_t)((const uint8_t *)top - (const uint8_t *)p);
}

static void hex(const char *name, const uint8_t *b, size_t n)
{
    printf("%s=", name);
    for (size_t i = 0; i < n; i++) printf("%02x", b[i]);
    printf("\n");
}

#define MEASURE(label, stmt)                                                                    \
    do {                                                                                        \
        uint32_t *lo_ = paint_stack(), *top_;                                                   \
        __asm volatile("mov %0, sp" : "=r"(top_));                                              \
        tick_start();                                                                           \
        uint32_t t0_ = tick_read();                                                             \
        stmt;                                                                                   \
        uint32_t dt_ = tick_elapsed(t0_, tick_read());                                          \
        printf("bench %s instr=%lu stack=%lu\n", label,                                         \
               (unsigned long)((uint64_t)dt_ * instr_per_tick_x1000 / 1000u),                   \
               (unsigned long)stack_used(lo_, top_));                                           \
    } while (0)

static uint8_t kem_pk[MLKEM768_PUBLICKEYBYTES], kem_sk[MLKEM768_SECRETKEYBYTES];
static uint8_t kem_ct[MLKEM768_CIPHERTEXTBYTES], kem_ss[MLKEM_BYTES], kem_ss2[MLKEM_BYTES];
static uint8_t dsa_pk[MLDSA65_PUBLICKEYBYTES], dsa_sk[MLDSA65_SECRETKEYBYTES], dsa_sig[MLDSA65_BYTES];

int main(void)
{
    uint8_t coins[64], m[32], seed[32], rnd[32];
    static const uint8_t msg[] = "QVL1 evidence test vector";
    static const uint8_t ctx[] = "QVL1-EVIDENCE";
    uint8_t pre[2 + sizeof(ctx) - 1];
    int rc = 0;

    for (int i = 0; i < 64; i++) coins[i] = (uint8_t)i;          /* d = 00..1f, z = 20..3f */
    for (int i = 0; i < 32; i++) m[i] = (uint8_t)(0x40 + i);
    for (int i = 0; i < 32; i++) seed[i] = (uint8_t)(0x80 + i);
    memset(rnd, 0, sizeof rnd);                                   /* deterministic ML-DSA */
    pre[0] = 0;
    pre[1] = (uint8_t)(sizeof(ctx) - 1);
    memcpy(pre + 2, ctx, sizeof(ctx) - 1);

    calibrate();
    printf("calib instr_per_tick=%lu.%03lu\n", (unsigned long)(instr_per_tick_x1000 / 1000u),
           (unsigned long)(instr_per_tick_x1000 % 1000u));

    MEASURE("mlkem768_keypair", rc |= mlkem_keypair_derand(kem_pk, kem_sk, coins));
    MEASURE("mlkem768_encaps", rc |= mlkem_enc_derand(kem_ct, kem_ss, kem_pk, m));
    MEASURE("mlkem768_decaps", rc |= mlkem_dec(kem_ss2, kem_ct, kem_sk));
    MEASURE("mldsa65_keypair", rc |= mldsa_keypair_internal(dsa_pk, dsa_sk, seed));
    MEASURE("mldsa65_sign", rc |= mldsa_signature_internal(dsa_sig, msg, sizeof(msg) - 1, pre, sizeof pre, rnd,
                                                            dsa_sk, 0));
    MEASURE("mldsa65_verify", rc |= mldsa_verify_internal(dsa_sig, msg, sizeof(msg) - 1, pre,
                                                           sizeof pre, dsa_pk, 0));

    hex("kem_pk", kem_pk, sizeof kem_pk);
    hex("kem_ct", kem_ct, sizeof kem_ct);
    hex("kem_ss", kem_ss, sizeof kem_ss);
    hex("dsa_pk", dsa_pk, sizeof dsa_pk);
    hex("dsa_sig", dsa_sig, sizeof dsa_sig);
    printf("decaps_match=%d rc=%d\n", memcmp(kem_ss, kem_ss2, sizeof kem_ss) == 0, rc);
    return rc != 0 || memcmp(kem_ss, kem_ss2, sizeof kem_ss) != 0;
}
