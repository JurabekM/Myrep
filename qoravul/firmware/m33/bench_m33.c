/* Instruction-count proxy for qv_detect on QEMU mps2-an505.
 * Run with -icount shift=0 (1 instruction = 1 ns virtual time). SysTick ticks
 * are converted to instructions with a self-calibration loop of exactly 2e6
 * instructions (subs+bne). This is NOT a cycle count: real cycles need
 * DWT_CYCCNT on hardware (QEMU does not model the DWT cycle counter). */
#include <stdint.h>
#include <stdio.h>

#include "../qv_infer.h"
#include "../qv_vectors.h"

#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)

static uint32_t run(int iters)
{
    qv_result_t r;
    volatile int32_t sink = 0;
    SYST_RVR = 0x00FFFFFFu;
    SYST_CVR = 0;
    SYST_CSR = 5u; /* enable, processor clock, no interrupt */
    uint32_t t0 = SYST_CVR;
    for (int it = 0; it < iters; it++)
        for (int v = 0; v < QV_N_VECTORS; v++) {
            qv_detect(&qv_vec_x[v * QV_FEATURES], &r);
            sink += r.score;
        }
    uint32_t t1 = SYST_CVR;
    SYST_CSR = 0;
    (void)sink;
    return (t0 - t1) & 0x00FFFFFFu; /* down-counter */
}

static uint32_t calibrate(void)
{
    uint32_t n = 1000000u; /* 2 instructions per iteration */
    SYST_RVR = 0x00FFFFFFu;
    SYST_CVR = 0;
    SYST_CSR = 5u;
    uint32_t t0 = SYST_CVR;
    __asm volatile("1: subs %0, %0, #1\n bne 1b" : "+r"(n));
    uint32_t t1 = SYST_CVR;
    SYST_CSR = 0;
    return (t0 - t1) & 0x00FFFFFFu;
}

int main(void)
{
    uint32_t cal = calibrate(); /* ticks for 2e6 instructions */
    uint32_t base = run(0), ticks = run(4);
    unsigned long per = (unsigned long)((uint64_t)(ticks - base) * 2000000u / cal / (4u * QV_N_VECTORS));
    printf("qv_detect: ~%lu instructions/window (QEMU icount proxy; %lu instr/tick)\n", per,
           (unsigned long)(2000000u / cal));
    return 0;
}
