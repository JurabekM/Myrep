/* mldsa-native sozlamasi (MLD_CONFIG_FILE): ML-DSA-65, kam RAM, katta buferlar stekda
 * emas — statik arenada. RP2040'da asosiy stek atigi 4 KB (SCRATCH_Y). */
#ifndef AQ_MLDSA_CONFIG_H
#define AQ_MLDSA_CONFIG_H

#define MLD_CONFIG_PARAMETER_SET 65
#define MLD_CONFIG_NAMESPACE_PREFIX mldsa
#define MLD_CONFIG_REDUCE_RAM
#define MLD_CONFIG_CUSTOM_ALLOC_FREE

#if !defined(__ASSEMBLER__)
#include <stddef.h>
void *aq_arena_ol(size_t n);
void aq_arena_ber(void *p);
#define MLD_CUSTOM_ALLOC(v, T, N) T *(v) = (T *)aq_arena_ol(sizeof(T) * (N))
#define MLD_CUSTOM_FREE(v, T, N) aq_arena_ber(v)
#endif

#include "mldsa_native_config.h"   /* qolgan standart sozlamalar */

#endif
