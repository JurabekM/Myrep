/* Host parity test: C int8 inference vs Python golden vectors, bit for bit. */
#include <stdio.h>

#include "qv_infer.h"
#include "qv_vectors.h"

int main(void)
{
    int ok = 0, anomalies = 0;
    for (int v = 0; v < QV_N_VECTORS; v++) {
        const float *x = &qv_vec_x[v * QV_FEATURES];
        int8_t xq[QV_FEATURES], yq[QV_FEATURES];
        qv_result_t r;
        int good = 1;

        qv_quantize(x, xq);
        int32_t s = qv_score_q(xq, yq, 0);
        qv_detect(x, &r);
        for (int k = 0; k < QV_FEATURES; k++) {
            if (xq[k] != qv_vec_xq[v * QV_FEATURES + k]) good = 0;
            if (yq[k] != qv_vec_yq[v * QV_FEATURES + k]) good = 0;
        }
        if (s != qv_vec_score[v] || r.score != s) good = 0;
        if (r.anomaly != qv_vec_anomaly[v] || r.culprit != qv_vec_culprit[v]) good = 0;
        if (!good) {
            fprintf(stderr, "mismatch at vector %d: score C=%ld py=%ld anomaly C=%d py=%d culprit C=%d py=%d\n", v,
                    (long)s, (long)qv_vec_score[v], r.anomaly, qv_vec_anomaly[v], r.culprit, qv_vec_culprit[v]);
        }
        ok += good;
        anomalies += r.anomaly;
    }
    printf("parity: %d/%d vectors bit-exact (%d anomalous)\n", ok, QV_N_VECTORS, anomalies);
    return ok == QV_N_VECTORS ? 0 : 1;
}
