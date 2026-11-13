/* Host timing of qv_detect over the golden vectors (not an MCU cycle count). */
#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <time.h>

#include "qv_infer.h"
#include "qv_vectors.h"

int main(void)
{
    enum { ITERS = 2000 };
    qv_result_t r;
    volatile int32_t sink = 0;
    struct timespec a, b;
    clock_gettime(CLOCK_MONOTONIC, &a);
    for (int it = 0; it < ITERS; it++)
        for (int v = 0; v < QV_N_VECTORS; v++) {
            qv_detect(&qv_vec_x[v * QV_FEATURES], &r);
            sink += r.score;
        }
    clock_gettime(CLOCK_MONOTONIC, &b);
    double ns = ((double)(b.tv_sec - a.tv_sec) * 1e9 + (double)(b.tv_nsec - a.tv_nsec)) / (ITERS * QV_N_VECTORS);
    printf("qv_detect: %.1f ns/window on host (%d windows)\n", ns, ITERS * QV_N_VECTORS);
    return sink == 0x7fffffff;
}
