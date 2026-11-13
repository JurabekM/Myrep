/* QORAVUL int8 autoencoder inference, bit-exact with qoravul/tinyml/model.py.
 * Build without -ffast-math and with -ffp-contract=off so qv_quantize matches
 * numpy float32 arithmetic (no FMA contraction). */
#include "qv_infer.h"

#include <math.h>

#include "qv_model.h"

#if QV_N_IN != QV_FEATURES
#error "model input width does not match QV_FEATURES"
#endif

static int32_t clamp32(int64_t v, int32_t lo, int32_t hi)
{
    return v < lo ? lo : (v > hi ? hi : (int32_t)v);
}

void qv_quantize(const float x[QV_FEATURES], int8_t xq[QV_FEATURES])
{
    for (int k = 0; k < QV_FEATURES; k++) {
        float z = (x[k] - qv_mean[k]) / qv_std[k] / qv_s_in;
        if (z > 127.0f) z = 127.0f;
        if (z < -127.0f) z = -127.0f;
        xq[k] = (int8_t)lrintf(z); /* round-half-even, same as numpy.rint */
    }
}

int32_t qv_score_q(const int8_t xq[QV_FEATURES], int8_t yq[QV_FEATURES], int32_t err[QV_FEATURES])
{
    int8_t buf_a[QV_MAX_WIDTH], buf_b[QV_MAX_WIDTH];
    int8_t *in = buf_a, *out = buf_b;
    for (int k = 0; k < QV_FEATURES; k++) in[k] = xq[k];

    for (int l = 0; l < QV_N_LAYERS; l++) {
        const int n_in = qv_dims[l], n_out = qv_dims[l + 1];
        const int8_t *w = qv_w[l];
        const int64_t m0 = qv_m0[l];
        const int sh = qv_sh[l];
        const int32_t lo = qv_relu[l] ? 0 : -127;
        for (int o = 0; o < n_out; o++) {
            int32_t acc = qv_b[l][o];
            for (int i = 0; i < n_in; i++) acc += (int32_t)w[o * n_in + i] * (int32_t)in[i];
            /* arithmetic shift of a signed int64 (floor), as in numpy >> */
            int64_t y = ((int64_t)acc * m0 + ((int64_t)1 << (sh - 1))) >> sh;
            out[o] = (int8_t)clamp32(y, lo, 127);
        }
        int8_t *t = in;
        in = out;
        out = t;
    }

    int32_t score = 0;
    for (int k = 0; k < QV_FEATURES; k++) {
        int32_t d = (int32_t)xq[k] - (int32_t)in[k];
        int32_t e = d * d;
        if (yq) yq[k] = in[k];
        if (err) err[k] = e;
        score += e;
    }
    return score;
}

void qv_detect(const float x[QV_FEATURES], qv_result_t *res)
{
    int8_t xq[QV_FEATURES];
    int32_t err[QV_FEATURES];
    qv_quantize(x, xq);
    res->score = qv_score_q(xq, 0, err);

    int env = -1;
    for (int k = 0; k < QV_FEATURES; k++) {
        if (xq[k] < qv_env_lo[k] || xq[k] > qv_env_hi[k]) {
            env = k;
            break;
        }
    }
    res->envelope = env >= 0;
    res->anomaly = res->envelope || res->score > QV_THRESHOLD;

    if (env >= 0) {
        res->culprit = (uint8_t)env;
        return;
    }
    /* argmax err[k] / feat_thresh[k] by cross-multiplication; first index wins ties */
    int best = 0;
    for (int k = 1; k < QV_FEATURES; k++) {
        uint64_t lhs = (uint64_t)err[k] * (uint64_t)qv_feat_thresh[best];
        uint64_t rhs = (uint64_t)err[best] * (uint64_t)qv_feat_thresh[k];
        if (lhs > rhs) best = k;
    }
    res->culprit = (uint8_t)best;
}
