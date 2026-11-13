/* QORAVUL int8 detector -- C99, no heap, no floats after qv_quantize(). */
#ifndef QV_INFER_H
#define QV_INFER_H

#include <stdint.h>

#define QV_FEATURES 8

typedef struct {
    int32_t score;   /* sum over features of (x_q - y_q)^2 */
    uint8_t anomaly; /* envelope violated OR score > threshold */
    uint8_t envelope;/* 1 if the envelope stage fired */
    uint8_t culprit; /* feature index blamed for the anomaly */
} qv_result_t;

/* float32 features -> int8: rint((x - mean) / std / s_in), clamped to +-127. */
void qv_quantize(const float x[QV_FEATURES], int8_t xq[QV_FEATURES]);

/* Autoencoder reconstruction + score. yq and err may be NULL. */
int32_t qv_score_q(const int8_t xq[QV_FEATURES], int8_t yq[QV_FEATURES], int32_t err[QV_FEATURES]);

/* Full detection pipeline on one window. */
void qv_detect(const float x[QV_FEATURES], qv_result_t *res);

#endif /* QV_INFER_H */
